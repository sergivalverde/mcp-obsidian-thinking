import asyncio

def main():
    """Main entry point for the package."""
    # Import here to avoid circular import warnings
    from . import server
    asyncio.run(server.main())

__all__ = ['main']