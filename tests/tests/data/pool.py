from django.test import TestCase

from fox_tools.data import Record, RecordSet, Pool
from .record_set import RecordSetTestCase


class PoolTestCase(TestCase):
    values = RecordSetTestCase.values
    
    def setUp(self):
        self.pool = Pool()
        self.records = tuple(RecordSet('name', records=(r.clone() for r in vals))
                             for vals in self.values)

    def test_register(self):
        for key, records in enumerate(self.records):
            self.pool.register(key, records)
            with self.assertRaises(RuntimeError):
                self.pool.register(key, records)

            result = self.pool.get(key)
            self.assertEquals(records, result)

    def test_get(self):
        for key, records in enumerate(self.records):
            self.pool.register(key, records)
            result = self.pool.get(key)
            self.assertIs(records, result)

        result = self.pool.get(len(self.records))
        self.assertIsNone(result)

    def test_get_object(self):
        for key, records in enumerate(self.records):
            self.pool.register(key, records)
            for index, record in records.items():
                result = self.pool.get(key, index)
                self.assertEquals(record.data, result.data)
