from itertools import islice
import glob
import os
import traceback


from django import test


__all__ = ('TestError', 'for_each_sample', 'SamplesTestCase', 'SerializerTestCase')


class TestError(Exception):
    error_fmt = '- {key}:\n    {error}'
    context_fmt = '- Context: {context}'
    errors = None
    context = None

    def __init__(self, message, errors=None, context=None):
        super().__init__(message)
        self.errors = self.set_errors(errors)
        self.context = context

    def set_errors(self, errors):
        """ Return errors gathered by stack info """
        by_stack = {}
        for key, error in errors.items():
            if isinstance(error, Exception):
                stack = None
            else:
                error, stack = error
                stack = stack.replace(type(error).__name__ + ': ' + str(error), '')
            by_key = (stack, type(error))
            by_stack.setdefault(by_key, []).append((key, error))
        return [(stack, errors) for (stack,_), errors in by_stack.items()]

    def errors_str(self):
        result = ''
        for stack, errors in self.errors:
            infos = '\n'.join(self.error_fmt.format(key=k, error=repr(e))
                                for k, e in islice(errors, 5))
            if len(errors) > 5:
                infos += '\n- {} more errors...'.format(len(errors)-5)
            if stack:
                infos += '\n- stack:\n' + stack
            result += infos + '\n'
        return result        

    def info_str(self):
        infos = ''
        if self.context:
            infos += '\n' + self.context_fmt.format(context=context)
        if self.errors:
            infos += '\n' + self.errors_str()
        return infos

    def __repr__(self):
        return super().__repr__() + self.info_str()

    def __str__(self):
        return super().__str__() + self.info_str()


def for_each_sample(func):
    """
    Decorator calling provided function for each samples data file provided
    by SamplesTestCase.

    :param callable func: `func(path, data)`.
    :raises TestError with gathered errors
    """
    def wrapper(self):
        errors = {}
        for path, data in self.files.items():
            try:
                func(self, path, data)
            except Exception as err:
                errors[path] = (err, traceback.format_exc())
        if errors:
            raise TestError('exceptions while running tests:', errors)
    return wrapper


class SamplesTestCase(test.TestCase):
    """
    Read data samples from file once at test class setup.
    """
    data_path = None
    """ Glob search string to data (excluding `data_dir`) """
    data_parser = None
    """ Function parsing data if required. For example: `json.loads`. """
    reader = None
    """ If provided use reader instance for data got from files. """

    def setUp(self):
        pass

    @classmethod
    def setUpClass(cls):
        if cls.data_path:
            cls.files = cls.get_data_files()
        super().setUpClass()

    @classmethod
    def get_data_files(cls, path=None, reader=None):
        if reader is None:
            reader = cls.reader

        path = os.path.abspath(path or cls.data_path)
        paths = glob.glob(path) 
        files = {}
        for path in paths:
            with open(path, 'r') as file:
                content = file.read()
                if cls.data_parser:
                    content = cls.data_parser(content)
                    if reader:
                        content = cls.reader.read(content, force_data=True)
                files[path] = content
        return files

    def zip_test(self, datas, results, test, many=False):
        """
        Run `test` against datas and related results. If many, run test for
        each element of data (corresponding result must then be also an
        iterable

        :raise TestError: occured exceptions.
        """
        datas = dict(datas)
        errors = {}
        for key, result in results.items():
            try:
                data = datas[key]
                if many:
                    for source, value in zip(data, result):
                        test(key, source, value)
                else:
                    test(key, source, result)
            except Exception as err:
                import traceback
                if not errors:
                    traceback.print_exc()
                errors[key] = err
        if errors:
            raise TestError('tests raised exceptions:', errors)


class SerializerTestCase(test.TestCase):
    """ TestCase used in serializers' testing """
    serializer_class = None
    serializer_kwargs = None
    
    def get_serializer(self, **kwargs):
        """ Return serializer instance. """
        return self.serializer_class(**kwargs)

    def deserialize(self, data, as_data=True, raises=True, **kwargs):
        """
        Deserialize data and return serializer.
        :param (dict|list) data: data to deserialize
        :param bool as_data: return validated data instead of serializer
        :param bool raises: serializer's `raise_exception` at validation
        :param **kwargs arguments passed to serializer instanciation.

        Flowchart:
            - `get_serializer(data=data, **kwargs)`
            - `serializer.is_valid(raise_exception=raises)`
        """
        serializer = self.get_serializer(data=data, **kwargs)
        serializer.is_valid(raise_exception=raises)
        print('validated_data', data, serializer.validated_data, kwargs)
        return serializer.validated_data if as_data else serializer

    def deserialize_many(self, datas, **kwargs):
        """
        Deserialize multiple data iterating over `datas`. Gather raised
        exceptions before raising.

        :param iter datas: an iterator of `(key, data)`.
        :param **kwargs: passed down to `self.deserialize`
        :return deserialize results as `{key: serializer}`.
        :raise TestError: occured exceptions.
        """
        kwargs['raises'] = True
        results, errors = {}, {}
        for key, data in datas:
            try:
                results[key] = self.deserialize(data, **kwargs)
            except Exception as err:
                import traceback
                if not errors:
                    traceback.print_exc()
                errors[key] = err

        if errors:
            raise TestError('deserialize raised exceptions:', errors)
        return results

