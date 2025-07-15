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
        get_,
        set_,
        _awaiters,
        _get_awaiter,
    ):
        self.descriptor = descriptor
        self.face = face
        self.data = data
        self.get = get_
        self.set = set_
        self._awaiters = _awaiters
        self._get_awaiter = _get_awaiter


class Awaiter:
    def __init__(self):
        # Create a Future on the current loop
        self._future = asyncio.get_event_loop().create_future()

    @property
    def promise(self):
        return self._future

    def resolve(self, value):
        if self._future.done():
            return

        if hasattr(value, "__await__"):
            loop = asyncio.get_event_loop()

            async def _chain():
                try:
                    res = await value
                except Exception as e:
                    if not self._future.done():
                        self._future.set_exception(e)
                else:
                    if not self._future.done():
                        self._future.set_result(res)

            loop.create_task(_chain())
        else:
            self._future.set_result(value)

    def reject(self, reason):
        if not self._future.done():
            self._future.set_exception(
                reason if isinstance(reason, Exception) else Exception(str(reason))
            )

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
            {"key": k, "type": ("unknown" if k not in obj else infer_type(obj[k]))}
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

    def _get_awaiter(key):
        if key not in _awaiters:
            _awaiters[key] = Awaiter()
        return _awaiters[key]

    def get_(key, caller=None, next_=False):
        cd = children_map.get(key)
        if not cd or (cd.get("private") and caller):
            raise KeyError(f'microenv: get non-existent property "{key}"')
        if next_:
            return _get_awaiter(key).promise
        if "get" in overrides:
            return overrides["get"](key, _ref, caller)
        return obj.get(key)

    def set_(key, value, caller=None):
        cd = children_map.get(key)
        if not cd or (cd.get("private") and caller):
            raise KeyError(f'microenv: set non-existent property "{key}"')

        if "set" in overrides:
            result = overrides["set"](key, value, _ref, caller)
        else:
            result = value

        if hasattr(result, "__await__"):
            if key in _awaiters:
                loop = asyncio.get_event_loop()
                task = loop.create_task(result)

                if key in _awaiters:
                    _awaiters[key].resolve(task)

                async def _wrapper():
                    return await task

                result = _wrapper()
        else:
            if key in _awaiters:
                _awaiters[key].resolve(result)

        obj[key] = result
        return result

    class Face:
        __slots__ = ()

        def __getattr__(self, key):
            v = get_(key)
            if callable(v):
                return lambda payload, caller=None: v(payload, caller)
            return v

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
        _awaiters=_awaiters,
        _get_awaiter=_get_awaiter,
    )
    return _ref
