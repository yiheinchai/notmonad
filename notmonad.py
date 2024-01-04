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
    newfunc.__name__ = func.__name__
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

        newVal, newFunc, newArgs, newKwargs = monad(*args, **pkwargs)
        return newVal, newFunc, newArgs, {**_kwargs, **newKwargs, "_consumed": True}

    inner.__name__ = monad.__name__
    return inner


def compose(*monads):
    def combined_monad(_monads, value, func=None, *args, **kwargs):
        pkwargs = {
            key: value for key, value in kwargs.items() if not key.startswith("_")
        }
        # TODO: BAD CODE rethink __ as actionable args
        __kwargs = {key: value for key, value in kwargs.items() if key.startswith("__")}
        _kwargs = {
            key: value
            for key, value in kwargs.items()
            if key.startswith("_")
            # TODO: BAD CODE too many edge case conditions
            and not key.startswith("__") and not key in ["_consumed", "_skip"]
        }
        # TODO: BAD CODE too many edge case conditions
        if func is None and not args and not pkwargs and not __kwargs:
            return value

            # TODO: BAD CODE too many edge case conditions
        if (len(_monads) == 0 and kwargs.get("_skip", False)) or (
            len(_monads) == 0 and func is not None
        ):
            return partial(combined_monad, monads, value, **_kwargs)

        monad, *rest_monads = _monads

        # enables skipping execution of rest of monads, used by mem
        if kwargs.get("_skip", False):
            newVal, newFunc, newArgs, newKwargs = value, func, args, kwargs
        else:
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


def monad(value, monad_func):
    return partial(monad_func, value)


#########################################
# BASE MONADS
#########################################


@caller
def just(value, func, *args, **kwargs):
    if value is None and func is not None:
        return func(*args, **kwargs), func, args, kwargs
    return func(value, *args, **kwargs), func, args, kwargs


@caller
def maybe(value, func=None, *args, **kwargs):
    if isinstance(value, Exception):
        return value, func, (), {}

    try:
        if value is None and func is not None:
            result = func(*args, **kwargs)
        else:
            result = func(value, *args, **kwargs)
    except Exception as e:
        result = e

    return result, func, args, kwargs


def debug(value, func, *args, **kwargs):
    if isinstance(value, Exception):
        return value, func, args, kwargs

    debug_trace = kwargs.pop("_debug_trace", [])

    pkwargs = {key: value for key, value in kwargs.items() if not key.startswith("_")}

    errors = ""

    try:
        result = func(value, *args, **pkwargs)
    except Exception as e:
        errors = e
        result = None

    new_trace = {
        "func": getattr(func, "__name__", ""),
        "args": (value, *args),
        "kwargs": kwargs,
        "value": result,
        "errors": repr(errors),
        "repr": f"{getattr(func, '__name__', '')}{(value, *args)} -> {result} [{repr(errors)}]",
    }

    print("\n======== \n", new_trace["repr"])

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


def assign_args(value, func, *args, **kwargs):
    order = kwargs.pop("order", None)

    if order is None:
        return value, func, args, kwargs

    args = (value, *args)

    # order is in destination: origin format
    ordered_args = tuple(
        [
            args[origin]
            for dest, origin in order.items()
            if isinstance(dest, int) and isinstance(origin, int)
        ]
    )
    ordered_kwargs = {
        dest: args[origin]
        for dest, origin in order.items()
        if isinstance(dest, str) and isinstance(origin, int)
    }

    value, *args = ordered_args

    return value, func, args, {**kwargs, **ordered_kwargs}


def swap_val(value, func, *args, **kwargs):
    v_key = kwargs.pop("v_key", None)

    if v_key is None:
        return value, func, args, kwargs

    val_temp = value

    try:
        value = args[0]
    except IndexError as e:
        raise IndexError(
            "To swap out the value to a kwarg, there must at least one arg to replace it."
        ) from e

    return value, func, args[1:], {**kwargs, v_key: val_temp}


