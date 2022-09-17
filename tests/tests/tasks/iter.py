from django.test import TestCase

from fox_tools.tasks import Task, Pool
from fox_tools.tasks.iter import IterTaskSet


class IterTaskSetTestCase(TestCase):
    def setUp(self):
        self.values = list(range(0,10))
        self.tasks = [Task(v, func=lambda *a, **kw: v)
                        for v in self.values]
        self.object = IterTaskSet('test', chunk_size=2, iter=iter(self.tasks))

    def test_submit_from_pool(self):
        pool = Pool()
        pool.submit(self.object)
        pool.run(keep_alive=True)

    def test_get_tasks(self):
        n = 0
        while n < len(self.values):
            result = [task.key for task, kw in self.object.get_tasks()]
            expected = self.values[n:n+2]
            self.assertEquals(result, expected)
            n += 2


