from re import sub
from typing import Generic, TypeVar
from lib_piglet.domains.graph import vertex
from lib_piglet.domains.gridmap import grid_state
from lib_piglet.domains.n_puzzle import puzzle_state
from lib_piglet.search.search_node import search_node

State = TypeVar("State")


class domain_serialiser(Generic[State]):

    def serialise(self, state: search_node[State]):
        return dict()

    def views(self):
        return None

    def pivot(self):
        return None


def get_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def chunk(l, n):
    return list(get_chunks(l, n))


class n_puzzle_serialiser(domain_serialiser[puzzle_state]):
    def views(self):
        return {
            "tile": [
                {
                    "$": "rect",
                    "width": 0.98,
                    "height": 0.98,
                    "fill": "${{ theme.foreground }}",
                    "clear": True,
                    "label-x": 0.1,
                    "label-y": 0.85,
                    "x": "${{ $.row }}",
                    "y": "${{ $.col }}",
                    "label-size": 0.5,
                    "label-color": "${{ theme.background }}",
                    "label": "${{ $.board[$.col][$.row] }}",
                    "$if": "${{ $.board[$.col][$.row] != 'x' }}",
                    "$info": {"tile": "${{ $.board[$.col][$.row] }}"},
                }
            ],
            "main": [
                {
                    "$if": "${{ $.type != 'stats' }}",
                    "$": "tile",
                    "$for": {"$to": "${{ $.width * $.height }}"},
                    "col": "${{ Math.floor($.i / $.width) }}",
                    "row": "${{ $.i % $.width }}",
                }
            ],
        }

    def serialise(self, state: search_node[puzzle_state]):
        return {
            "width": state.state_.width(),
            "height": state.state_.width(),
            "board": chunk(state.state_.state_list_, state.state_.width()),
        }


class grid_serialiser(domain_serialiser[grid_state]):
    def views(self):
        return {
            "main": [
                {
                    "$if": "${{ $.type != 'stats' }}",
                    "$": "rect",
                    "width": 1,
                    "height": 1,
                    "fill": 
                        sub(r"\s+", " ", """
                        ${{
                            ({
                                destination: color.red, 
                                source: color.green, 
                                close: color.pink, 
                                expand: color.deepPurple,
                                generating: color.amber, 
                                'generating-new': color.amber, 
                                'generating-pruned': color.blueGrey, 
                                'dominated-by': color.amber, 
                                'relaxed-by': color.amber, 
                                solution: color.blue
                            })[$.type] ?? theme.accent
                        }}
                    """).strip(),
                    "alpha": 1,
                    "x": "${{ $.x }}",
                    "y": "${{ $.y }}",
                }
            ]
        }

    def pivot(self):
        return {"x": "${{ $.x + 0.5 }}", "y": "${{ $.y + 0.5 }}", "scale": 1}

    def serialise(self, current: search_node[grid_state]):
        [x, y] = current.state_
        return {"x": y, "y": x}


class graph_serialiser(domain_serialiser[vertex]):

    def views(self):
        return {
            "main": [
                {
                    "$if": "${{ $.type != 'stats' }}",
                    "$": "circle",
                    "radius": 1,
                    "fill": "${{ ({source: color.green, close: color.red, expand: color.orange, generate: color.yellow, solution: color.blue})[$.type] ?? theme.accent }}",
                    "alpha": 1,
                    "x": "${{ $.x }}",
                    "y": "${{ $.y }}",
                },
                {
                    "$": "path",
                    "fill": "${{ ({source: color.green, close: color.red, expand: color.orange, generate: color.yellow, solution: color.blue})[$.type] ?? theme.accent }}",
                    "points": [
                        {
                            "x": "${{ $.x }}",
                            "y": "${{ $.y }}",
                        },
                        {
                            "x": "${{ parent?.x ?? $.x }}",
                            "y": "${{ parent?.y ?? $.y }}",
                        },
                    ],
                    "line-width": 1,
                },
            ]
        }

    def pivot(self):
        return {"x": "${{ $.x }}", "y": "${{ $.y }}", "scale": 1}

    def serialise(self, current: search_node[vertex]):
        [x, y] = current.state_.get_location()
        return {"x": y, "y": x}


serialisers: dict = {
    "grid": grid_serialiser(),
    "n_puzzle": n_puzzle_serialiser(),
    "graph": graph_serialiser(),
}
