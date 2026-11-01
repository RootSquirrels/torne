"""The HTTP routers.

Each router owns one resource family and translates HTTP into calls on the
read service. The routers hold no business rule: a filter belongs to the
service, and an identifier that does not exist is a 404 the router raises.
"""

from . import assets, catalogue, health, missions, models, results, sources

__all__ = ["assets", "catalogue", "health", "missions", "models", "results", "sources"]
