# django-fox-tools
Tools set to be used in conjunction with Django and Django Rest Framework. Provide the following modules:

- `data`: manipulate and serialize related data with complex schemes.
    - `pool`: pool of data by record set key;
    - `reader`, `readers`: deserialize and manipulate data, used in conjunction with data pool;
    - `record`, `record_set`: records and set of data records CRUD (get, commit, save);
    - `relation`: data relationships resolution using specified index and pool;
- `combinations`: iterator generating combinations of values.
- `commands/management`:
    - `data_summary`: run over files, extracting data of provided JSON paths;
    - `http_scan`: http scanner generating urls based on provided format;
- `mixins`: some Django view mixins.
    - `FilterMixin`: filters and pagination using `django-filter` and pagination.
- `serializers`: some DRF's fields and serializers.
    - `MapField`: representation-value mapping;
    - type conversion without error to `int`, `float`;
    - `TimerField`: `MM"SS'MS` timer format conversion to milliseconds `int`;
    - `ModelListSerializer`: serialize models, with optional delete;
- `settings`: class-based settings.
- `string`: some string utils, mainly case-conversion (snake, camel, verbose);
- `tasks`: pool and future based task, including common used ones:
    - `base`, `pool`: base tasks and pool mechanisms;
    - `http_request`: http request tasks (base, api, json, download);
    - `http_scanner`: http download using `Combination` url generator;
    - `import_model`: bulk model import using provided data-set (unstable over multithread);
    -  (http scanner, http request, model import, ...);
    -  `viewsets`: DRF viewsets handling tasks pool;


More documentation will come up soon, still it is best to check in-code documentation for the moment. Library is developped based on my other projects' needs.

