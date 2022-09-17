from django.conf import settings


class Settings:
    """
    Provide settings loading and defaults. Uses `django.conf.settings`
    as default configuration source.

    Example:

        ```
        class MySettings(Settings):
            a = 13
            b = 12

        my_settings = MySettings('MY_SETTINGS_KEY')
        print(my_settings.a, my_settings['a'], my_settings.get('b'))
        ```

        This will load values from project settings.
    """
    def __init__(self, key=None, module=None, conf=None):
        """
        Instanciate and load settings, from provided ``conf`` or
        ``module`` (defaults to ``django.conf.settings``).

        Uses key to get 
        """
        if key:
            self.load(key, module)
        if conf:
            self.update(conf)

    def load(self, key, module=None):
        if module is None:
            module = settings
        self.__dict__.update(getattr(module, key, {}))

    def update(self, conf):
        if isinstance(conf, Conf):
            conf = conf.__dict__
        self.__dict__.update(conf)

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getattr__(self, key):
        return self.__dict__.get(key)


