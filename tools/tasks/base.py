import concurrent.futures as futures
import time

from ..tool import Tool


__all__ = ('BaseTask', 'Task', 'TaskSet', 'task', 'wait')


class BaseTask:
    """
    Base class providing interface for tasks to be run by pool's
    executor.
    """
    key = None
    """ Task key """
    priority = 0
    """ Task priority, by lower first ran """
    futures = []
    """ Futures generated through submit calls """
    parent = None
    """ Parent task or task set. """
    scheduled = False
    """ True if task has been scheduled at least once. """

    @property
    def done(self):
        """ Return True if task is done. """
        return next((False for f in self.futures if not f.done()), True)

    def __init__(self, key, **kwargs):
        """
        Initialize task.

        :param key: task's key
        :param **kwargs: init attributes values (must be declared on class)
        """
        self.key = key
        self.futures = []
        self.__dict__.update({k:v for k,v in kwargs.items()
                                if hasattr(self, k)})

    def get_future(self, key, many=False):
        """ Return future by task key or None. If ``many``, return iterator. """
        gen = (f for f in self.futures if getattr(f, 'task_key') == key)
        return gen if many else next(gen, None)

    def results(self):
        """
        Yield results from futures that finished, as tuples of
        ```(task_key, future, exception or result)```.
        """
        for i, future in enumerate(self.futures):
            if future.done():
                try:
                    result = future.result()
                except Exception as err:
                    result = err
                yield (getattr(future, 'task_key', i), future, result)

    def run(self, *args, **kwargs):
        """ Method called by pool's executor. """
        raise NotImplementedError('run is not implemented by subclass')

    def submit(self, executor, key=None, func=None, **kwargs):
        """
        Submit task to executor returning future (also assigned to
        ``task.future``) or list of futures.

        This method add the `task_key` attribute to the future set to
        to provided `key` argument (defaults to `self.key`).
        """
        if key is None:
            key = self.key
        if func is None:
            func = self.run
        kwargs['key'] = key
        future = executor.submit(self.run, **kwargs)
        setattr(future, 'task_key', key)
        self.futures.append(future)
        self.scheduled = True
        return future


class Task(BaseTask):
    """ Single task. """
    func = None
    """ Function to call. """
    kwargs = None
    """ ``func`` arguments updated with run's kwargs. """
    this = None
    """ ``self`` argument passed to func if not None. """
    
    def __init__(self, key, func=None, kwargs=None, **kw):
        self.func = func
        self.kwargs = kwargs or {}
        super().__init__(key, **kw)

    def run(self, *args, throw=True, **kwargs):
        """
        Run the task. If ``self.func`` is provided, return its result.
        Otherwise raise ``NotImplementedError`` or return provided kwargs
        (if ``throw is False``). 
        """
        if not self.func:
            if throw:
                raise NotImplementedError('`func` must be passed to task '
                                          'or `run` method implemented')
            return kwargs

        kw, kwargs = kwargs, self.kwargs.copy()
        kwargs.update(kw)
        return self.func(self.this, *args, **kwargs) if self.this else \
               self.func(*args, **kwargs)

    @classmethod
    def decorate(cls, func, *args, key=None, **kwargs):
        """
        Create Task for provided func, and return. Set attribute
        `func.task` to the new object.
        """
        if key is None:
            key = func.__name__
        setattr(func, 'task', (cls, (key, func) + args, kwargs))
        return func


