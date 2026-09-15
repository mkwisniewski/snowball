"""Shared CHF formatting for the app and the CLI."""


def chf(x: float) -> str:
    return f"CHF {x:,.0f}"


def chf_short(x: float) -> str:
    """Compact format so big numbers never truncate with '...'."""
    ax = abs(x)
    if ax >= 1_000_000_000:
        return f"CHF {x / 1_000_000_000:.2f} B"
    if ax >= 1_000_000:
        return f"CHF {x / 1_000_000:.2f} M"
    if ax >= 10_000:
        return f"CHF {x / 1_000:.0f} k"
    return chf(x)
