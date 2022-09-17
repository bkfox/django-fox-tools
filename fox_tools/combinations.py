"""
Generate values based on formats and variables registered on the 
`Combinations` generator class.

Base `Variable` class provides multiple values iterators, such as list,
range, date range.
"""
from datetime import date, timedelta
from itertools import islice


__all__ = ('Variable', 'Combinations', 'iter_dfs',)


def var_type(func):
    setattr(func, 'var_type', func.__name__)
    return func


class Variable:
    """
    Base class used for iterating over values, representing a variable and
    its values.

    Either ``get()`` or getter method (``get_typename``) must be provided.
    Init method can be implemented for specific types, such as: ``init_typename()``.

    Get method must return a new iterator over values.
    """
    default_typ = 'list'
    
    def __init__(self, name, args, typ=None):
        """
        Initialize iterator.

        :raises: ValueError when no 
        :param str name: variable name
        :param str typ: type name
        :param [] args: arguments set to ``self.args`` if no init method \
                        is present for provided type.
        """
        self.name = name
        self.typ = typ or 'list'

        get = getattr(self, self.typ, None)
        if (get is None or not hasattr(get, 'var_type')) \
                and not getattr(self, 'get', None):
            raise ValueError(
                'no getter found for type {} nor ``get()`` is provided'
                .format(self.type)
            )
        self.get = get 
        
        init = getattr(self, 'init_' + self.typ, None)
        if init:
            init(*args)
        else:
            self.args = args

    @classmethod
    def parse(cls, value):
        """
        Return class instance from provided text string.
        Value format: ``[key][:[type=list]]?=[*arg,]``.
        """
        key, value = value.split('=', 1)
        key = key.split(':', 1)
        
        name, typ = key[0], key[1] if len(key) > 1 else cls.default_typ
        args = value.split(',')
        args = [arg.strip() for arg in args]
        return cls(name, args, typ)

    @classmethod
    def get_types(cls):
        """ Return supported variable types, as iterator of `(name, doc)` """

        return (func for func in (getattr(cls, k) for k in dir(cls))
                    if hasattr(func, 'var_type'))

    @var_type
    def list(self):
        """ Return all provided items. """
        return iter(self.args)

    def init_ints(self, *args):
        self.args = [int(a) for a in args]

    @var_type
    def ints(self):
        """ Return all provided items as integer. """
        return iter(self.args)

    def init_floats(self, *args):
        self.args = [float(a) for a in args]

    @var_type
    def floats(self):
        """ Return all provided items as floats. """
        return iter(self.args)

    def init_range(self, *args):
        self.args = tuple(int(a) for a in args)

    @var_type
    def range(self):
        """ Iterate over a range of integers. Args: [start,end,step] """
        return iter(range(*self.args))

    def init_date_range(self, start, end=None, step=1, strftime='%Y-%m-%d'):
        self.start = date(*(int(a) for a in start.split('-',3)))
        self.end = date(*(int(a) for a in end.split('-',3))) \
                if end else date.today()
        self.step = timedelta(days=int(step))
        self.strftime = strftime

    @var_type
    def date_range(self):
        """
        Iterate over a range of dates, yield a string representation.
        Args: [start,end,step=1,strftime='%Y-%m-%d].
        Dates have the following format: 'YYYY-MM-DD'
        """
        start = self.start
        while start < self.end:
            yield start.strftime(self.strftime)
            start += self.step


class Combinations:
    """
    Generate all values combination using provided variables and consts.
    Use ``input.format(**vars)`` to get value.
    """
    inputs = None
    variables = None

    def __init__(self, inputs, variables=None, consts=None):
        self.inputs = tuple(inputs) if isinstance(inputs, (list,tuple)) else (inputs,)
        self.variables = variables
        self.consts = consts or {}

    def iter(self):
        """ Return an iterator generating all inputs combinations. """
        if not self.variables:
            return [input.format(**self.consts) for input in self.inputs]

        values = self.consts.copy()
        for output in iter_dfs(self.variables):
            values.update(output)
            for inp in self.inputs:
                yield inp.format(**values)


def iter_dfs(variables, index=0, output=None):
    """
    Return an iterator over all possible variables combinations, using depth
    first search algorithm.

    Yield ``(name, value)`=None`.
    """
    if index >= len(variables):
        return
    if output is None:
        output = {}

    node = variables[index]
    next_index = index+1
    for value in node.get():
        output[node.name] = value
        if next_index < len(variables):
            for child_value in iter_dfs(variables, next_index, output):
                yield child_value
        else:
            yield output
            

