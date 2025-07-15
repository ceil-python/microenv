import inspect

try:
    import uasyncio as asyncio
except ModuleNotFoundError:
    import asyncio


class MicroEnv:
    def __init__(
        self,
        descriptor,
        face,
        data,
        get,
        set_,
        _awaiters,
        _get_awaiter,
        _pending_get,
    ):
        self.descriptor = descriptor
        self.face = face
        self.data = data
        self.get = get
        self.set = set_
        self._awaiters = _awaiters
        self._get_awaiter = _get_awaiter
        self._pending_get = _pending_get


class Awaiter:
    def __init__(self):
        self._future = asyncio.get_event_loop().create_future()

    def resolve(self, value):
        if not self._future.done():
            self._future.set_result(value)

    def reject(self, reason):
        if not self._future.done():
            self._future.set_exception(
                reason if isinstance(reason, Exception) else Exception(str(reason))
            )

    @property
    def promise(self):
        return self._future

    def then(self, cb):
        self._future.add_done_callback(lambda fut: cb(fut.result()))


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
        else:
            return "unknown"

    if "children" not in descriptor:
        children = [
            {
                "key": k,
                "type": ("unknown" if k not in obj else infer_type(obj[k])),
            }
            for k in obj
        ]
        descriptor = {
            "key": "environment",
            "type": "environment",
            **descriptor,
            "children": children,
        }
    children_map = {c["key"]: c for c in descriptor.get("children", [])}
    _awaiters = {}
    _pending_get = {}

    def _get_awaiter(key):
        if key not in _awaiters:
            _awaiters[key] = Awaiter()
        return _awaiters[key]

    def get(key, caller=None, next_=False):
        child_descriptor = children_map.get(key)
        if not child_descriptor:
            raise KeyError(f'microenv: get non-existent property "{key}"')
        # privacy: only matter if the key is private and a caller is supplied
        if child_descriptor.get("private") and caller:
            raise PermissionError(f'microenv: get private property "{key}"')
        # async “next” request
        if next_:
            return _pending_get.setdefault(key, _get_awaiter(key).promise)
        # otherwise just return the current value
        return obj.get(key)

    def set_(key, value, caller=None):
        child_descriptor = children_map.get(key)
        if not child_descriptor:
            raise KeyError(f'microenv: set non-existent property "{key}"')
        if caller and child_descriptor.get("private"):
            raise PermissionError(f'microenv: set private property "{key}"')
        if key in _awaiters:
            _awaiters[key].resolve(value)
        obj[key] = value
        return value

    class Face:
        __slots__ = ()

        def __getattr__(self, key):
            v = get(key)
            if callable(v):
                return lambda payload, caller=None: v(payload, caller)
            return v

        def __setattr__(self, key, value):
            set_(key, value)

        def __getitem__(self, key):
            return self.__getattr__(key)

        def __setitem__(self, key, value):
            self.__setattr__(key, value)

    return MicroEnv(
        descriptor=descriptor,
        face=Face(),
        data=obj,
        get=get,
        set_=set_,
        _awaiters=_awaiters,
        _get_awaiter=_get_awaiter,
        _pending_get=_pending_get,
    )
