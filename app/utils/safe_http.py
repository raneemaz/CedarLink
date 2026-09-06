"""One guarded wrapper around ``urllib.request.urlopen``.

CedarLink makes exactly two outbound HTTP calls — the currency exchange-rate
lookup and the Twilio SMS/WhatsApp API — and both use URLs that come from
configuration or a hardcoded literal, never from a request. Even so, a bare
``urlopen`` will follow ``file://``, ``ftp://`` and other schemes if handed
one, so this refuses anything that is not ``http``/``https`` before the call.

That makes the ``# nosec B310`` below a checked assertion rather than a
silent suppression: the scheme is validated on the line above it.
"""

import urllib.request
from urllib.parse import urlparse

_ALLOWED_SCHEMES = {"http", "https"}


class UnsafeUrlError(ValueError):
    """The URL uses a scheme CedarLink will not open."""


def safe_urlopen(request_or_url, *, timeout):
    """``urlopen`` restricted to http/https. ``request_or_url`` is a
    ``urllib.request.Request`` or a URL string."""
    url = (
        request_or_url.full_url
        if isinstance(request_or_url, urllib.request.Request)
        else request_or_url
    )
    scheme = urlparse(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"refusing to open a {scheme or 'schemeless'} URL")

    # Scheme is validated to be http/https immediately above.
    return urllib.request.urlopen(request_or_url, timeout=timeout)  # nosec B310
