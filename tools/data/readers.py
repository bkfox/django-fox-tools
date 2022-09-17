from .reader import BaseReader, Reader
from .record import Record
from .record_set import RecordSet
from .pool import Pool


__all__ = ('Readers',)


class Readers(Reader):
    """
    Handle reading data using multiple readers, read data are put in
    instance's data pool

    At init, class populate pool with records:
    - taking from provided ones
    - cloning from class `records` attribute
    - generate default one using declared readers, with arguments
        `(index='pk', model=reader.model)`
    """
    readers = None
    """ Readers, as dict/iterable of `{key, BaseReader}`. """
    record_sets = None
    """
    RecordSet to be registered on pool, as dict of `{key: record_set}}`.
    Where `record_set` can be
    - RecordSet instance
    - `(record_set_class, [args])`: (as in `*args`)
    - `(record_set_class, {args})`: (as in `**kwargs`)
    """

    def __init__(self, readers=None, *args, **kwargs):
        """
        :param {key:Reader} readers: use those readers instead of class' ones
        :param Pool pool: provide initial pool
        """
        if readers is not None:
            self.readers = readers
        super().__init__(*args, **kwargs)

    def read(self, data, pool, *args, **kwargs):
        """
        Read over data using declared readers, returning data pool.

        :param any data: input data
        :param Pool pool: record set pool to store results to;
        :param **kwargs: pass down arguments to `reader.read()`;
        :returns pool with results
        """
        many = kwargs.pop('many', None)
        data = super().read(data, many=False, **kwargs)

        readers = self.readers
        if isinstance(readers, dict):
            readers = readers.items()

        for key, reader in readers:
            try:
                self.read_one(key, data, reader, pool, **kwargs)
            except:
                print('Error on reader', key, reader)
                raise
        return pool

    def read_one(self, key, data, reader=None, pool=None, save=False, **kwargs):
        """
        Read data for one provided reader. Update pool with results, based
        on provided key.

        If save is True, save newly inserted items.

        Flowchart:
        - ``get_pool_record_set(pool, key)``: if pool provided
        - ``reader.read(data, pool, **kwags)``
        - ``pool.update``: if pool provided
        - ``pool.save``: if pool provided and save
 
        :param Key key: pool result key, and reader key if none provided;
        :param any data: data to read;
        :param Reader reader: use this reader to read data;
        :return reader's `read` return as data.
        """
        if reader is None:
            reader = self.readers.get(key)
        if reader is None:
            raise ValueError('reader must be provided through `self.readers` '
                             'or `reader` argument')
        if pool:
            self.get_pool_record_set(pool, key)

        kwargs['force_data'] = True
        data = reader.read(data, pool=pool, **kwargs)
        if data and pool and key in pool:
            if reader.many:
                data = pool.update(key, data)
            else:
                data = pool.commit(key, data)
            if save:
                pool.save(key)
        return data

    def get_pool_record_set(self, pool, key):
        """
        Get record set registered in pool, create and registering it if not.

        :param Pool pool
        :param Key key
        :returns RecordSet instance for the provided key.

        Flowchart (if key not in pool):
        - ``get_record_set(pool)``
        - ``pool.register(key, record_set)``
        """
        if key not in pool:
            record_set = self.get_record_set(key)
            record_set is not None and pool.register(key, record_set)
        return pool[key]

    def get_record_set(self, key):
        """ Return record set instance for provided key. """
        if not self.record_sets:
            return None
            
        record_set = self.record_sets.get(key)
        if isinstance(record_set, RecordSet):
            record_set = record_set.clone()
        elif isinstance(record_set, (tuple,list)):
            set_class, args = record_set
            record_set = set_class(**args) if isinstance(args, dict) else \
                            set_class(*args)
        elif record_set and not isinstance(record_set, RecordSet):
            raise ValueError('invalid record set description for key {}'
                                .format(key))
        return record_set


    # ---- dict like interface
    def get(self, key):
        return self.readers.get(key)

    def keys(self):
        """ Return an iterator over items' keys. """
        return self.readers.keys()
        
    def values(self):
        """ Return an iterator over items. """
        return self.readers.values()

    def items(self):
        """ Return an iterator over `(key,item)`. """
        return self.readers.items()

    def pop(self, key, default=None):
        return self.readers.pop(key, default)

    def __iter__(self):
        return iter(self.readers)

    def __getitem__(self, key):
        return self.readers[key]

    def __setitem__(self, key, value):
        self.readers[key] = value

    def __delitem__(self, key):
        del self.readers[key]

    def __len__(self):
        return len(self.readers)

    def __contains__(self, key):
        return key in self.readers

    def __str__(self):
        return 'RecordSet({}, {})'.format(self.index, self.readers)

    def __repr__(self):
        return 'RecordSet({}, {})'.format(self.index, self.readers)

