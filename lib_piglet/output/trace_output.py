import sys
from lib_piglet.output.file_output import file_output
from yaml import dump


class trace_output(file_output):
    i = 0

    def clear(self):
        sys.stdout.write("\x1b[1A")
        sys.stdout.write("\x1b[2K")

    def __init__(self, **kwargs):
        self.warn_filename_validity(kwargs)
        super().__init__(**kwargs)

    def warn_filename_validity(self, kwargs):
        if "file" in kwargs and not kwargs["file"].endswith(".trace.yaml"):
            print(
                f"Warning: output file must end in '.trace.yaml', otherwise it can't be imported into Posthoc.",
                file=sys.stderr,
            )

    def head(self, **kwargs):
        print("---")
        self.verbatim(dump({"version": "1.4.0"}))
        if "views" in kwargs and kwargs["views"]:
            self.verbatim(dump({"views": kwargs["views"]}))
        if "pivot" in kwargs and kwargs["pivot"]:
            self.verbatim(dump({"pivot": kwargs["pivot"]}))
        self.verbatim("events:\n")

    def event(self, **kwargs):
        self.clear()
        print(
            f"Logging to {self.args['file']} | Event {self.i:,}: {kwargs.get('type') or 'event'} {kwargs.get('id') or ''}"
        )
        self.i += 1
        self.verbatim(f"- {dump(kwargs, default_flow_style=True,width=99999)}")
