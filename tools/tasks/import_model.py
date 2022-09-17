import time
import threading

from django.core import serializers
from django.db import models, transaction
from django.utils.functional import cached_property

from .base import Task, TaskSet, task


__all__ = ('import_model', 'ImportModel', 'ImportModels')


def import_model(*args, **kwargs):
    """
    Shortcut for ``@task(*args, task_class=ImportModelTask, **kwargs)``.

    Key is mandatory in order to ease function naming.
    """
    kwargs['task_class'] = ImportModel
    return task(*args, **kwargs)


class ImportModel(Task):
    """
    Bulk import to provided target model (create/update). Declared tasks
    takes following attributes: `(source, context, target)`.
    """
    model = None
    """ Target model. """
    source_key = None
    """ Attribute name or callable on source. """
    target_key = None
    """ Attribute name on target. """
    skip_id_zero = True
    """ If True, skip instance with `not source_id` """
    locks = {}
    """
    [class attribute] Thread locks by model, in order to avoid SQL's
    `DeadLock` error.
    """
    lock = None
    """ Task's thread lock, set at init. """

    def __init__(self, key, func, model, source_key, target_key, **kwargs):
        self.model = model
        self.lock = type(self).locks.setdefault(model, threading.Lock())
        self.source_key = source_key
        self.target_key = target_key
        super().__init__(key, func, **kwargs)

    def _get_rel(self, obj, key, *args, **kwargs):
        if isinstance(key, str):
            return getattr(obj, key, None)
        return key(obj, *args, **kwargs)

    def source_rel(self, source, context):
        return self._get_rel(source, self.source_key, context)

    def target_rel(self, target):
        return getattr(target, self.target_key, None)

    def run(self, dataset, results, **kwargs):
        """
        Fetch objects from db for provided data set, create or update
        them.
        """
        # don't use key provided by kwargs in order to avoid splitting
        # results over data range (=> key = 'parent_key.data_range')
        key = self.key
        result = results.setdefault(key, {})
        model, func = self.model, self.func

        items = ((self.source_rel(item, results), item) for item in dataset)

        if self.skip_id_zero:
            items = tuple((k, item) for k, item in items if k)
        else:
            items = tuple(items)

        if not len(items):
            return {}

        ids = set(item[0] for item in items)
        self.acquire_lock(ids)
        try:
            with transaction.atomic() as atomic:
                queryset = model.objects.select_for_update(of=tuple()) \
                                .filter(**{self.target_key + '__in': ids })
                in_db = { self.target_rel(r): r for r in queryset }

                to_create, to_update = {}, {}
                for key_, item in items:
                    obj = in_db.get(key_, None) or to_create.get(key_, None)
                    target = super().run(source=item, results=results, target=obj,
                                            **kwargs)
                    if not target:
                        continue

                    setattr(target, self.target_key, key_)
                    if obj and key_ in in_db:
                        to_update[key_] = target
                    else:
                        to_create[key_] = target

                if to_create:
                    to_create = model.objects.bulk_create(to_create.values())
                    result.update({self.target_rel(r): r for r in to_create})
                    # miss row id here
                if to_update:
                    result.update({self.target_rel(r): r for r in to_update.values()})
                    for obj in to_update.values():
                        obj.save()
        finally:
            self.release_lock(ids)
        return result

    def acquire_lock(self, ids):
        return self.lock.acquire()

    def release_lock(self, ids):
        return self.lock.release()
        

class ImportModels(TaskSet):
    """
    Import items by chunk from provided dataset, using thread pool.

    It runs import methods declared on this class. To declare an import
    method, just use decorators provided in this module.

    Note/TODO: does not support multithread
    """
    dataset = None
    """ Dataset to import """
    chunk_size = 64
    """ Chunk size """

    def __init__(self, key, dataset=None, **kwargs):
        self.dataset = dataset
        super().__init__(key, **kwargs)

    @classmethod
    def split(cls, key, dataset, chunk_size=None, count=None, data_range=None,
                **init_kwargs):
        """
        Create multiple import task over dataset, split by chunk.
        """
        dataset = cls.get_dataset(dataset, data_range=data_range, slice=False)
        chunk_size = chunk_size or cls.chunk_size
        count = cls.count(dataset, count)
        for i in range(0, count, chunk_size):
            data_range = (i, i+chunk_size)
            task = cls('{}.{}'.format(key, i),
                       cls.get_dataset(dataset, data_range=data_range, slice=True),
                       **init_kwargs)
            yield task

    @classmethod
    def count(self, dataset, count=None):
        size = dataset.count() if isinstance(dataset, models.QuerySet) else \
                    len(dataset)
        return size if count is None else min(size, count)

    @classmethod
    def get_dataset(self, dataset, data_range=None, slice=True):
        if isinstance(dataset, models.QuerySet):
            dataset = dataset.all()
        if slice:
            if data_range is not None:
                dataset = dataset[data_range[0]:data_range[1]]
            else:
                dataset = dataset[:]
        return dataset

    def get_tasks(self, **kwargs):
        kwargs.setdefault('results', {})
        kwargs['dataset'] = self.dataset
        return super().get_tasks(**kwargs)

    def run(self, dataset, **kwargs):
        return super().run(dataset=self.dataset, **kwargs)

    @classmethod
    def load(cls, path=None, stream=None, **kwargs):
        if stream is None:
            stream = open(path, 'r')

        with stream:
            kwargs['dataset'] = list(serializers.deserialize('json', stream))
            return cls(**kwargs)

    def dumpdata(self, path=None, stream=None, count=None):
        """
        Dump data to file (by path or stream), to be used as fixture.
        """
        if stream is None:
            stream = open(path, 'w')
        if count is None:
            count = self.count
        with stream:
            serializers.serialize('json', self.dataset[:count],
                                  stream=stream)

