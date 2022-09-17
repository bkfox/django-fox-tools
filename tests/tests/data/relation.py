from django.test import TestCase

from fox_tools.data import Pool, Relation, Record, RecordSet


__all__ = ('RelationTestCase',)


class RelationTestCase(TestCase):
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

    def test_get_reference_data(self):
        relation = Relation(0, 'rel', '$.nested.rel')
        for value in self.values:
            expected = value['nested']['rel']
            result = relation.get_reference_data(value)
            self.assertEquals(expected, result)

    def test_resolve(self):
        relation = Relation(0, 'rel', '$.nested')
        for value in self.values:
            expected = self.pool.get(0, value['nested']['rel'])
            result = relation.resolve(self.pool, value)
            self.assertEquals(expected, result)
    



