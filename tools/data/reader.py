from django.db import models
from jsonpath2.path import Path as JSONPath


from .record import Record
from .record_set import RecordSet


__all__ = ('as_json_path', 'BaseReader', 'Reader')


def as_json_path(path, allow_none=False):
    """ Return provided path as json path """
    if isinstance(path, str):
        return JSONPath.parse_str(path)
    elif isinstance(path, JSONPath):
        return path
    elif allow_none and path is None:
        return None
    raise ValueError('invalid path {} (type: {})'.format(path, type(path)))


class BaseReader:
    """
    Base class for data reader.

    A reader is used to deserialize data and process eventual complexe data
    update and manipulation.
    """
    path = None
    """ JsonPath to get target data from. """
    many = False
    """ If True, expect multiple data target """

    def __init__(self, path=None, many=False):
        self.path = as_json_path(path, True)
        self.many = many

    def read(self, data, path=None, many=None, **kwargs):
        """
        Read data: extract it from provided (parsed) object.

        :param dict|list|[] data: source data
        :param JSONPath path: override self.path;
        :param **kwargs: passed down to ``get_serializer``.
        :returns extracted data

        Flowshart:
            - ``get_data(data, path, **kwargs)``
        """
        if path is None: path = self.path
        if many is None: many = self.many
        return self.get_data(data, path, many)

    def get_data(self, data, path, many=False, with_path=False):
        """
        Return data using provided path, as `(json_path, data)`.

        :param data: input data
        :param JsonPath path: target path
        :param bool many: return an array instead the first matching value
        :param with_path: for each match, return a tuple of ``(path, value)``.
        """
        if not path:
            return data
        iter = ((m.node.tojsonpath(), m.current_value) for m in path.match(data)) \
                    if with_path else (m.current_value for m in path.match(data))
        return list(iter) if many else next(iter, None)


class Reader(BaseReader):
    """
    Get data by JSONPath (using jsonpath2 library), and deserialize if
    serializer_class is provided.
    """
    serializer_class = None
    """ Serializer class """
    serializer_kwargs = None
    """ Init arguments to pass to serializer instanciation"""
    record_set_class = RecordSet
    """ RecordSet class. """

    def __init__(self, path=None, serializer_class=None, many=False, 
                    record_set_class=RecordSet, **serializer_kwargs):
        self.serializer_class = serializer_class
        self.serializer_kwargs = serializer_kwargs
        self.record_set_class = record_set_class
        super().__init__(path, many)

    @property
    def model(self):
        """ Get model """
        if not self.serializer_class:
            return None
        return getattr(self.serializer_class.Meta, 'model', None)

    def read(self, data, path=None, many=None, force_data=None, pool=None, **kwargs):
        """
        Extract data from provided (parsed) object. Create and return
        serializer if ``serializer_class`` to validate data (calling
        ``serializer.is_valid()``.

        When no serializer is provided, return data.

        :param dict|list|[] data: source data
        :param bool force_data: if True, return validated_data instead of serializer
        :param JSONPath path: override self.path;
        :param bool many: override self.many;
        :param **kwargs: passed down to ``get_serializer``.
        :returns serializer, serializer.validated_data or data

        Flowshart:
            - ``get_data``
            - ``get_serializer``
            - ``serializer.is_valid()``
        """
        if many is None:
            many = self.many
        data = super().read(data, path, many, pool=pool, **kwargs)
        serializer = data and self.get_serializer(data, many=many, **kwargs)
        if serializer:
            serializer.is_valid()
            if not force_data:
                return serializer
            data = serializer.validated_data
        return data

    def get_serializer(self, data, **kwargs):
        """ Return data serializer or None. """
        serializer_class = self.serializer_class
        if serializer_class:
            if self.serializer_kwargs:
                kwargs.update((k, v) for k,v in self.serializer_kwargs.items()
                                if k not in kwargs)
            return serializer_class(data=data, **kwargs)
        return None
