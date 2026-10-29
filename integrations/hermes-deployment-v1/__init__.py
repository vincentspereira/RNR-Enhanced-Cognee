"""Native directory-plugin wrapper; discovery uses register_memory_provider."""
def register(ctx):
    from .enhanced_cognee_hermes import register as register_provider
    register_provider(ctx)

__all__ = ["register"]
