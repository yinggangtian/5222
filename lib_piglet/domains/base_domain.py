from typing import Generic, TypeVar

from lib_piglet.search.search_node import search_node


State = TypeVar("State")


class base_domain(Generic[State]):
    def get_name(self):
        raise NotImplementedError("Domains must be given a name.")
