class base_output:
    def __init__(self, **kwargs):
        pass

    def verbatim(self, s: str):
        pass

    def head(self, **kwargs):
        pass

    def event(self, **kwargs):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()
