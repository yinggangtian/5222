import sys
from lib_piglet.output.file_output import file_output
from yaml import dump

from lib_piglet.output.print_output import print_output


class trace_print_output(print_output):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def head(self, **kwargs):
        self.verbatim(dump({"version": "1.4.0"}))
        if "views" in kwargs and kwargs["views"]:
            self.verbatim(dump({"views": kwargs["views"]}))
        if "pivot" in kwargs and kwargs["pivot"]:
            self.verbatim(dump({"pivot": kwargs["pivot"]}))
        self.verbatim("events:")

    def event(self, **kwargs):
        self.verbatim(f"- {dump(kwargs, default_flow_style=True,width=99999).rstrip()}")
