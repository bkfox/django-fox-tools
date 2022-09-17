from .record_set import RecordSet


__all__ = ('Pool',)

        
class Pool:
    """
    A Pool handle records indexed by a model-key and a record-key.
    A Record is either a `Record` instance or django model's one.
    """
    def __init__(self, record_sets=None):
        self.record_sets = dict(record_sets or {})

    def register(self, key, records, force=False):
        """ Register RecordSet for a specific key """
        if not force and key in self.record_sets:
            raise RuntimeError('there is already a records registered for key {}'
                                .format(key))
        self.record_sets[key] = records

    def get(self, key, pk=None):
        """ Get object(s) from pool. """
        record_set = self.record_sets.get(key)
        if record_set is None:
            return None
        return record_set if pk is None else record_set.get(pk)

    def index_of(self, key, item):
        return self.record_sets[key].index_of(item)

    def update(self, key, *args, **kwargs):
        kwargs['pool'] = self
        return self.record_sets[key].update(*args, **kwargs)

    def commit(self, key, *args, **kwargs):
        kwargs['pool'] = self
        return self.record_sets[key].commit(*args, **kwargs)

    def save(self, key, *args, **kwargs):
        return self.record_sets[key].save(*args, **kwargs)

    def __str__(self):
        return str(self.record_sets)

    def __contains__(self, key):
        return key in self.record_sets

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.register(key, value, force=True)

    def __delitem__(self, key):
        del self.record_sets[key]

    def __getattr__(self, key):
        if key in self.record_sets:
            return self.record_sets.get(key)
        return super().__getattr__(key)

