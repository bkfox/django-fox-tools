import time
from django.test import TestCase

from fox_tools.tasks import BaseTask, Pool, Task, TaskSet, task


__all__ = ('slow_fib', 'Base', 'TaskTestCase', 'TaskSetTestCase')


# Pool
def slow_fib(n, **kwargs):
    time.sleep(0.01)
    return 1 if n <= 1 else n * slow_fib(n-1)


class Base:
    class PoolTestCase(TestCase):
        pool = None
        tasks_count = 10
        
        def setUp(self):
            self.pool = Pool()

        def get_tasks(self, start=1, count=None, step=1):
            if count is None:
                count = self.tasks_count
            return [Task(i, slow_fib, {'n':i})
                    for i in range(start, start+count, step)]

        def test_get_futures(self):
            tasks = self.get_tasks()
            self.pool.submit(tasks)
            with self.pool.get_executor() as executor:
                futures = list(self.pool.get_futures(executor))
                expected_count = 0

                for task in tasks:
                    self.assertTrue(task.scheduled,
                        "task.scheduled is not True after Task.submit")
                    self.assertTrue(len(task.futures) > 0,
                        "task.futures is empty")
                    future = task.futures[0]
                    self.assertIsNotNone(getattr(future, 'task_key', None),
                        "future misses 'task_key' attribute")
                    expected_count += len(task.futures)

                self.assertEquals(len(futures), expected_count,
                    "get_futures results has not same length as tasks")

                
        def test_submit_run(self):
            tasks = self.get_tasks()
            self.pool.submit(tasks)

            for task in tasks:
                self.assertNotEquals(self.pool.tasks.get(task.key), None,
                    "task not added to pools' task list")

            self.pool.run()

            for task in tasks:
                self.assertEquals(task.done, True,
                    "task.done is not True after run")
                results = list(task.results())
                self.assertEquals(len(results), len(task.futures),
                    "task.results not the same length of task.futures")
            
        def test_submit_twice(self):
            tasks = self.get_tasks()
            self.pool.submit(tasks)
            first = self.pool.tasks.copy()

            tasks = self.get_tasks()
            self.pool.submit(tasks)
            second = self.pool.tasks.copy()

            self.assertEquals(first, second)


class TaskTestCase(Base.PoolTestCase):
    def test_submit_while_running(self):
        self.pool.submit(self.get_tasks())
        self.pool.submit(Task(-1, lambda **kw: self.pool.submit(
            Task(-2, slow_fib, {'n': 13})
        )))
        self.pool.run()

    def test_submit_multiple_while_running(self):
        def submit(values):
            for k, v in values:
                self.pool.submit(Task(k, slow_fib, {'n': v}))

        self.pool.submit(Task(0, lambda **kw: time.sleep(1)))
        self.pool.submit(Task(-1, lambda **kw: submit(
            ((i, i*2) for i in range(-2, 10))
        )))
        self.pool.submit(Task(-10, lambda **kw: submit(
            ((i, i*2) for i in range(0, 10))
        )))
        self.pool.run()


class TaskSetTestCase(Base.PoolTestCase):
    # TODO
    class TestSet(TaskSet):
        n_tasks_methods = 2
        
        @task()
        def slow_fib(self, n=1, **kwargs):
            # assert(isinstance(self, TestSet), "TestSet.slow_fib: self is not TestSet")
            return slow_fib(n, **kwargs)

        @task()
        def twice(self, n=1, **kwargs):
            # assert(isinstance(self, TestSet), "TestSet.twice: self is not TestSet")
            return n * 2

    
    def get_tasks(self, start=1, count=None, step=1):
        if count is None:
            count = self.tasks_count
        return [TaskSet(i, super(TaskSetTestCase, self).get_tasks(start, count, step),
                      keep_results=True) for i in range(start, count, step)]

    def test_tasks_methods(self):
        tasks = self.TestSet(0)

        methods = tasks.get_tasks_methods()
        self.assertEquals(len(methods), tasks.n_tasks_methods,
            "TaskSet.get_tasks_methods: missing tasks methods.")
        self.assertEquals(len(tasks.tasks), tasks.n_tasks_methods,
            "TaskSet.tasks: missing tasks methods (should be set at init).")

        for task in methods:
            func = getattr(tasks, task.key)
            self.assertEquals(func(n=2), task.run(n=2),
                "TaskSet.get_tasks_methods: returned task does not return "
                "same value as decorated method's result")
            
        results = tasks.run(n=2)
        self.assertEquals(len(results), tasks.n_tasks_methods,
            "TaskSet.run: wrong results count")

        

        # executor = self.pool.get_executor()
        # futures = tasks.submit(executor)
     

    def test_init_with_tasks(self):
        tasks = reversed(super(TaskSetTestCase, self).get_tasks(0,10))
        # test: add iterator + sort
        task = TaskSet(0, tasks)

        keys = [t.key for t in task.tasks]
        expected = list(range(0, 10))
        self.assertEquals(keys, expected,
            "tasks not ordered by key: {} != {}".format(keys, expected))

        low_priority_task = Task(10, priority=-10)
        task.add(low_priority_task)
        self.assertEquals(low_priority_task, task.tasks[0],
            "tasks not ordered by priority")

    def test_add_task(self):
        tasks = TaskSet(0)
        items = self.get_tasks()
        tasks.add(items[0])
        count = len(tasks.tasks)
        self.assertEquals(count, 1,
            "invalid items length ({} != 1)".format(count))
        
    def test_add_tasks_no_sort(self):
        tasks = TaskSet(0)
        items = self.get_tasks()
        tasks.add(items, sort=False)
        self.assertEquals(tasks.tasks, items,
            "items not the same as provided ones")
    
    def test_add_tasks_sort(self):
        tasks = TaskSet(0)
        items = self.get_tasks()
        r_items = reversed(items)
        tasks.add(items, sort=True)
        self.assertEquals(tasks.tasks, items,
            "items not ordered")

    def test_results(self):
        tasks = self.get_tasks()
        self.pool.submit(tasks)
        self.pool.run()

        for task in tasks:
            results = dict((k, r) for k, f, r in task.results())
            self.assertEquals(len(results), len(task.tasks),
                    "task.results is not the same length as `task.tasks`")
            for task_ in task.tasks:
                result = results.get(task_.key)
                expected = slow_fib(task_.key)
                self.assertNotEquals(result, None,
                    "missing result for task {}".format(task_.key))
                self.assertEquals(result, expected,
                    "invalid result for task {} ({} != {})".format(
                        task_.key, result, expected))

