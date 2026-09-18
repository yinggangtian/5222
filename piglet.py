# import sys

# if sys.version_info[0] < 3 or (sys.version_info[0] == 3 and sys.version_info[1] <= 10):
#     raise Exception("Requires Python 3.11 or newer")

# # ──────────────────────────────────────────────────────────────────────────────

import sys
from typing import Union
import os

from lib_piglet.cli.cli_tool import (
    csv_header,
    is_log_mode,
    parse_args,
    parse_logger_args,
    parse_problem,
    parse_scen_header,
    print_header,
    statistic_csv,
    statistic_string,
)
from lib_piglet.cli.run_tool import run_multi_tasks, run_task
from lib_piglet.logging.search_logger import search_logger
from lib_piglet.utils.identifier import get_random_id
from lib_piglet.output.outputs import outputs
from lib_piglet.output.base_output import base_output


def get_logger(spec: Union[list, None], auto_filename: str = None):
    [key, filename, *_] = parse_logger_args(spec)
    key = "trace-file" if key == "trace" and filename else key
    logger = outputs[key] if key in outputs else base_output
    return search_logger(logger=logger(file=filename or auto_filename))


def main():

    args = parse_args()

    header_readed = False

    # detect which source to accept scenario data. An explicit -p always wins:
    # falling back to stdin whenever it is not a tty would silently ignore -p
    # for any non-interactive caller, such as a script, an IDE console or CI.
    if args.problem is not None:
        if not os.path.exists(args.problem):
            print("err; Given problem scenario file does not exist: {}".format(args.problem), file = sys.stderr)
            exit(1)
        source = open(args.problem)
    elif not sys.stdin.isatty():
        source = sys.stdin
    else:
        print("err; You must provide a problem scenario file or provide problem through standard input", file = sys.stderr)
        print("piglet.py -h for help", file=sys.stderr)
        exit(1)

    if not is_log_mode(args.log):
        print_header(args.anytime)
    if args.output_file:
        out = open(args.output_file, "w+")
        out.write(csv_header(args.anytime))

    domain_type = None
    multi_tasks = []
    seen = 0
    ran = 0
    for line in source:
        content = line.strip().split()
        if should_ignore(content):
            continue

        if not header_readed:
            domain_type = parse_scen_header(content)
            header_readed = True
            continue

        if seen >= args.problem_index:
            if ran >= args.problem_number:
                break

            task = parse_problem(content, domain_type)

            with get_logger(
                args.log, f"{'-'.join([args.framework, args.strategy])}-{get_random_id()}.trace.yaml",
            ) as logger:
                if args.multi_agent:
                    multi_tasks.append(task)
                    search = run_multi_tasks(domain_type, multi_tasks, args)
                else:
                    search = run_task(task, args, logger)
                stats = statistic_string(
                    args, search, args.anytime, logger.logger_ if args.log else None
                )
                if stats:
                    print(stats)
                if args.output_file:
                    out.write(statistic_csv(args, search, args.anytime))
            ran += 1
        seen += 1
    if args.output_file:
        out.close()


def should_ignore(content):
    return len(content) == 0 or content[0] == "#" or content[0] == "c"


if __name__ == "__main__":
    main()
