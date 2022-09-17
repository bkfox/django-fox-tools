import os

from tools.tasks.iter import IterTaskSet
from tools.tasks.http_request import DownloadRequest


__all__ = ('Scanner',) 



class Scanner(IterTaskSet):
    """ Download using url generator """
    output_dir = './'
    """ Output directory to save files into. """
    session = None
    """ HTTP session to use (set to first sent request). """
    request_kw = None
    """ Init kwargs for requests. """
    request_class = DownloadRequest
    """ Request class """

    def __init__(self, key, generator, **kwargs):
        """
        :params tuple|list urls: target urls, defaults to key.
        """
        self.generator = generator
        if generator:
            kwargs['iter'] = generator.iter()
        super().__init__(key, **kwargs)

    def from_iter(self, url):
        """ Return download task. """
        output = self.get_download_output(url, **kwargs)
        if not output:
            return
        kwargs = self.request_kw.copy() if self.request_kwargs else {}
        kwargs['session'] = self.session
        kwargs['output'] = output

        req = self.request_class(url, **kwargs)
        if not self.session:
            self.session = req.session
        return req

    def get_download_output(self, url):
        """ Return output stream for the provided url. """
        if not self.output_dir:
            return

        basepath  = os.path.join(self.output_dir, url.replace('/','_'))
        path = basepath
        if os.path.exist(path):
            i = 1
            while os.path.exist(path):
                path = basepath + str(i)
                i += 1
        return output

    def reset_iter(self):
        self.iter = generator.iter()

