from django.test import TestCase
from tools.serializers import Unsafe, MapField #, NestedField


class MapFieldTestCase(TestCase):
    def setUp(self):
        self.map = {'a':1, 'b':2, 'c': 3}
        self.field = MapField(map=self.map, default=None)

    def test_to_representation_no_default(self):
        field = MapField(map=self.map)
        self.assertEquals(field.to_representation('a'), 1)
        self.assertIsNone(field.to_representation('z')) 

    def test_to_representation_with_default(self):
        field = MapField(map=self.map, default='c')
        self.assertEquals(field.to_representation('a'), 1)
        self.assertEquals(field.to_representation('z'), self.map['c']) 

    def test_to_internal_value_no_default(self):
        field = MapField(map=self.map) 
        self.assertEquals(field.to_internal_value(1), 'a')
        self.assertIsNone(field.to_internal_value(-1)) 

    def test_to_internal_value_with_default(self):
        field = MapField(map=self.map, default='c') 
        self.assertEquals(field.to_internal_value(1), 'a')
        self.assertEquals(field.to_internal_value(-1), 'c') 

    def test_to_internal_value_keep_unsafe(self):
        field = MapField(map=self.map, keep_unsafe=True) 
        self.assertEquals(field.to_internal_value(1), 'a')
        self.assertEquals(field.to_internal_value(-1), Unsafe(-1)) 


# class NestedFieldTestCase(TestCase):
#     def setUp():
#         self.object = {'a': {'1': 1, '2': 2}, 'b': 3}
# 
#     def test_to_internal_value(self):
#         field = NestedField('a::1', serializer.IntegerField())
#         self.assertEquals(field.to_internal_value(self.object), self.object['a']['1'])
        
