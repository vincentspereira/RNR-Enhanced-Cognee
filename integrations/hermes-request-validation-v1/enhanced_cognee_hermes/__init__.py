"""Native Hermes provider. Import performs no configuration or backend access."""
from .provider import EnhancedCogneeProvider


def register(ctx):
    ctx.register_memory_provider(EnhancedCogneeProvider())


__all__ = ["EnhancedCogneeProvider", "register"]
