import copy
from django.db import models, transaction
from .record import Record


__all__ = ('RecordSet',)


class RecordSet:
    """
    Set of indexed records with commit system used to keep instances
    of provided model (django's `Model` or `Record`). Provide interface
    similar to dict and manipulation facilities.
    """
    # TODO: override operators: + - | & 
    
    def __init__(self, index, model=Record, records=None, relations=None):
        self.index = index
        self.model = model
        self.records = {}
        self.relations = relations
        if records:
            self.update(records)

    @staticmethod
    def get_item_data(item):
        """
        Get items' data as a dict of `{key, value}`. Item can either
        be a Record, django Model, a dict or an iterable of `(key, value)`.
        """
        if isinstance(item, models.Model):
            # FIXME: it uses Django's internal API: concrete_fields
            return {field.name: getattr(item, field.name)
                    for field in item._meta.concrete_fields
                        if hasattr(item, field.name)}
        elif isinstance(item, Record):
            return item.data
        elif isinstance(item, dict):
            return item
        elif hasattr(item, '__iter__') and not isinstance(item, str):
            return dict(item)
        raise ValueError('item must be a Record, a Django Model, a dict '
                         'or an iterable of `key,value`')

    @staticmethod
    def record_updated(item):
        """
        Return True if provided item has been created or updated since last
        saved/fetched from db.
        """
        if isinstance(item, models.Model) and getattr(item, 'pk', None) is None:
            return True
        return getattr(item, '_pool_updated', False)

    def is_updated(self, key):
        """
        Return True if element at provided position has been updated.
        Return None if no item has been found.
        """
        item = self.records.get(key)
        return item and self.record_updated(item)

    def index_of(self, item):
        """ Return index for the provided item. """
        if self.index == None:
            return None
        if isinstance(item, dict):
            item = Record(data=item)
        if callable(self.index):
            return self.index(item)
        return getattr(item, self.index, None)

    def resolve(self, pool, item):
        """ Resolve relations for provided item's data """
        if not self.relations:
            return
        relations = self.relations.items() if isinstance(self.relations, dict) else \
                        self.relations
        for field, relation in relations:
            target = relation.resolve(pool, item)
            # Only update when target has been found, otherwise leave field
            # as is.
            if target is not None:
                item[field] = target

    def commit(self, item, key=None, override=False, pool=None):
        """
        Update or insert a single item into records. Item can be one of:
        django Model, Record, dict or iterable of attributes' `(key,value)`.

        Resolve declared relations for item if pool is provided.

        :param Item item: item to update or insert
        :param Key key: item's index key (default: `self.index_o(item)`)
        :param bool override: override existing item in set.
        :param Pool pool: if provided, resolve item's relations using this pool
        :return updated/inserted item.
        """
        key = key or self.index_of(item)
        target = self.records.get(key)
        if target is None or override:
            if not isinstance(item, (models.Model,Record)):
                if pool:
                    self.resolve(pool, item)
                model = self.model
                if issubclass(model, models.Model):
                    item = {k: v for k,v in item.items()
                            if hasattr(model, k)}
                item = self.model(**item)
            # FIXME: if model or item, clone it
            self.records[key] = item
            target = item
        else:
            item = self.get_item_data(item)
            if pool:
                self.resolve(pool, item)
            try:
                for key, value in item.items():
                    setattr(target, key, value)
            except:
                print('error', self.model, key, item)
                raise
            setattr(target, '_pool_updated', True)
        return target

    def update(self, items, keyed=False, override=False, pool=None):
        """
        Update record set with provided records which can be an iterable
        of records, or a dict of records (by insert/update key in this case).

        Flowchart:
            - `before_update_hook` if provided
            - `self.commit(item,key,override,pool)`
            - `after_update_hook` if provided

        Hook methods should have the following signature:
            `_update_hook([(index,item], override=override) -> [(index,item)]` 

        :param Items records: records (or data) to insert or update
        :param bool keyed: provided records is an iterable of `(key,item)` if True
        :param bool override: override existing records if True
        :param Pool pool: if provided, resolve item's relations using this pool
        """
        if not keyed and not isinstance(items, dict):
            items = ((self.index_of(item), item) for item in items)
        if isinstance(items, dict):
            items = items.items()
        if hasattr(self, 'before_update_hook') or \
                hasattr(self, 'after_update_hook'):
            items = list(items)

        if hasattr(self, 'before_update_hook'):
            items = self.before_update_hook(items, override=override)

        items = [self.commit(item, key=key, override=override, pool=pool)
                    for key, item in items]

        if hasattr(self, 'after_update_hook'):
            items = self.after_update_hook(items, override=override)

        return items
        
    def remove(self, item):
        """ Remove record using index of item """
        key = self.index_of(item)
        if key in self.records:
            del self.records[key]

    def save(self, *args, **kwargs):
        """
        Save objects that have been updated or created for the provided
        model key, in a single atomic transaction.
        """
        with transaction.atomic():
            for record in self.records.values():
                if self.record_updated(record):
                    record.save(*args, **kwargs)
                    setattr(record, '_pool_updated', False)

    # ---- dict like accessors
    def get(self, key):
        return self.records.get(key)

    def keys(self):
        """ Return an iterator over items' keys. """
        return self.records.keys()
        
    def values(self):
        """ Return an iterator over items. """
        return self.records.values()

    def items(self):
        """ Return an iterator over `(key,item)`. """
        return self.records.items()

    def pop(self, key, default=None):
        return self.records.pop(key, default)

    def clone(self):
        """ Clone self """
        clone = copy.copy(self)
        if self.records:
            clone.records = dict(self.records)
        return clone

    def __iter__(self):
        """ Iterate over values. """
        return iter(self.values())

    def __getitem__(self, key):
        return self.records[key]

    def __setitem__(self, key, value):
        self.records[key] = value

    def __delitem__(self, key):
        del self.records[key]

    def __len__(self):
        return len(self.records)

    def __contains__(self, key):
        if isinstance(key, (models.Model, Record)):
            key = self.index_of(key)
        return self.records.__contains__(key)

    def __str__(self):
        return 'RecordSet({}, {})'.format(self.index, self.records)

    def __repr__(self):
        return 'RecordSet({}, {})'.format(self.index, self.records)

    # ---- TODO: operators

