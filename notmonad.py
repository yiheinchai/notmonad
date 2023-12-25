#########################################
# MONADS PLATFORM
#########################################


def partial(func, /, *args, **keywords):
    def newfunc(*fargs, **fkeywords):
        newkeywords = {**keywords, **fkeywords}
        return func(*args, *fargs, **newkeywords)

    newfunc.func = func
    newfunc.args = args
    newfunc.keywords = keywords
    return newfunc


def caller(monad):
    def inner(*args, **kwargs):
        pkwargs = {
            key: value for key, value in kwargs.items() if not key.startswith("_")
        }
        _kwargs = {key: value for key, value in kwargs.items() if key.startswith("_")}

        if _kwargs.get("_consumed", False):
            raise RuntimeError(
                f"Cannot compose two caller monads together. {monad.__name__} is the second caller monad used. Please remove this for it to work."
            )

        newVal, newFunc, newArgs, newKwargs = monad(*args, **kwargs)
        return newVal, newFunc, newArgs, {**_kwargs, **newKwargs, "_consumed": True}

    inner.__name__ = monad.__name__
    return inner


def compose(*monads):
    def combined_monad(_monads, value, func=None, *args, **kwargs):
        pkwargs = {
            key: value for key, value in kwargs.items() if not key.startswith("_")
        }
        _kwargs = {
            key: value
            for key, value in kwargs.items()
            if key.startswith("_") and not key == "_consumed"
        }
        if func is None and not args and not pkwargs:
            return value

        if len(_monads) == 0 and func is not None:
            return partial(combined_monad, monads, value, **_kwargs)

        monad, *rest_monads = _monads
        newVal, newFunc, newArgs, newKwargs = monad(value, func, *args, **kwargs)
        return combined_monad(rest_monads, newVal, newFunc, *newArgs, **newKwargs)

    return partial(combined_monad, monads)


def mmonad(monad_to_add):
    def _monad_monad(monad_list, monad_to_add=None):
        def combined_monad(_monads, value, func=None, *args, **kwargs):
            if func is None and not args and not kwargs:
                return value

            if len(_monads) == 0 and func is not None:
                return partial(combined_monad, monad_list, value)

            monad, *rest_monads = _monads
            newVal, newFunc, newArgs, newKwargs = monad(value, func, *args, **kwargs)
            return combined_monad(rest_monads, newVal, newFunc, *newArgs, *newKwargs)

        if monad_to_add is None:
            return partial(combined_monad, monad_list)
        return partial(_monad_monad, [*monad_list, monad_to_add])

    return _monad_monad([], monad_to_add)


def monad(value, _monad):
    return partial(_monad, value)


#########################################
# BASE MONADS
#########################################


@caller
def just(value, func, *args, **kwargs):
    kwargs = {key: value for key, value in kwargs.items() if not key.startswith("_")}
    return func(value, *args, **kwargs), func, args, kwargs


@caller
def maybe(value, func=None, *args, **kwargs):
    kwargs = {key: value for key, value in kwargs.items() if not key.startswith("_")}
    if value is None:
        return None, func, (), {}

    try:
        result = func(value, *args, **kwargs)
    except Exception as e:
        result = None

    return result, func, args, kwargs


def debug(value, func, *args, **kwargs):
    if value is None:
        return None, func, args, kwargs

    debug_trace = kwargs.pop("_debug_trace", [])

    errors = ""

    try:
        result = func(value, *args, **kwargs)
    except Exception as e:
        errors = e
        result = None

    new_trace = {
        "func": getattr(func, "__name__", ""),
        "args": (value, *args),
        "kwargs": kwargs,
        "value": result,
        "errors": str(errors),
        "repr": f"{getattr(func, '__name__', '')}{(value, *args)} -> {result} [{str(errors)}]",
    }

    return value, func, args, {**kwargs, "_debug_trace": [*debug_trace, new_trace]}


def shout(value, func, *args, **kwargs):
    print("I am shouting!", func.__name__)
    return value, func, args, kwargs


def log(value, func, *args, **kwargs):
    execution_log = kwargs.pop("_log", [])
    return (
        value,
        func,
        args,
        {**kwargs, "_log": [*execution_log, getattr(func, "__name__", None)]},
    )


def order_args(value, func, *args, **kwargs):
    def sort_args(args, order):
        return tuple([args[index] for index in order])

    order = kwargs.pop("order", None)

    if order is None:
        return value, func, args, kwargs

    value, *args = sort_args([value, *args], order)

    return value, func, args, kwargs


#########################################
# CONVENIENCE MONADS
#########################################


def Maybe(value, func=None, *args, **kwargs):
    if func is None and not args and not kwargs:
        return value

    try:
        result = func(value, *args, **kwargs)
    except Exception as e:
        result = None

    return partial(Maybe, result)


def Just(value, func=None, *args, **kwargs):
    if func is None and not args and not kwargs:
        return value
    return partial(Just, func(value, *args, **kwargs))


def chain(value):
    return monad(value, Just)


def add(arg1, arg2):
    return arg1 + arg2


monad(5, compose(debug))(add, 1)(lambda x: x / 0)(add, 3)
