import io

from django.test import TestCase

from rest_framework import serializers
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer

from fox_tools.data import Pool, Reader, RecordSet
from fox_tools.tasks.http_request import *


class TestResponse:
    def __init__(self, **kwargs):
        self.__dict__.update(**kwargs)

    def copy(self):
        return TestResponse(**self.__dict__)

    def iter_content(self, chunk_size, as_text=False):
        i, n = 0, len(self.text)
        text = self.text
        if not isinstance(text, str) and as_text:
            text = text.decode('utf-8')
        while i < n:
            yield text[i:i+chunk_size]
            i += chunk_size
        

class TestSession:
    """ Emulates requests.session interface with predefined responses. """
    renderer_class = JSONRenderer

    def __init__(self, responses=None, renderer_class=JSONRenderer):
        self.renderer_class = renderer_class
        self.responses = {}
        if responses:
            for k, v in responses.items():
                self.set_response(v, k)

    def get_response(self, url, method=None, **options):
        keys = ((url,method), (url,None), (None, None))
        response = next((self.responses.get(k) for k in keys
                             if k in self.responses), None)
        return response or ''

    def set_response(self, data, url=None, method=None):
        if isinstance(data, (TestResponse,str)) or data is None:
            self.responses[(url,method)] = data
        else:
            self.responses[(url,method)] = self.renderer_class().render(data) \
                                                .decode('utf-8')

    def request(self, method, url, **options):
        response = self.get_response(url, method)
        if isinstance(response, TestResponse):
            response = response.copy()
            response.url = url
            response.method = method
            response.options = options
            return response
        return TestResponse(url=url, text=response, method=method, options=options,
                            status_code=response and 200 or 404)


class TestSerializer(serializers.Serializer):
    a = serializers.DictField()
    b = serializers.IntegerField()

class TestSerializer2(serializers.Serializer):
    c = serializers.IntegerField()
    d = serializers.IntegerField()


class HttpRequestTestCase(TestCase):
    def setUp(self):
        self.map = {'/a/': 'a', '/b/': 'b'}
        self.session = TestSession(self.map)
        self.object = HttpRequest('/a/', session=self.session,
            headers={'Referer': 'test.io'})
        
    def test_request(self):
        obj, map = self.object, self.map
        result = obj.request(headers={'Origin': 'test.io'})
        self.assertEquals(result.text, map[obj.url], "Default url unused")

        headers = result.options['headers']
        self.assertIsNotNone(headers.get('Origin'))
        self.assertIsNotNone(headers.get('Referer'))

    # TODO: test_request_redirect

    def test_run(self):
        self.object.run()


class ApiRequestTestCase(TestCase):
    def setUp(self):
        self.map = {'/a/': {'a': {'1': 13, '2':23}},
                    '/b/': {'b': 32},    
                    '/ab/': {'a': {'1': 13, '2':23}, 'b': 32 }}
        self.session = TestSession(self.map)
        self.object = ApiRequest('/ab/', session=self.session,
            parser_class=JSONParser)

    def test_parse_data(self):
        text = JSONRenderer().render(self.map).decode('utf8')
        result = self.object.parse(text)
        self.assertEquals(result, self.map, "with parser: data-s should be equals")

        self.object.parser_class = None
        result = self.object.parse(self.map)
        self.assertIs(result, self.map, "no parser: raw should be returned")

    def test_run_no_serializer(self):
        obj = self.object
        result = obj.request()
        self.assertEquals(result.data, self.map[obj.url])

        reader = Reader(path='$.a["1"]')
        result = obj.request(reader=reader)
        self.assertEquals(result.data, self.map[obj.url]['a']['1']) 

    def test_run_with_serializer(self):
        obj = self.object
        reader = Reader(serializer_class=TestSerializer)
        result = obj.request(reader=reader)
        self.assertIsNotNone(result.data)
        self.assertEquals(result.data.validated_data, self.map[obj.url])


class DownloadRequestTestCase(TestCase):
    def setUp(self):
        self.map = { '/a/': TestResponse(status_code=200, text='abc', headers={'Cookies':'a=1'}),
                     '/b/': TestResponse(status_code=200, text=b'abcb', headers={'Cookies':'b=1'})}
        self.session = TestSession(self.map)

    def test_request(self):
        for url, resp in self.map.items():
            obj = DownloadRequest(url, session=self.session, save_all=True)
            result = obj.request(as_binary=False)
            self.assertEquals(resp.text, result.text, '(url={})'.format(url))

    def test_save(self):
        for url, resp in self.map.items():
            stream = io.StringIO()
            resp.url = url
            obj = DownloadRequest(url, session=self.session, save_all=True, stream=stream)
            obj.save(stream, resp, save_headers=True, close_stream=False)
            expected = self.get_expected(url, resp)
            self.assertEquals(expected, stream.getvalue(), '(url={})'.format(url))

    def get_expected(self, url, resp):
        content = isinstance(resp.text, bytes) and resp.text.decode('utf-8') or \
                    resp.text
        
        exp = '{url}\n{headers}\n{sep}\n{content}'.format(
            url=url, content=content, sep='-'*80,
            headers='\n'.join('{}: {}'.format(k,v) for k, v in resp.headers.items())
        )
        return exp

