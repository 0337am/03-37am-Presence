from __future__ import annotations


MIN_ARTWORK_UPGRADE_BYTES = 4096

ARTWORK_UPGRADE_NUMERATOR = 3
ARTWORK_UPGRADE_DENOMINATOR = 2


def should_upgrade_artwork(
    existing_size: int,
    candidate_size: int,
) -> bool:
    """
    Return True only when a new artwork candidate
    is an obvious upgrade over the cached image.

    Windows Media can briefly expose a small generic
    fallback image for Spotify local files. The first
    image must therefore not become permanent, but a
    later fallback must also not overwrite a healthy
    cover.

    The policy is deliberately conservative:
    - empty cache entries can always be repaired;
    - smaller or equal candidates never replace;
    - a replacement must be at least 4 KiB larger;
    - a replacement must be at least 1.5x the
      existing encoded size.
    """

    try:
        current = int(
            existing_size
        )

        candidate = int(
            candidate_size
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if candidate <= 0:
        return False

    if current <= 0:
        return True

    if candidate <= current:
        return False

    if (
        candidate - current
        < MIN_ARTWORK_UPGRADE_BYTES
    ):
        return False

    return (
        candidate
        * ARTWORK_UPGRADE_DENOMINATOR
        >= current
        * ARTWORK_UPGRADE_NUMERATOR
    )
