from textwrap import shorten
from typing import Iterable, TypeVar
from lib_piglet.output.base_output import base_output

T = TypeVar("T")


def chunks(it: Iterable[T], n: int):
    """
    Yield successive n-sized chunks from lst.
    https://stackoverflow.com/questions/312443/how-do-i-split-a-list-into-equally-sized-chunks
    """
    lst = list(it)
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class print_output(base_output):

    i = 0

    def verbatim(self, s: str):
        print(s)

    def event(self, **kwargs):
        self.verbatim(self.i)
        for chunk in chunks(kwargs.items(), 4):
            self.verbatim(
                "    "
                + " ".join(
                    shorten(f"{k}: {v}", width=30, placeholder="...").ljust(31)
                    for k, v in chunk
                )
            )
        self.verbatim("---")
        self.i += 1
