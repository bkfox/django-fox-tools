from django.test import TestCase
from rest_framework import serializers

from tools.data import Pool, Relation, Record, RecordSet
from tools.serializers import RelationalSerializer


__all__ = ('RelationalSerializerTestCase',)


class TestSerializer(RelationalSerializer):
    nested = serializers.DictField()
    relations = {'related': Relation(0, 'rel', '$.nested')}


class RelationalSerializerTestCase(TestCase):
    records = (
        Record(name='a', value=0),
        Record(name='b', value=1),
        Record(name='c', value=2),
    )
    values = (
        {'nested': {'rel': 'a'}},
        {'nested': {'rel': 'b'}},
        {'nested': {'rel': 'c'}},
    )

    def setUp(self):
        self.pool = Pool()
        self.pool.register(0, RecordSet('name'))
        self.pool.update(0, self.records)

    def test_resolve_relations(self):
        serializer = TestSerializer(pool=self.pool)
        for value in self.values:
            expected = self.pool.get(0, value['nested']['rel'])
            result = serializer.resolve_relations(value)
            self.assertEquals(expected, result.get('related'))

    def test_run_validation(self):
        serializer = TestSerializer(pool=self.pool)
        for value in self.values:
            expected = self.pool.get(0, value['nested']['rel'])
            result = serializer.run_validation(value)
            self.assertEquals(expected, result.get('related'))

