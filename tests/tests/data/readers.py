from django.test import TestCase

from rest_framework import serializers

from fox_tools.data import as_json_path, Pool, Reader, Readers, Record, RecordSet
from tests.models import NameValue
from tests.serializers import NameValueSerializer
from . import samples
from .reader import ReaderTestCase


__all__ = ('ReadersTestCase',)



class TestReader(Reader):
    index = None

    def __init__(self, index, *args, **kwargs):
        self.index = index
        super().__init__(*args, **kwargs)


class TestReaders(Readers):
    readers = {
        0: TestReader('name', serializer_class=NameValueSerializer, many=True),
        1: TestReader('value', many=True),
    }


class ReadersTestCase(TestCase):
    values = samples.name_values[0]

    def setUp(self):
        self.readers = TestReaders()
        self.pool = Pool({
            k: RecordSet(r.index)
                for k, r in self.readers.readers.items()
        })

    def test_read(self):
        results = self.readers.read(self.values, self.pool)
        for item in self.values:
            result = results.get(0, item['name'])
            self.assertEquals(item, result.data)

            result = results.get(1, item['value'])
            self.assertEquals(item, result.data)

    def test_get_record_set(self):
        obj = self.readers
        obj.record_sets = {'a': RecordSet('a'),
                           'b': (RecordSet, ('b',)),
                           'c': (RecordSet, {'index': 'c'}), }

        for key in obj.record_sets.keys():
            result = obj.get_record_set(key)
            self.assertIsInstance(result, RecordSet)
            self.assertEquals(result.index, key)

    def test_get_pool_record_set(self):
        obj = self.readers
        obj.record_sets = {'a': RecordSet('a'),
                           'b': RecordSet('b'), }

        pool = Pool({'b': RecordSet('b2')})
        result = obj.get_pool_record_set(pool, 'a')
        self.assertEquals(result.index, 'a')

        result = obj.get_pool_record_set(pool, 'b')
        self.assertEquals(result.index, 'b2')
