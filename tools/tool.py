import asyncio
import concurrent.futures as futures


__all__ = ('Tool',)


class Tool:
    def __init__(self, **kwargs):
        invalids = []
        for k, v in kwargs.items():
            if not hasattr(self, k):
                invalids.append(k)
            setattr(self, k, v)

        if invalids:
            raise AttributeError(', '.join(invalids))

    def log(self, item, *args, level='I', **kwargs):
        if isinstance(item, Exception):
            level = 'E'
            item = '{}: {}'.format(type(item), item)
            if args:
                item += '\n  - {}'.format(args)
            if kwargs:
                item += '\n  - {}'.format(kwargs)
        elif isinstance(item, str):
            item.format(**kwargs)
        print('[{}]'.format(level), item, *args)