# DEPRECATED
def swap_val_auto(v_key):
    @caller
    def _swap_val(value, func, *args, **kwargs):
        if v_key is None:
            return value, func, args, kwargs

        kwargs = {**kwargs, v_key: value}

        return func(*args, **kwargs), func, args[1:], kwargs

    return _swap_val


# DEPRECATED
def swap_val_auto_optional(v_key_auto):
    @caller
    def _swap_val(value, func, *args, **kwargs):
        v_key = kwargs.pop("v_key", None)

        if v_key is not None:
            kwargs = {**kwargs, v_key: value}
            return func(*args, **kwargs), func, args[1:], kwargs

        if v_key_auto is None:
            return value, func, args, kwargs

        kwargs = {**kwargs, v_key_auto: value}

        return func(*args, **kwargs), func, args[1:], kwargs

    return _swap_val


def mem(value, func, *args, **kwargs):
    # mem APIs
    post_key = kwargs.get("__post", None)
    get_key = kwargs.get("__get", None)
    should_call = kwargs.get("__call", False)
    data_to_mount = kwargs.get("__mount", None)

    should_retain = kwargs.get("__retain", False)

    kwargs_mem: dict = kwargs.get("_mem", {})

    if post_key is not None:
        newMem = {**kwargs_mem, post_key: value}

        if get_key is None:
            if should_retain:
                newValue = value
            else:
                newValue = None

        if data_to_mount is not None:
            newValue = data_to_mount

        return newValue, func, args, {**kwargs, "_mem": newMem, "_skip": True}

    if get_key is not None:
        # throw old value away. need to store in mem before to not lose it
        if should_retain:
            newValue = kwargs_mem.get(get_key, None)
        else:
            newValue = kwargs_mem.pop(get_key, None)

        if should_call:
            # TODO: DO NOT CALL, return a partial to be called instead
            newValue = value(newValue)

        return newValue, func, args, {**kwargs, "_mem": kwargs_mem, "_skip": True}

    if data_to_mount is not None:
        newValue = data_to_mount
        return newValue, func, args, {**kwargs, "_skip": True}

    return value, func, args, {**kwargs, "_skip": False}


#########################################
# CONVENIENCE MONADS
#########################################
Maybe = compose(maybe)
Just = compose(just)
ForLoops = compose(debug, swap_val, maybe)


#########################################
# CONVENIENCE FUNCTIONS
#########################################


def chain(value):
    return monad(value, Just)


def loop(data, map=lambda x: x, filter=lambda x: True):
    return [map(i) for i in data if filter(i)]


def p_loop(value, *args, **kwargs):
    """Partial loop (cloop) to allow for chaining of nested loops together"""
    return partial(loop, *args, map=value, **kwargs)


def innerwrap(transform, value, pipeline):
    return transform(pipeline(value))


def wrap(pipeline, *args, **kwargs):
    """Feed data into processing pipeline first, and then wrap it nicely"""
    return partial(innerwrap, *args, pipeline=pipeline, **kwargs)


def outerwrap(transform, value, pipeline):
    return pipeline(transform(value))


def peel(pipeline, *args, **kwargs):
    """Peel the data first, then feed it in the data processing pipeline"""
    return partial(outerwrap, *args, pipeline=pipeline, **kwargs)


def call(func, *args, **kwargs):
    return func(*args, **kwargs)


def join(value, value2):
    def inner(data):
        return [value(data), value2(data)]

    return inner


def merge(value, value2):
    def inner(data):
        return {**value(data), **value2(data)}

    return inner


def p_merge(*args):
    return partial(merge, *args)


def while_loop(value, func, cond=True, break_cond=lambda x: False):
    if not cond:
        return value

    new_val = func(value)

    if break_cond(new_val):
        return new_val

    return while_loop(new_val, func, cond, break_cond)


def while_(value, func):
    new_val, should_break = func(value)

    if should_break:
        return new_val

    return while_loop(new_val, func)
