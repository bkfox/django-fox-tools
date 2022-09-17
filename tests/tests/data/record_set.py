from django.test import TestCase

from fox_tools.data import Record, RecordSet
from . import samples


class TestRecordSet(RecordSet):
    before_update = False
    after_update = False
    
    def before_update_hook(self, items, **kw):
        self.before_update = True
        return items

    def after_update_hook(self, items, **kw):
        self.after_update = True
        return items


class RecordSetTestCase(TestCase):
    values = [[Record(**kw) for kw in name_values]
                for name_values in samples.name_values]

    def setUp(self):
        records = (r.clone() for r in self.values[0])
        self.records = TestRecordSet('name', records=records)

    def test_index_of(self):
        for record in self.values[0]:
            index = self.records.index_of(record)
            self.assertEquals(index, record.name)

    def test_index_of_dict(self):
        for record in self.values[0]:
            index = self.records.index_of(record.data)
            self.assertEquals(index, record.name)

    def test_index_of_index_callable(self):
        self.records.index = lambda r: r.value
        for record in self.values[0]:
            index = self.records.index_of(record)
            self.assertEquals(index, record.value)

    def test_commit_new_record(self):
        record = Record(name='a2', value=3)
        result = self.records.commit(record)
        self.assertIs(record, result)
        self.assertFalse(self.records.record_updated(result))

    def test_commit_new_dict(self):
        record = Record(name='a2', value=3)
        result = self.records.commit(record)
        self.assertIsInstance(result, self.records.model)
        self.assertEquals(record.data, result.data)

    def test_commit_update_record(self):
        for record in self.values[1]:
            if record in self.records:
                result = self.records.commit(record)
                self.assertEquals(record.data, result.data)

    def test_commit_update_dict(self):
        for record in self.values[1]:
            if record in self.records:
                result = self.records.commit(record.data)
                self.assertEquals(record.data, result.data)

    def test_commit_update_override(self):
        for record in self.values[1]:
            if record in self.records:
                result = self.records.commit(record, override=True)
                self.assertIs(record, result)

    def test_update_records(self):
        self.records.update(r for r in self.values[1] if r in self.records)
        self.assertEquals(len(self.values[0]), len(self.records))
        self.assertTrue(self.records.before_update)
        self.assertTrue(self.records.after_update)
        for record in self.values[1]:
            if record not in self.records:
                continue
            result = self.records.get(record.name)
            self.assertEquals(record.data, result.data)
            self.assertTrue(self.records.record_updated(result),
                            'record: {}'.format(record.data))
            
    def test_update_dict(self):
        self.records.update({r.name: r for r in self.values[1]})
        for record in self.values[1]:
            result = self.records.get(record.name)
            self.assertEquals(record.data, result.data)

    def test_update_keyed(self):
        self.records.update(((r.name, r) for r in self.values[1]), keyed=True)
        for record in self.values[1]:
            result = self.records.get(record.name)
            self.assertEquals(record.data, result.data)

    def test_remove(self):
        for record in self.values[1]:
            self.records.remove(record)
            self.assertFalse(record.name in self.records)

    def test_save(self):
        self.records.update(r for r in self.values[1] if r in self.records)
        for record in self.records.values():
            is_updated = record.name in self.records
            self.assertEquals(is_updated, self.records.record_updated(record),
                              'record: {}'.format(record.data))
        self.records.save()
        for record in self.records:
            self.assertFalse(self.records.record_updated(record))

    def test_contains(self):
        for record in self.values[0]:
            self.assertTrue(record.name in self.records)
            self.assertFalse(record.value in self.records)
            self.assertTrue(record in self.records)
