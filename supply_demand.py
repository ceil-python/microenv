from typing import Any, Callable, Dict, Optional, Union


# Type aliases
DemandProps = Dict[str, Any]
SupplyMethod = Callable[[Optional[Any], "Scope"], Any]
ScopedDemand = Callable[[DemandProps], Any]
SuppliersMerge = Dict[str, Union[bool, Dict[str, SupplyMethod], list]]
ExtendSuppliersMethod = Callable[
    [Dict[str, SupplyMethod], SuppliersMerge], Dict[str, SupplyMethod]
]
DemandReturn = Any


# Supplier function type (Callable with specific signature)
def supplier_type(data: Optional[Any], scope: "Scope") -> DemandReturn:
    pass


# Scope class for holding demand context
class Scope:
    def __init__(self, key: str, _type: str, path: str, demand: ScopedDemand):
        self.key = key
        self.type = _type
        self.path = path
        self.demand = demand


# Function to merge suppliers with operations: clear, add, remove
def merge_suppliers(
    original: Dict[str, SupplyMethod], merge_op: SuppliersMerge
) -> Dict[str, SupplyMethod]:
    merged = {}
    if not merge_op.get("clear", False):
        merged.update(original)
    merged.update(merge_op.get("add", {}))
    for key in merge_op.get("remove", []):
        merged.pop(key, None)
    return merged


# Main function to handle global demand
def global_demand(props: DemandProps) -> DemandReturn:
    key = props["key"]
    _type = props["type"]
    path = props["path"]
    suppliers = props.get("suppliers", {})

    if not key or not _type or not path:
        raise ValueError("Key, Type, and Path are required in global_demand.")

    print(f"Global demand called with: Key: {key}, Type: {_type}, Path: {path}")

    supplier_func = suppliers.get(_type)
    if supplier_func:
        print(f"Calling supplier for type: {_type}")
        return supplier_func(
            props.get("data"),
            {
                "key": key,
                "type": _type,
                "path": path,
                "demand": create_scoped_demand(props),
            },
        )
    print(f"Supplier not found for type: {_type}")


# Function to create a demand function that is scoped
def create_scoped_demand(super_props: DemandProps) -> ScopedDemand:
    def demand_func(props: DemandProps) -> DemandReturn:
        demand_key = props.get("key", super_props["key"])

        if "type" not in props:
            raise ValueError("Type is required in scoped demand.")

        path = f"{super_props['path']}/{demand_key}({props['type']})"
        new_suppliers = merge_suppliers(
            super_props["suppliers"], props.get("suppliers_merge", {})
        )

        return global_demand(
            {
                "key": demand_key,
                "type": props["type"],
                "path": path,
                "data": props.get("data"),
                "suppliers": new_suppliers,
            }
        )

    return demand_func


# Initiate supply and demand process
def supply_demand(
    root_supplier: SupplyMethod, suppliers: Dict[str, SupplyMethod]
) -> DemandReturn:
    suppliers_copy = suppliers.copy()
    suppliers_copy["$$root"] = root_supplier
    return global_demand(
        {
            "key": "root",
            "type": "$$root",
            "path": "root",
            "suppliers": suppliers_copy,
        }
    )


# Example supplier functions
def first_supplier(data: Optional[Any], scope: Scope) -> str:
    print("First supplier function called.")
    return "1st"


def second_supplier(data: Optional[Any], scope: Scope) -> str:
    print("Second supplier function called.")
    return "2nd"


def third_supplier(data: Optional[Any], scope: Scope) -> DemandReturn:
    print("Third supplier function called.")
    return scope["demand"](
        {
            "type": "first",
        }
    )


# Main execution
if __name__ == "__main__":
    suppliers = {"first": first_supplier, "second": second_supplier}

    def root_supplier(data: Optional[Any], scope: Scope) -> None:
        print("Root supplier function called.")
        res = scope["demand"](
            {
                "type": "third",
                "suppliers_merge": {"add": {"third": third_supplier}},
            }
        )
        print("Root supplier function call result is:", res)

    supply_demand(root_supplier, suppliers)
