# stats/last_updated.py
# Returns a formatted string with the latest data date from a given DataFrame.

import pandas as pd


def post_last_updated(df: pd.DataFrame) -> str | None:
    """Return a formatted string with the latest ref_date in df, or None on failure."""
    try:
        ref_dates = pd.to_datetime(df["ref_date"], format="%Y-%m-%d", errors="coerce")
        return f" Dashboard based on system data as of {ref_dates.max().strftime('%A, %B %d, %Y')}."
    except (KeyError, AttributeError):
        return None
