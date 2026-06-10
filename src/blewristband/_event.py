class Event:
    def __init__(self):
        self._handlers = []

    def __iadd__(self, handler):
        self._handlers.append(handler)
        return self

    def __isub__(self, handler):
        try:
            self._handlers.remove(handler)
        except ValueError:
            pass
        return self

    def __call__(self, *args):
        for h in self._handlers:
            h(*args)
