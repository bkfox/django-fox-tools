from django.test import TestCase

from rest_framework import serializers

from fox_tools.data import as_json_path, Reader, Record
from tests.models import NameValue
from tests.serializers import NameValueSerializer
from . import samples


class FunctionsTestCase(TestCase):
    def test_as_json_path_from_str(self):
        as_json_path('$.*')

    def test_as_json_path_from_json_path(self):
        path = as_json_path('$.*')
        as_json_path(path)

    def test_as_json_path_from_none_allowed(self):
        as_json_path(None, allow_none=True)

    def test_as_json_path_raise(self):
        with self.assertRaises(ValueError):
            as_json_path(None)
        with self.assertRaises(ValueError):
            as_json_path(13)


class ReaderTestCase(TestCase):
    values = samples.name_values
    nested_values = samples.nested_values

    def setUp(self):
        self.reader = Reader(serializer_class=NameValueSerializer)

    def test_model(self):
        model = self.reader.model
        self.assertEquals(NameValue, model)

    def test_model_none(self):
        self.reader.serializer_class = None
        model = self.reader.model
        self.assertIsNone(model)

    def test_read_with_serializer(self):
        for items in self.values:
            for data in items:
                result = self.reader.read(data)
                self.assertIsInstance(result, NameValueSerializer)
                self.assertEquals(data, result.validated_data)

    def test_read_with_serializer_many_force_data(self):
        for items in self.values:
            result = self.reader.read(items, many=True, force_data=True)
            self.assertIsInstance(result, list)
            self.assertTrue(len(items), len(result))
            self.assertEquals(items, result)

    def test_read_with_path(self):
        for items in self.nested_values:
            expected = [r['a'] for r in items]
            result = self.reader.read(items, path=as_json_path('$.*.a'), many=True,
                                      force_data=True)
            self.assertEquals(expected, result)

    def test_get_data(self):
        for items in self.nested_values:
            result = self.reader.get_data(items, as_json_path('$.*.a'))
            self.assertEquals(items[0], result)

    def test_get_data(self):
        for items in self.nested_values:
            expected = [r['a'] for r in items]
            result = self.reader.get_data(items, as_json_path('$.*.a'), many=True)
            self.assertEquals(expected, result)

    def test_get_serializer(self):
        for items in self.values:
            self.reader.serializer_kwargs = {'many':True}
            serializer = self.reader.get_serializer(items)
            self.assertIsNotNone(serializer)
            self.assertTrue(serializer.many)


