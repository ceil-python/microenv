import types


class MicroEnv:
    def __init__(self, obj, descriptor) -> None:
        self.descriptor = descriptor
        self.id = descriptor["id"]
        self.face = obj
        self.data = {}
        self.supply_demand(obj, descriptor)

    def create_scoped_demand(self, root_props, props, suppliers={}) -> object:
        demand_key = props[1]["id"]
        path = f"{root_props['path']}/{demand_key}"
        self.data[path] = {
            "key": demand_key,
            "type": "chidlren",
            "path": path,
            "data": props[0],
            "suppliers": suppliers,
        }
        return self.data[path]

    def global_demand(self, props) -> object:
        key = props["key"]
        _type = props["type"]
        path = props["path"]

        if not key or not _type or not path:
            raise ValueError("Key, Type, and Path are required in global_demand.")

        if "children" in self.descriptor:
            self.create_scoped_demand(
                props, self.descriptor["children"]
            )

        return props

    def supply_demand(self, obj, descriptor, suppliers={}) -> object:
        data = descriptor.copy()
        data["$$root"] = obj
        self.data["root"] = {
            "key": "root",
            "type": "$$root",
            "path": "root",
            "data": obj,
            "suppliers": suppliers,
        }
        self.global_demand(self.data["root"])

    def get(self, key, path="root") -> any:
        if isinstance(self.data[path]["data"][key], types.FunctionType):
            return self.data[path]["data"][key]()
        else:
            return self.data[path]["data"][key]

    def set(self, key, value, path="root") -> any:
        self.data[path]["data"][key] = value
        return self.data[path]["data"][key]
