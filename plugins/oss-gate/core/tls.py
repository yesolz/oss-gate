"""Explicit additional CA trust, without changing verification or ambient settings."""

from contextvars import ContextVar
import hashlib
from pathlib import Path
import ssl

import certifi

MAX_CA_BYTES = 1024 * 1024
EVIDENCE = ContextVar("tls_trust_evidence", default=None)


class TLSConfigurationError(ValueError):
    pass


def build_context(config):
    """Load once per operation; offline policy evaluation never opens this file."""
    path = (config or {}).get("network", {}).get("additional_ca_file")
    if path is None:
        return True, None
    try:
        source = Path(path)
        if not source.is_absolute() or not source.is_file():
            raise ValueError("CA file must be an absolute regular file")
        with source.open("rb") as stream:
            data = stream.read(MAX_CA_BYTES + 1)
        if not data or len(data) > MAX_CA_BYTES or b"PRIVATE KEY" in data:
            raise ValueError("invalid CA bundle")
        context = ssl.create_default_context(cafile=certifi.where())
        context.load_verify_locations(cadata=data.decode("ascii"))
    except (OSError, ValueError) as exc:
        # File paths and certificate contents must not leak through diagnostics.
        raise TLSConfigurationError("cannot load selected additional CA certificates") from exc
    return context, {
        "base": "certifi",
        "certifi_version": certifi.__version__,
        "additional_ca_sha256": hashlib.sha256(data).hexdigest(),
    }
