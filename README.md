# micro env

Minimal implementation of environment with different data types represented as a tree.

```python
from env import MicroEnv

if __name__ == "__main__":
    def test():
        return 2
    micro_env = MicroEnv(
        {"prop_a": 1, "prop_b": 2, "prop_c": test},
        {
            "id": "my_env",
            "children": [
                {
                    "prop_d": {"type": "int", "value": 1},
                },
                {"id": "my_env1"},
            ],
        },
    )
    micro_env.set("prop_a", 10)
    micro_env.get("prop_a")
    micro_env.set("prop_d", test, "root/my_env1")
    micro_env.get("prop_d", "root/my_env1")
```