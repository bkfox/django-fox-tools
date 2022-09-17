from django.test import TestCase

from fox_tools.combinations import *


__all__ = ('VariableTestCase', 'CombinationsTestCase', 'FunctionsTestCase')


class VariableTestCase(TestCase):
    def test_parse(self):
        formats = [('a:ints=1,2,3', (1,2,3)),
                   ('a:ints=1', (1,)),
                   ('a=alef,beth,giled,1', ('alef','beth','giled','1')),
                   ('a:floats=1.2,3.4', (1.2, 3.4)) ]
        for string, expected in formats:
            result = Variable.parse(string)
            self.assertEquals(result.name, 'a', '{res} != "a" (for "{string}")'
                .format(res=result, string=string))
            self.assertEquals(tuple(result.args), expected)

    def test_get_list(self):
        args = ['3','2','4']
        iter = Variable('a', args)
        results = list(iter.get())
        self.assertEquals(results, args)
        
    def test_init_get_ints(self):
        args = ['3','2','4']
        expected = [int(a) for a in args]
        iter = Variable('a', args, 'ints')
        self.assertEquals(iter.args, expected)

        results = list(iter.get())
        self.assertEquals(results, expected)
        
    def test_init_get_floats(self):
        args = ['3.0','-2','4.43']
        expected = [float(a) for a in args]
        iter = Variable('a', args, 'floats')
        self.assertEquals(iter.args, expected)

        results = list(iter.get())
        self.assertEquals(results, expected)

    def test_get_range(self):
        args = [0,10,2]
        expected = list(range(*args))
        iter = Variable('a', args, 'range')
        result = list(iter.get())
        self.assertEquals(result, expected)

    def test_get_date_range(self):
        args = ['2022-05-04', '2022-05-14']
        expected = ['2022-05-{:0>2}'.format(i) for i in range(4,14)]
        iter = Variable('a', args, 'date_range')
        result = list(iter.get())
        self.assertEquals(result, expected) 


class CombinationsTestCase(TestCase):
    def test_iter(self):
        input = '/test/{a}/{b}/{c}/{const}'
        vars = (Variable('a', [0,1]), Variable('b', [3,4]), Variable('c', [5,6]))
        expected = [input.format(a=v[0], b=v[1], c=v[2], const='const') for v in (
            (0,3,5), (0,3,6), (0,4,5), (0,4,6), (1,3,5), (1,3,6), (1,4,5), (1,4,6),
        )]
        
        combine = Combinations(input, vars, {'const': 'const'})
        results = list(combine.iter())
        self.assertEquals(results, expected)


class FunctionsTestCase(TestCase):
    def test_iter_dfs(self):
        args = ([0,1], [3,4])
        vars = (Variable('a', [0,1]), Variable('b', [3,4]))
        expected = [{'a':0, 'b':3}, {'a':0, 'b':4},
                    {'a':1, 'b':3}, {'a':1, 'b':4},]
        result = [o.copy() for o in iter_dfs(vars)]
        self.assertEquals(result, expected)
        