class TaskSet(BaseTask):
    """
    Run a set of sub-tasks by priority in the same pool task.

    Two ways to provide tasks: decorated methods using `@task` or
    similar, and at instance's init.
    """
    # TODO: sort tasks before get_tasks
    tasks = None
    """ Provided tasks. """

    def __init__(self, key, tasks=None, **kwargs):
        """
        :param key: task's key
        :param iterable tasks: set of tasks to execute
        """
        kwargs.pop('func', None)
        self.tasks = self.get_tasks_methods()
        if tasks:
            self.add(tasks)
        super().__init__(key, **kwargs)

    def get_tasks_methods(self):
        """ Get methods declared as task (using `@task`). """
        cls = type(self)
        if '__tasks' not in cls.__dict__:
            tasks = [getattr(f, 'task')
                     for f in (getattr(cls, k) for k in dir(cls))
                     if callable(f) and hasattr(f, 'task')]
            setattr(cls, '__tasks', tasks)

        tasks = [
            task_class(*args, this=self, **kwargs)
            for task_class, args, kwargs in getattr(cls, '__tasks')
        ]
        tasks.sort(key=lambda k: (k.priority, k.key))
        return tasks

    def add(self, tasks, sort=True):
        """ Add task(s) to set. """
        if isinstance(tasks, BaseTask):
            self.tasks.append(tasks)
        else:
            self.tasks.extend(tasks)
        if sort:
            self.tasks.sort(key=lambda k: (k.priority, k.key))

    def run(self, *args, task=None, **kwargs):
        """
        Run task or set's tasks (if `task is None`).
        :return dict by task key of task run's result.
        """
        if task:
            return {task.key: task.run(*args, **kwargs)}
        return {task.key: task.run(*args, **kw)
                  for task, kw in self.get_tasks(**kwargs)}

    def submit(self, executor, **kwargs):
        tasks = self.get_tasks(**kwargs)
        futures = [task.submit(executor, **kw)
                    for task, kw in tasks]
        self.futures.extend(futures)
        self.scheduled = True
        return futures

    def get_tasks(self, **kwargs):
        """ Get tasks. """
        key = kwargs.pop('key', self.key)
        for task in self.tasks:
            task_key = self.get_task_key(key=task.key, **kwargs)
            kw = {'key': task_key, 'parent': self}
            kw.update(kwargs)
            yield (task, kw)

    def get_task_key(self, key=None, **kwargs):
        """
        Return key for provided task. Default is ``taskset_key.task_key``.
        """
        return key

    def get_task(self, key, many=False):
        """
        Return task by key or None. If ``many`` is True, return
        iterator.
        """
        gen = (t for t in self.tasks if t.key == key)
        return gen if many else next(gen, None)

    def wait(self, *keys, **key_kwargs):
        """ Wait for tasks to be completed. """
        if key_kwargs:
            key_kwargs.pop('key', None)
            keys = (self.get_task_key(key, **key_kwargs)
                        for key in keys)

        for key in keys:
            future = self.get_future(key)
            if not future:
                print('>>>', [f.task_key for f in self.futures])
                raise RuntimeError("task's future {} not found".format(key))
            while True:
                if future.done():
                    break
                time.sleep(0)


def task(*args, task_class=Task, **kwargs):
    """
    Declare TaskSet's method as task using `Task.decorate`.

    `func` is excluded of provided Task's init arguments, since the
    decorated method is the one.

    :param key: Task's key
    :param *args: Task's init args
    :param **kwargs: Task's init kwargs

    """
    def decorator(func):
        return task_class.decorate(func, *args, **kwargs)
    return decorator


def wait(*task_keys, **wait_kwargs):
    """
    Decorator used to wait for task's future on the same TaskSet to be completed.
    It calls ``this.get_task_key(**wrapper_kwargs)`` in order to get
    futures' keys

    :param *task_keys: keys if tasks to wait.
    :param **wait_kwargs: ``wait_task``'s kwargs (excluding `parent`)
    """
    def decorator(func):
        def wrapper(*args, key=None, parent=None, **kwargs):
            if parent is None:
                raise ValueError('Missing `parent` task argument. '
                                 '`wait` decorator must be used inside TaskSet.')

            keys = [parent.get_task_key(key, **kwargs) for key in task_keys]
            parent.wait(*task_keys, **wait_kwargs)
            return func(*args, key=key, parent=parent, **kwargs)
        if hasattr(func, 'task'):
            setattr(wrapper, 'task', func.task)
        return wrapper
    return decorator

