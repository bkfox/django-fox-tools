from django.db import models

from .record_set import RecordSet


__all__ = ('ModelRecordSet',)


class ModelRecordSet(RecordSet):
    """
    Record set with features for pre-loading models from database..
    """
    lookup = None
    """
    Use this lookup field instead of index. It can either be a field name or
    a callable.

    When lookup is a callable, it takes the following signature:
        `lookup(queryset, indexes, items) -> QuerySet`
    """
    queryset = None
    """ Base queryset. """
    # delete = False
    # """ Delete items in db not found in read data """

    def __init__(self, index, model=None, lookup=None, queryset=None, **kwargs):
        if model is None:
            if queryset is None:
                raise ValueError('at least model or queryset must be provided')
            model = queryset.model
        elif model is not None and not issubclass(model, models.Model):
            raise ValueError('model must be a django Model class')

        self.lookup = lookup
        self.queryset = queryset or model.objects.all()
        super().__init__(index, model, **kwargs)

    def get_queryset(self, indexes=None, items=None):
        """
        Return queryset for provided indexes or items 
        """
        queryset = self.queryset
        lookup = self.lookup or self.index
        if not lookup or not (isinstance(lookup, str) or callable(lookup)):
            raise RuntimeError('lookup must be provided when index is not '
                               'a string, as a string or callable.')

        if indexes is None: 
            if items is None:
                raise ValueError('at least one of `indexes` and `items` must be '
                                 'a string')
            # get indexes of items that are not in self
            indexes = {index for index,_ in items if index not in self}

        if callable(lookup):
            return lookup(queryset, indexes, items)

        if len(indexes) > 1:
            lookup = lookup + '__in'
        return queryset.filter(**{lookup: indexes})

    def before_update_hook(self, items, override):
        if override:
            # if override, should not load from database
            return items

        queryset = self.get_queryset(items=items)
        in_db = {self.index_of(item): item for item in queryset}

        # change list in place
        for i in range(0,len(items)):
            index, item = items[i]
            if index in in_db:
                items[i] = (index, in_db.get(index))
        return items

