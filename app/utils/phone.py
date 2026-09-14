"""Phone-number validation, shared by everywhere a number is accepted.

The rules were written for a store's public contact number and are reused
verbatim for a delivery driver's: the same keypad, the same separators
people actually type, and the same refusal of a national format whose
country code we would have to guess.

Callers keep their own exception type — a bad social link is a
``SocialLinkError``, a bad driver number a ``DeliveryError`` — so this
module raises a plain :class:`PhoneNumberError` for each to translate,
rather than importing a service's exception into a util.
"""

import re

# 7 is the shortest national number in use anywhere; 15 is the E.164 ceiling.
MIN_DIGITS = 7
MAX_DIGITS = 15

# Digits plus the separators a person types: ``+961 3 100 001``,
# ``00961-3-100-001``, ``(03)/100.001``.
_TYPED = re.compile(r"^\+?[0-9 ()./-]+$")


class PhoneNumberError(ValueError):
    """A value that is not a dialable international phone number."""


def international_digits(value, field="phone"):
    """A typed phone number as bare international digits.

    Accepts ``+961 3 100 001``, ``00961-3-100-001`` and ``9613100001``. A
    number that still starts with a trunk ``0`` after that is a national
    format we cannot expand without guessing the country, so it is refused
    with an explanation rather than stored as something undialable.

    Returns the digits. A caller that wants to keep the number in the
    shape the user typed it can ignore the return value and use this
    purely as a check.
    """
    if not _TYPED.match(value):
        raise PhoneNumberError(f"'{value}' is not a valid {field} number")

    digits = "".join(ch for ch in value if ch.isdigit())

    if digits.startswith("00"):
        digits = digits[2:]

    if digits.startswith("0"):
        raise PhoneNumberError(
            "Include the country code, for example +961 3 123 456"
        )

    if not MIN_DIGITS <= len(digits) <= MAX_DIGITS:
        raise PhoneNumberError(f"'{value}' is not a valid {field} number")

    return digits
