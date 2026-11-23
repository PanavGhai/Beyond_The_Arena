"""Fast, deterministic conversion of user seed text to a 32-bit seed."""

import hashlib


SEED_MODULUS = 1 << 32


def normalize_seed(value):
    """Return a stable 32-bit seed from decimal input or arbitrary text.

    Decimal strings are reduced digit-by-digit modulo 2**32, avoiding Python's
    large-integer parsing limit and keeping memory use constant. Other text is
    mapped through a 32-bit BLAKE2s digest.
    """
    raw = str(value).strip()
    if not raw:
        raise ValueError("Seed cannot be empty")

    digits = raw
    sign = 1
    if digits[0] in "+-":
        if digits[0] == "-":
            sign = -1
        digits = digits[1:]

    if digits and all("0" <= char <= "9" for char in digits):
        number = 0
        for digit in digits:
            number = (number * 10 + ord(digit) - ord("0")) % SEED_MODULUS
        return (sign * number) % SEED_MODULUS

    digest = hashlib.blake2s(raw.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, byteorder="big")
