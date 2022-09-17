from itertools import islice

from .base import Task, TaskSet


__all__ = ('IterTaskSet',)


class IterTaskSet(TaskSet):
    """
    Use iterator in order to generate tasks. TaskSet is submitted
    multiple time, as long as iterator is not exhausted.
    """
    iter = None
    """ Iterator over tasks """
    chunk_size = 20
    """ Number of tasks to take on ``submit``. """

    def __init__(self, key, iter, **kwargs):
        self.iter = iter
        super().__init__(key, **kwargs)

    def submit(self, *args, **kwargs):
        result = super().submit(*args, **kwargs)
        if self.iter is not None:
            self.scheduled = False
        return result

    _regular_tasks_taken = False

    def get_tasks(self, **kwargs):
        if not self._regular_tasks_taken:
            tasks = list(super().get_tasks(**kwargs))
            self._regular_tasks_taken = True
        else:
            tasks = []

        if self.iter is not None and len(tasks) < self.chunk_size:
            count = self.chunk_size - len(tasks)
            extra = [t for t in (self.from_iter(v, **kwargs)
                        for v in islice(self.iter, 0, count)) if t]
            if extra is None:
                self.iter = None
            else:
                tasks += extra
        return tasks

    def from_iter(self, value, **kwargs):
        """
        Return task from provided iter value. By default, consider value
        as a task.
        :returns: task or None
        """
        return (value, kwargs) if isinstance(value, Task) else None

