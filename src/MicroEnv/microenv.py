import asyncio

try:
    import inspect

    is_awaitable = inspect.isawaitable
except ImportError:
    # MicroPython
    def is_awaitable(val):
        is_awaitable = True
        try:
            return getattr(val, "__await__")
        except:
            try:
                getattr(val, "__next__")
            except:
                is_awaitable = False
        return is_awaitable


class MicroEnv:
    def __init__(
        self,
        descriptor,
        face,
        data,
        get_,
        set_,
    ):
        self.descriptor = descriptor
        self.face = face
        self.data = data
        self.get = get_
        self.set = set_


class MicroAwaitQueue:
    def __init__(self):
        self._waiters = []
        self._result = None
        self._done = None

    async def wait(self):
        if self._done:
            return self._result

        ev = asyncio.Event()
        self._waiters.append(ev)
        await ev.wait()
        return self._result

    def resolve_all(self, value):
        if self._done:
            return

        self._done = True
        self._result = value
        for ev in self._waiters:
            ev.set()
        self._waiters.clear()


def microenv(obj=None, descriptor=None, overrides=None):
    obj = obj or {}
    descriptor = descriptor or {}
    overrides = overrides or {}

    def infer_type(v):
        if v is None:
            return "null"
        elif isinstance(v, str):
            return "string"
        elif isinstance(v, bool):
            return "boolean"
        elif isinstance(v, (int, float)):
            return "number"
        elif isinstance(v, list):
            return "array"
        elif isinstance(v, dict):
            return "object"
        elif hasattr(v, "__await__"):
            return "promise"
        elif callable(v):
            return "function"
        else:
            return "unknown"

    if "children" not in descriptor:
        children = [
            {"key": k, "type": ("unknown" if k not in obj else infer_type(obj[k]))}
            for k in obj
        ]
        new_descriptor = {"key": "environment", "type": "environment"}
        new_descriptor.update(descriptor)
        new_descriptor["children"] = children
        descriptor = new_descriptor

    children_map = {c["key"]: c for c in descriptor.get("children", [])}
    _awaiters = {}

    def get_(key, caller=None, next_=False):
        cd = children_map.get(key)
        if not cd or (cd.get("private") and caller):
            raise KeyError(f'microenv: get non-existent property "{key}"')
        if next_:
            if key not in _awaiters:
                _awaiters[key] = MicroAwaitQueue()
            return _awaiters[key].wait()
        if "get" in overrides:
            return overrides["get"](key, _ref, caller, next_)
        return obj.get(key)

    def set_(key, value, caller=None):
        cd = children_map.get(key)
        if not cd or (cd.get("private") and caller):
            raise KeyError(f'microenv: set non-existent property "{key}"')

        if "set" in overrides:
            result = overrides["set"](key, value, _ref, caller)
        else:
            result = value

        if is_awaitable(result):

            async def resolver():
                resolved = await result
                obj[key] = resolved
                if key in _awaiters:
                    _awaiters[key].resolve_all(resolved)
                return resolved

            return asyncio.get_event_loop().create_task(resolver())
        else:
            obj[key] = result
            if key in _awaiters:
                _awaiters[key].resolve_all(result)
        return result

    class Face:
        __slots__ = ()

        def __getattr__(self, key):
            return get_(key)

        def __setattr__(self, key, value):
            set_(key, value)

        def __getitem__(self, key):
            return self.__getattr__(key)

        def __setitem__(self, key, value):
            self.__setattr__(key, value)

    _ref = MicroEnv(
        descriptor=descriptor,
        face=Face(),
        data=obj,
        get_=get_,
        set_=set_,
    )
    return _ref
