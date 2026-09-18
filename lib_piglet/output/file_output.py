from os import makedirs
from os.path import dirname
from lib_piglet.output.base_output import base_output


class file_output(base_output):
    def __init__(self, **kwargs):
        self.args = kwargs
        if "file" in self.args:
            directory = dirname(self.args["file"])
            if directory:
                makedirs(dirname(self.args["file"]), exist_ok=True)
            self.file = open(self.args["file"], "w")
        else:
            raise IOError("Output file not specified.")

    def verbatim(self, s: str):
        self.file.write(s)

    def event(self, **kwargs):
        self.verbatim(", ".join(f"{k}: {v}" for k, v in kwargs.items()) + "\n")

    def close(self):
        self.file.close()
