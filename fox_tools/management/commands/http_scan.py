"""
Download data from remote server into files using provided urls template.
Urls are generated using provided variables.

Url are formatted using standard python `format` method.
Provided variables have this format: `[key][:type]?=[args],*`.

"""
import argparse
from datetime import datetime
import multiprocessing
import os

import requests

from django.core.management.base import BaseCommand

from fox_tools.combinations import Variable, Combinations
from fox_tools.tasks import Pool
from fox_tools.tasks.http_request import DownloadRequest
from fox_tools.tasks.iter import IterTaskSet


__all__ = ('Command',) 


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        
        group = parser.add_argument_group('urls')
        group.add_argument('-u', '--urls', metavar='URL', type=str, nargs='*',
            help='URL to get data from.', dest='urls' 
        )
        group.add_argument('-V', '--variables', type=str, nargs='*',
            help='Declare a variable used in the url generator')
        group.add_argument('--types', action='store_true',
            help='List variables types', dest='list_types')
        group.add_argument('--overwrite', action='store_true',
            help='Overwrite existing files')
        group.add_argument('--skip', action='store_true',
            help='Skip requests when file exists')

        group = parser.add_argument_group('request')
        group.add_argument('-H', '--headers', type=str, nargs='*',
            help='HTTP headers in `name:value` format.')
        group.add_argument('-m', '--method', type=str, nargs='?',
            default='GET', help='HTTP method')
        group.add_argument('-k', '--keep-all', action='store_true',
            help='Write file even when failure response code is returned')
        group.add_argument('-d', '--dir', type=str, nargs='?', dest='directory',
            default='./', help='Output directory')
        group.add_argument('-T', '--timeout', type=float, default=None,
            help="Request timeout (sec)")
        group.add_argument('--save-headers', action='store_true',
            help='Save responses\' headers', dest='save_headers')

        group = parser.add_argument_group('pool')
        group.add_argument('-w', '--workers', type=int,
            default=multiprocessing.cpu_count(),
            help="Number of concurrent workers (default: cpu count)")
        # group.add_argument('-v', '--var', type=str, nargs='?')

    def handle(self, urls=None, variables=None, list_types=False,
               workers=4, timeout=None,
               headers=None, **options):
        if list_types:
            self.print_vars_types()

        if not urls:
            return

        variables = [Variable.parse(v) for v in variables]
        # requests' options
        if headers:
            options['headers'] = {k.strip(): v.strip() for k, v in
                                    (h.split(':',1) for h in headers)}

        iter = self.iter(urls, variables, **options)
        key = datetime.now().strftime('scan_%Y-%m-%d_%H-%M-%S')
        task = IterTaskSet(key, iter)
        self.pool = Pool(max_workers=workers, task_timeout=timeout)
        self.pool.completed = lambda fut: self.completed(fut)
        self.pool.submit(task)
        self.pool.run(keep_alive=True)

    def print_vars_types(self):
        for func in Variable.get_types():
            print(func.var_type)
            if not func.__doc__:
                continue
            lines = func.__doc__.strip().split('\n')
            for line in lines:
                print('  ', line.strip())

    def completed(self, future):
        try:
            resp = future.result()['response']
            print('-', future.task_key, resp.status_code)
        except Exception as err:
            print('-', future.task_key, err)

    def iter(self, urls, variables, directory, overwrite=False, skip=False, **kwargs):
        urls = Combinations(urls, variables)
        session, session_counts, max_session_counts = requests.Session(), 0, 10
        
        for url in urls.iter():
            stream = self.get_stream_path(url, directory, overwrite, skip)
            if not stream:
                continue
            if session_counts >= max_session_counts:
                session.close()
                session, session_counts = requests.Session(), 0
            req = DownloadRequest(url, stream=stream, session=session, **kwargs)
            session_counts += 1
            yield req
        session.close()

    def get_stream_path(self, url, directory, overwrite=False, skip=False):
        basepath = url[url.find('://')+3:].replace('/','_')
        basepath  = os.path.join(directory, basepath)
        path = basepath
        exists = os.path.exists(path)
        if exists and skip:
            return
        if exists and not overwrite:
            i = 1
            while os.path.exists(path):
                path = basepath + '-' + str(i)
                i += 1
        return path

