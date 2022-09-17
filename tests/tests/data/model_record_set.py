from django.test import TestCase

from tools.data import Record, ModelRecordSet
from . import samples
from ...models import NameValue


__all__ = ('ModelRecordSetTestCase',)


class ModelRecordSetTestCase(TestCase):
    values = samples.name_values

    @classmethod
    def setUpClass(cls):
        model_values = [NameValue(**vals)
                            for vals in cls.values[0]]
        for item in model_values:
            item.save()
        cls.model_values = model_values
        super(ModelRecordSetTestCase, cls).setUpClass()

    def setUp(self):
        self.record_set = ModelRecordSet('name', NameValue)

    def test_before_update_hook_override(self):
        models_by_id = {r.name: r for r in self.model_values}

        items = self.values[1]
        results = self.record_set.before_update_hook(
            list((self.record_set.index_of(item), item) for item in items),
            False)

        self.assertEquals(len(items), len(results))

        for i, (index, result) in enumerate(results):
            if isinstance(result, dict):
                self.assertNotIn(result['name'], models_by_id)
                self.assertIs(items[i], result)
            else:
                in_db = models_by_id[result.name]
                self.assertEquals(in_db, result)
