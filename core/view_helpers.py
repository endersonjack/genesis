from functools import wraps


def empresa_scoped(view_func):
    """
    Inclui rotas sob empresa/<empresa_id>/... sem alterar cada view.
    Remove empresa_id dos kwargs antes de chamar a view original.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        kwargs.pop('empresa_id', None)
        return view_func(request, *args, **kwargs)

    return wrapper
