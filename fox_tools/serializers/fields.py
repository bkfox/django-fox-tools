import math

from django.utils.functional import cached_property
from rest_framework import serializers

__all__ = ('Unsafe', 'is_unsafe',
           'MapField', 'IntegerField', 'IntReprField', 'FloatField',
           'TimerField')


class Unsafe:
    """ Tag value as unsafe. """
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def __eq__(self, other):
        return self.value == other.value if isinstance(other, Unsafe) else other


def is_unsafe(value):
    """ Return True if value is unsafe. """
    return isinstance(value, Unsafe)


class MapField(serializers.Field):
    """ Field mapping value to representation and vice-verse. """
    map = {}
    """ Values mapping as {value: representation} """
    keep_unsafe = False
    """
    Wrap values into ``Unsafe`` when not matched to map instead of
    returning default.
    """

    def __init__(self, *args, map=None, keep_unsafe=False, **kwargs):
        self.map = map
        self.keep_unsafe = keep_unsafe
        kwargs.setdefault('default', None)
        super().__init__(*args, **kwargs)

    @cached_property
    def reversed_map(self):
        return {v:k for k,v in self.map.items()}

    def to_representation(self, value):
        if value in self.map:
            return self.map[value]
        return self.map.get(self.default)

    def to_internal_value(self, data):
        if data in self.reversed_map:
            return self.reversed_map[data]
        return Unsafe(data) if self.keep_unsafe else self.default


# class NestedField(Visitor, serializers.Field):
#     """ Value inside a nested object. """
#     field = serializers.CharField(required=False,default=None)
#         
#     def __init__(self, key, field=None, **kwargs):
#         self.field = field
#         self.key = key
#         super().__init__(*args, **kwargs)
# 
#     def to_representation(self, value):
#         # TODO: implement?
#         return None
# 
#     def to_internal_value(self, data):
#         data = self.get_data_node(self.key, data, normalize_key=False) 
#         return self.field.to_internal_value(data)


class IntegerField(serializers.IntegerField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                return int(data)
            except:
                return self.default
        return super().to_internal_value(data)


class IntReprField(serializers.IntegerField):
    def to_internal_value(self, value):
        if isinstance(value, str):
            value = ''.join(c for c in value if c.isdigit())
        return super().to_internal_value(value)


class FloatField(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                return float(data)
            except:
                return self.default
        return super().to_internal_value(data)


class TimerField(serializers.Field):
    """ String with format like `MM"SS'MS` into milliseconds """
    def to_representation(self, value):
        m = math.floor(value / 60000)
        s = math.floor(value / 1000)
        ms = value-m-s
        return str(m) + "'" + str(s) + '"' + str(ms)
    
    def to_internal_value(self, data):
        if not isinstance(data, str) or "'" not in data:
            return
        m, s = data.split("'")
        s, ms = s.split('"')
        return int(m)*60*1000 + int(s)*1000 + int(ms)



