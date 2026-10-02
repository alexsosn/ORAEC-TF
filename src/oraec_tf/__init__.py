"""ORAEC to Text-Fabric conversion tools."""

from .source import (
    DEFAULT_SOURCE_REVISION,
    SOURCE_REPOSITORY,
    SourceSnapshot,
    fetch_source,
    validate_revision,
    verify_source,
)

__all__ = [
    "DEFAULT_SOURCE_REVISION",
    "SOURCE_REPOSITORY",
    "SourceSnapshot",
    "fetch_source",
    "validate_revision",
    "verify_source",
]

__version__ = "0.1.0.dev0"
