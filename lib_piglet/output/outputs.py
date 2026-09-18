from lib_piglet.output.trace_print_output import trace_print_output
from lib_piglet.output.print_output import print_output
from lib_piglet.output.trace_output import trace_output


outputs = {
    "print": print_output,
    "trace": trace_print_output,
    "trace-file": trace_output,
}
