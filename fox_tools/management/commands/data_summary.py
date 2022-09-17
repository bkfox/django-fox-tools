""" From data files, compile values summary. """
import argparse
import json
import math
import multiprocessing
import os
import sys

from django.core.management.base import BaseCommand
from fox_tools.data import DataReader
from fox_tools.tasks import Task, Pool


__all__ = ('DataSummary',)


class Summary(Task):
    files = None
    readers = None
    dest = None

    def run(self, *args, dest=None, **kwargs):
        if dest is None:
            dest = self.dest

        for path in self.files:
            if not os.path.exists(path):
                print("[W] File does not exists:", path, file=sys.stderr)
                continue
            try:
                if os.path.isdir(path):
                    for p in os.listdir(path):
                        p = os.path.join(path, p)
                        self.read_file(p, dest)
                else:
                    self.read_file(path, dest)
            except Exception as err:
                print('[E]', path, err, file=sys.stderr)
        return dest

    def read_file(self, path, dest):
        if not os.path.exists(path):
            return
        with open(path,'r') as file:
            data = json.load(file)
            for key, reader in self.readers.items():
                result = dest.setdefault(key, [])
                values = reader.read(data)
                if isinstance(values, (tuple,list)):
                    for value in values:
                        if value not in result:
                            result.append(value)
                elif values not in result:
                    result.append(values)
            return dest


class Command(BaseCommand):
    help = __doc__
    
    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter

        group = parser.add_argument_group('file')
        parser.add_argument('-k', '--keys', type=str, nargs='+',
            help='Path to target elements to summarize.')
        parser.add_argument('files', metavar='FILE', type=str, nargs='+',
            help='Read values from those files')

        group = parser.add_argument_group('pool')
        group.add_argument('-w', '--workers', type=int,
            default=multiprocessing.cpu_count(),
            help="Number of concurrent workers (default: cpu count)")

    def handle(self, files, keys, workers, **kwargs):
        readers = {k: DataReader(k, k) for k in keys}
        results = {}
        
        count = math.floor(len(files) / workers) + 1
        pool = Pool(max_workers=workers)
        workers = (Summary(i, files=files[i*count:(i+1)*count], readers=readers,
                            dest=results, many=True) for i in range(0, workers))
        pool.submit(workers)
        pool.run()
        for k, v in results.items():
            print(k, ': ', v)

