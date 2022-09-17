
class FiltersMixin:
    """
    Integrate Django Filters and pagination.

    Provide template context:
    - ``get_params``: GET parameters (except for ``self.page_var`` GET
        parameter;
    - ``filterset``: filterset instance
    - ``filterset_data'`: filterset cleaned data;

    """
    filterset_class = None
    """ Filterset class. """
    filterset = None
    """ Filterset instance (set on ``get_queryset``). """
    page_var = 'page'
    """ GET variable name for page """

    def get_filterset(self, query, **kwargs):
        data = self.request.GET
        if kwargs:
            data = dict(data)
            data.update(kwargs)
        return self.filterset_class(data, query)

    def get_queryset(self):
        query = super().get_queryset()
        if self.filterset_class:
            self.filterset = self.get_filterset(query)
            return self.filterset.qs
        return query

    def get_context_data(self, **kwargs):
        filterset = kwargs.setdefault('filterset', self.filterset)
        if filterset.is_valid():
            kwargs['filterset_data'] = filterset.form.cleaned_data
        else:
            kwargs['filterset_data'] = {}

        params = self.request.GET.copy()
        kwargs['get_params'] = params.pop(self.page_var, None) and params
        return super().get_context_data(**kwargs)

