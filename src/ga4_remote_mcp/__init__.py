"""Remote GA4 MCP Server (Streamable HTTP)."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ga4-remote-mcp")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = ["__version__"]
