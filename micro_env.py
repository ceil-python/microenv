from typing import Any, Dict, List, Optional, TypeVar, Callable, Union, Protocol
from supply_demand import supply_demand


class GetterProtocol(Protocol):
    def __call__(self, data: Dict[str, Any]) -> Any: ...


class SetterProtocol(Protocol):
    def __call__(self, data: Dict[str, Any]) -> Any: ...


def create_get(custom: Optional[GetterProtocol] = None) -> Any:
    def get_supplier(data: Dict[str, Any], context: Dict[str, str]) -> Any:
        descriptor = data.get("descriptor")
        obj = data.get("obj")
        caller = data.get("caller")
        next_val = data.get("next")
        key = context["key"]

        if custom:
            return custom(
                {
                    "key": key,
                    "descriptor": descriptor,
                    "obj": obj,
                    "caller": caller,
                    "next": next_val,
                }
            )

        return obj.get(key, descriptor.get("defaultData") if descriptor else None)

    return get_supplier


def create_set(custom: Optional[SetterProtocol] = None) -> Any:
    def set_supplier(data: Dict[str, Any], context: Dict[str, str]) -> Any:
        obj = data.get("obj")
        descriptor = data.get("descriptor")
        value = data.get("value")
        caller = data.get("caller")
        key = context["key"]

        if custom:
            return custom(
                {
                    "key": key,
                    "descriptor": descriptor,
                    "obj": obj,
                    "value": value,
                    "caller": caller,
                }
            )

        obj[key] = value
        return value

    return set_supplier


def micro_env(obj=None, descriptor=None, suppliers=None):
    if obj is None:
        obj = {}
    if suppliers is None:
        suppliers = {}
    if descriptor is None:
        descriptor = {}
    return supply_demand(
        {
            "obj": obj,
            "descriptor": descriptor,
        },
        {
            **suppliers,
            "get": create_get(),
            "set": create_set(),
        },
    )
