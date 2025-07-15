# microenv

[![PyPI version](https://img.shields.io/pypi/v/microenv.svg)](https://pypi.org/project/microenv/)
[![License](https://img.shields.io/pypi/l/supply-demand.svg)](LICENSE)

A minimal Python environment abstraction with privacy controls and async “next” subscriptions.

## Installation

```bash
pip install microenv
```

or

```bash
python -m pip install microenv
```

or

```bash
python3 -m pip install microenv
```

## Quickstart

```python
import asyncio
from microenv import microenv

# Define initial data and optional descriptor
data = {"public": 1, "secret": "s3cr3t"}
descriptor = {
    "children": [
        {"key": "public", "type": "number"},
        {"key": "secret", "type": "string", "private": True},
    ]
}

# Create the environment
env = microenv(obj=data, descriptor=descriptor)
face = env.face

# Basic get / set via the face
print(face.public)         # → 1
face.public = 42
print(env.data["public"])  # → 42

# Privacy: direct .secret bypasses privacy checks on the face
print(face.secret)         # → "s3cr3t"
face.secret = "new!"
print(env.data["secret"])  # → "new!"

# Async “next” subscription: await the next update to a key
async def wait_for_update():
    fut = env.get("public", next_=True)
    print("waiting for next public…")
    val = await fut
    print("new public value:", val)

# Schedule waiter and then update
loop = asyncio.get_event_loop()
loop.create_task(wait_for_update())
loop.call_soon(lambda: setattr(face, "public", 99))
loop.run_forever()
```

## API

- `microenv(obj: dict, descriptor: dict = None) → MicroEnv`
  - `env.face` : proxy for getting/setting properties.
  - `env.get(key, caller=None, next_=False)` : synchronous read or, if `next_=True`, a Future resolving on next `set`.
  - `env.set(key, value, caller=None)` : update a property, resolving any pending “next” futures.

## License

This project is licensed under the MIT License.  
See [LICENSE](https://github.com/ceil-python/microenv/blob/main/LICENSE) for details.
