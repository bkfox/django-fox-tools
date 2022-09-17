from django.db import models
from .reader import as_json_path


__all__ = ('Relation',)


class Relation:
    """
    Describe a relation between a reference object and a related one
    (referred as "target"). Reference object can either be a model or
    data.

    Example from input data:

        ```
        data = {
            name: 'horse name',
            stable: 'stable name',
            trainer: { 'name': 'trainer name' },
            weight,
        }

        pool = {
            stables: { 'stable name': StableModel() }
            trainers: { 'trainer name': TrainerModel() }
        }
        ```

    Here:
    - key: 'trainers', 'stables'
    - source_field: 'name', 'stable'
    - nested path: '$.trainer', None
    
    Used to get the right foreign key to the reference, using provided
    pool.
    """
    def __init__(self, key, source_field, nested_path=None):
        self.key = key
        self.source_field = source_field
        self.nested_path = as_json_path(nested_path, True)

    def resolve(self, pool, data):
        """
        Resolve object from provided pool. Raise KeyError if not found,
        return None if no source info.
        """
        source = self.get_reference_data(data)
        if not source:
            return None
        pk = source.get(self.source_field)
        if pk is None:
            return None
        target = pool[self.key][pk]
        return target

    def get_reference_data(self, data):
        """ Get nested source object if any, or data """
        if isinstance(data, models.Model):
            data = data.__dict__
        if not self.nested_path:
            return data
        return next((m.current_value for m in self.nested_path.match(data)), None)

