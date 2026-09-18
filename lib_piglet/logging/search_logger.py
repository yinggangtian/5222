from lib_piglet.output.base_output import base_output
from lib_piglet.search.base_search import base_search
from lib_piglet.search.search_node import search_node
from lib_piglet.search.event_listener import event_listener
from lib_piglet.logging.serialisers import serialisers
from lib_piglet.utils.identifier import identifier


class search_logger(event_listener):

    def __init__(self, **kwargs):
        self.search_ = kwargs.get("search")
        self.logger_ = kwargs.get("logger") or base_output

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.logger_.close()

    def get_serialiser(self):
        if self.search_:
            domain = self.search_.expander_.domain_.get_name()
            if domain in serialisers:
                return serialisers[domain]

    def head(self):
        serialiser = self.get_serialiser()
        if serialiser:
            self.logger_.head(
                views=serialiser.views(),
                pivot=serialiser.pivot(),
            )
        else:
            self.logger_.head()

    def log(self, name:str, event: str, current: search_node, **kwargs):
        def serialise(s):
            return serialiser.serialise(s)

        serialiser = self.get_serialiser()
        self.logger_.event(
            type=event,
            id=f"{name}-{current.id}",
            f=current.f_,
            g=current.g_,
            h=current.h_,
            depth=current.depth_,
            pId=f"{name}-{current.parent_.id}" if current.parent_ else None,
            **(serialise(current) if serialiser else None),
            **kwargs
        )
        return current


def bind(search: base_search, logger: search_logger):
    search.listener_ = logger
    logger.search_ = search
    return logger
