

__all__ = ('Record',)


class Record:
    """ Pool record when no object is provided. """
    data = None
    _pool_updated = False

    def __init__(self, data=None, **attrs):
        if attrs:
            self.data = attrs
            data and self.data.update(data)
        elif data:
            self.data = data

    def clone(self):
        """ Clone record """
        return type(self)(**self.data)

    def save(self, *args, **kwargs):
        """ Save record """
        pass

    def __getattr__(self, key):
        if key in self.data:
            return self.data[key]
        return super().__getattr__(key)

    def __setattr__(self, key, value):
        if not hasattr(type(self), key):
            self.data[key] = value
        return super().__setattr__(key, value)
