import io
import requests
from rest_framework.parsers import JSONParser

from tools.data import Reader, Readers, RecordSet
from .base import task, Task


__all__ = ('HttpRequest', 'ApiRequest', 'JsonRequest', 'DownloadRequest')


class HttpRequest(Task):
    """ Run HTTP request and extract data from response. """
    session = None
    """ requests' session. """
    url = None
    """ Url, use key as default value. """
    method = 'GET'
    """ Http method """
    options = None
    """ Request options """
    headers = None
    """ Request headers """
    follow_redirect = 0
    """
    Follow redirections, as an integer specifying maximum count of
    redirections to follow. HTTP codes from ``http_redirect_codes``.
    Boolean ``True`` is understood as 1 redirection.
    """
    http_redirect_codes = (301,302,303,307,308)

    def __init__(self, key, *args, url=None, session=None, headers=None, **kwargs):
        self.url = url or key
        self.session = session

        # mix headers
        if not self.headers:
            self.headers = headers
        elif headers:
            self.headers = self.headers.copy()
            self.headers.update(headers)
        super().__init__(key, *args, **kwargs)

    def run(self, url=None, method=None, session=None, options=None, **kwargs):
        """
        Do request passing down parameters to ``self.request()``.

        Flowchart:
        - ``self.request()``
        - ``super.run(throw=False, **kwargs)`` with extra/used: response, session
        """
        response = self.request(url, method, session, **(options or {}))
        kwargs['response'] = response
        kwargs['throw'] = False
        if hasattr(response, 'data'):
            kwargs['data'] = response.data
        return super().run(url=url, method=method, session=session, **kwargs)

    def request(self, url=None, method=None, session=None, headers=None,
                follow_redirect=None, **options):
        """ Do HTTP request and return response. """
        method = method or self.method
        url = url or self.url
        session = session or self.session
        if follow_redirect is None:
            follow_redirect = self.follow_redirect

        headers_ = self.headers and self.headers.copy() or {}
        options_ = self.options and self.options.copy() or {}
        if headers: headers_.update(headers)
        if options: options_.update(options)
        options_['headers'] = headers_

        session_ = session or Session()
        response = session.request(method, url, **options_)

        # HTTP redirection
        if follow_redirect and response.status_code in self.http_redirect_codes:
            follow_redirect = int(follow_redirect)
            while response.status_code in self.http_redirect_codes and \
                    follow_redirect > 0:
                url = response.headers.get('Location')
                if not url:
                    break
                response = session.request(method, url, **options)
                follow_redirect -= 1
        if not session:
            session_.close()
        return response
        

class ApiRequest(HttpRequest):
    """
    From HTTP request's response, read data and set it as response's
    ``data`` attribute.

    It uses ``tools.Reader`` in order to pick data element and
    deserialize.
    """
    parser_class = None
    """ Parse data using provided ``rest_framework.parsers.Parser`` class. """
    instance = None
    """ Data instances """
    reader = None
    """ Data reader/readers """

    def run(self, *args, instance=None, **kwargs):
        instance = instance or self.instance
        return super().run(*args, instance=instance, **kwargs)
    
    def request(self, *args, reader=None, instance=None, pool=None, **kwargs):
        """
        Request and parse/deserialize data.

        Flowchart:
        - ``super().request(*args, **kwargs)``
        - ``parse_data()``
        - ``reader.read()``
        - ``get_data(data, instance, reader)``
        """
        response = super().request(*args, **kwargs)
        data = response.text or None
        if data:
            data = self.parse(response.text)
            data = self.read(data, reader=reader, instance=instance, pool=pool)
        setattr(response, 'data', data)
        return response

    def read(self, data, reader=None, **kwargs):
        """
        Read data, using reader if one is found/provided.

        Flowchat:
        - ``get_reader(reader or self.reader)``
        - ``reader.read(**kwargs)``: if reader
        """
        if reader is None:
            reader = self.reader
        reader = self.get_reader(reader)
        return reader.read(data, **kwargs) if reader else data

    def get_reader(self, reader):
        """ Get reader. """
        reader = reader or self.reader
        if isinstance(reader, dict):
            return Readers(self.reader)
        return reader

    def parse(self, raw):
        """
        Parse raw data.
        If a parser is provided, parse and return data from provided ``raw``.
        If not parser is provided, return raw data as is.
        """
        if not self.parser_class:
            return raw
        if isinstance(raw, str):
            raw = raw.encode()
        if not callable(getattr(raw, 'read', None)):
            raw = io.BytesIO(raw)
        parser = self.parser_class and self.parser_class()
        return parser.parse(raw)


class JsonRequest(ApiRequest):
    parser_class = JSONParser


class DownloadRequest(HttpRequest):
    stream = None
    """ Stream or file path. """
    keep_all = False
    """ If True, also save file when response status code is not ``2**``. """
    save_headers = False
    """ If True, save location and headers in file. """
    as_binary = False
    """ If True, download and open file as binary. """
    chunk_size = 512
    """ Download chunk size """
    overwrite = False
    """ If True, overwrite existing file. """

    def request(self, *args, stream=None, keep_all=None, save_headers=None,
                as_binary=None, **kwargs):
        response = super().request(*args, **kwargs)
        if keep_all is None:
            keep_all = self.keep_all
        if stream is None:
            stream = self.stream

        if stream and (200 <= response.status_code < 300 or keep_all):
            self.save(stream, response, save_headers, as_binary=as_binary)
        return response

    def save(self, stream, response, save_headers=None, as_binary=None,
                close_stream=True):
        if save_headers is None:
            save_headers = self.save_headers
        if as_binary is None:
            as_binary = self.as_binary
        if isinstance(stream, str):
            stream = open(stream, 'wb' if as_binary else 'w')

        if close_stream:
            with stream:
                self._write_stream(response, stream, save_headers, as_binary)
        else:
            self._write_stream(response, stream, save_headers, as_binary)


    def _write_stream(self, response, stream, save_headers, as_binary):
        if save_headers:
            stream.write(response.url + '\n')
            for key, value in response.headers.items():
                stream.write(key + ': ' + value + '\n')
            stream.write(('-'*80) + '\n')

        for content in response.iter_content(self.chunk_size, not as_binary):
            stream.write(content)

