"""The explorer application — the HTTP layer over the catalogue read service.

Four things live here and nowhere else:

- the routers, which translate HTTP into read-service calls;
- the schemas, which describe what the API serves;
- the error handlers, which give every failure the same shape;
- the composition root, which wires them together.

The service layer below knows nothing about HTTP, and the scientific layers
know nothing about any of it.

`app` and `create_app` are re-exported here so that the console entry point
(`torne-explorer`) and the tests have one obvious place to look.
"""

from .application import app, create_app, main

__all__ = ["app", "create_app", "main"]
