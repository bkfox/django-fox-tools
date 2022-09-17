import concurrent.futures as futures
import time

from ..tool import Tool
from . import BaseTask


__all__ = ('Pool',)



class Pool(Tool):
    """
    Pool managing multiple `Task`s over executor.
    """
    max_workers = 5
    """ Maximum number of concurrent workers. """
    task_timeout = None
    """ Task timeout in seconds. """

    executor = None
    """ Pool executor. """
    tasks = None
    """ Dict of tasks by key. """

    @property
    def is_running(self):
        """True if pool is running""" 
        return self.executor is not None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.tasks:
            self.tasks = {}
        self.executor = None

    def get_task(self, key):
        """ Return task by key or None. """
        return self.tasks.get(key)

    def submit(self, tasks):
        """
        Add tasks to be executed by pool as: BaseTask instance or
        iterable of BaseTasks.
        """
        if isinstance(tasks, BaseTask):
            self.tasks.setdefault(tasks.key, tasks)
            return self.tasks.get(tasks.key)
        tasks = ((task.key, task) for task in tasks
                    if task.key not in self.tasks)
        self.tasks.update(tasks)
        return (self.tasks.get(task.key) for task in tasks)

    def shutdown(self):
        """ Shutdown executor and clear tasks. """
        self.executor.shutdown(cancel_futures=True)
        self.executor = None
        # TODO: clean up tasks

    def run(self, keep_alive=False, **context):
        """
        Run submitted tasks.

        :param bool keep_alive: if true, await for new tasks when there
            is no more tasks available.
        :param **context: context passed to tasks through `get_context()`.
        """
        if self.executor:
            raise RuntimeError('pool is already running')
        
        context = self.get_context(**context)
        self.executor = self.get_executor(**context)
        with self.executor as executor:
            context['executor'] = executor
            context['wait'] = keep_alive 
            while True:
                futs = list(self.get_futures(**context))
                if not futs:
                    break
                futs = futures.as_completed(futs, timeout=self.task_timeout)
                for future in futs:
                    try:
                        self.completed(future)
                        future.result()
                    except Exception as err:
                        self.log(err, task=getattr(future, 'task_key', None))
                        import traceback
                        traceback.print_exc()
                        raise
        self.executor = None

    def get_executor(self, **context):
        return futures.ThreadPoolExecutor(max_workers=self.max_workers)

    def get_context(self, **kwargs):
        """
        Provide context to tasks based on `**kwargs`.

        Pool class provides following context values:
        - `pool`: Pool instance running tasks (self);
        """
        kwargs.setdefault('pool', self)
        return kwargs

    def get_futures(self, executor, wait=False, **kwargs):
        """
        Submit unscheduled tasks to executor and return iterator over
        generated futures.
        """
        tasks = list(self.get_tasks(**kwargs))
        if wait and not tasks:
            while not tasks:
                if not self.is_running:
                    return
                time.sleep(0.01)
                tasks = list(self.get_tasks(**kwargs))

        for task in tasks:
            futs = task.submit(executor, **kwargs)
            if not futs:
                continue
            if isinstance(futs, futures.Future):
                yield futs
            else:
                for future in futs:
                    yield future

    def get_tasks(self, **kwargs):
        return (task for task in self.tasks.values() if not task.scheduled)

    def _await_task(self):
        """
        Loop await tasks to come. Return True if any, False if pool
        stopped.
        """
        while not self.tasks and self.is_running:
            time.sleep(0)
        return self.is_running

    def completed(self, task):
        # FIXME: gc.collect() on completed
        pass


