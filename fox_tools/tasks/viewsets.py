from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.response import Response
from .pool import Pool


__all__ = ('PoolViewSet',)


class PoolViewSet(viewsets.ViewSet):
    pool = None
    max_workers = 4

    def get_pool(self, create=False):
        if self.pool is None and create:
            self.pool = Pool(max_workers=self.max_workers)
        return self.pool

    @action(detail=False)
    def status(self, request):
        pool = self.get_pool()
        status = {
            'is_running': pool.is_running,
        }

        if pool:
            status['tasks'] = {
                key: { 'done': task.done,
                       'scheduled': task.scheduled,
                       'futures': [(f.task_key, f.done()) for f in task.futures] }
                for key, task in self.pool.tasks.items()
            }
        return Response(status)

