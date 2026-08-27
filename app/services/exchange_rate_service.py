"""Exchange-rate lookup for display-only currency conversion.

The rate is fetched from an external API and cached in-process. Only a
*successful* fetch is ever stored, so:

* a fresh successful result is served straight from the cache (within the TTL);
* if the API is unreachable but we have an older successful result, that result
  is served and flagged ``stale`` (its timestamp is not refreshed, so the very
  next call tries the API again);
* if no successful fetch has ever happened, the configured fallback is returned
  inline and never cached, so every subsequent call keeps retrying the API.

``get_rates()`` never raises.
"""

import json
import time
import urllib.request

from flask import current_app

# Only ever holds a SUCCESSFUL API result.
_cache = {"rates": None, "fetched_at": 0.0}


def _payload(rates, fetched_at, stale, source):
    return {
        "base": current_app.config["BASE_CURRENCY"],
        "rates": rates,
        "fetched_at": fetched_at,
        "stale": stale,
        "source": source,
    }


def get_rates():
    """Return ``{base, rates, fetched_at, stale, source}``. Never raises."""
    cfg = current_app.config
    now = time.time()

    # Fresh successful API result -> serve as-is.
    if (
        _cache["rates"]
        and now - _cache["fetched_at"] < cfg["EXCHANGE_RATE_TTL_SECONDS"]
    ):
        return _payload(
            _cache["rates"], _cache["fetched_at"], stale=False, source="api"
        )

    # Not fresh -> try (re)fetching every time.
    try:
        request = urllib.request.Request(
            cfg["EXCHANGE_RATE_API_URL"],
            headers={"User-Agent": "CedarLink/1.0"},
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode())

        api_rates = data.get("rates") or {}

        rates = {
            code: float(api_rates[code])
            for code in cfg["SUPPORTED_CURRENCIES"]
            if code in api_rates
        }
        rates.setdefault(cfg["BASE_CURRENCY"], 1.0)

        # Only cache when we actually got every supported currency.
        if all(code in rates for code in cfg["SUPPORTED_CURRENCIES"]):
            _cache.update(rates=rates, fetched_at=now)
            return _payload(rates, now, stale=False, source="api")

        raise ValueError("incomplete rate set from exchange-rate API")
    except Exception:
        if _cache["rates"]:
            # Last good API value; timestamp left stale so we retry next call.
            return _payload(
                _cache["rates"], _cache["fetched_at"], stale=True, source="api"
            )

        return _payload(
            dict(cfg["EXCHANGE_RATE_FALLBACK"]),
            now,
            stale=True,
            source="fallback",
        )
