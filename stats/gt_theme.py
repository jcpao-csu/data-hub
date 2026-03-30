# stats/gt_theme.py
# Shared great_tables theme utilities for the JCPAO Dashboard.
# Import apply_dark_theme and color constants into any stats/*.py file that uses GT.

from great_tables import GT, loc, google_font
from great_tables.style import text

# Palette constants — sourced from .streamlit/config.toml
GT_PRIMARY   = "#4da6ff"   # primaryColor
GT_GREEN     = "#3db87a"   # greenColor
GT_RED       = "#e05c5c"   # redColor
GT_ORANGE    = "#f28e2b"   # orangeColor
GT_YELLOW    = "#f5c842"   # yellowColor
GT_VIOLET    = "#9b72e6"   # violetColor
GT_GRAY      = "#6b7a99"   # grayColor
GT_BORDER    = "#2a3f5f"   # borderColor
GT_BG        = "#0d1b2a"   # backgroundColor
GT_BG_SECONDARY = "#1b2e45"  # secondaryBackgroundColor
GT_TEXT      = "#e8edf2"   # textColor


def apply_dark_theme(gt: GT) -> GT:
    """
    Apply the standard JCPAO dark-navy theme to a GT table.
    Chain this at the end of any GT builder function:

        return apply_dark_theme(GT(df).tab_header(...).cols_label(...))
    """
    return (
        gt
        .opt_table_font(font=google_font("Inter"))
        .tab_options(
            # Backgrounds
            table_background_color=GT_BG,
            heading_background_color=GT_BG,
            column_labels_background_color=GT_BG_SECONDARY,
            stub_background_color=GT_BG_SECONDARY,
            row_striping_background_color=GT_BG_SECONDARY,

            # Text
            table_font_color=GT_TEXT,
            column_labels_font_weight="600",
            heading_title_font_size="16px",
            heading_title_font_weight="700",

            # Borders
            table_border_top_style="hidden",
            table_border_bottom_style="hidden",
            column_labels_border_top_color=GT_BORDER,
            column_labels_border_bottom_color=GT_TEXT,
            row_striping_include_stub=True,

            # Sizing
            table_font_size="15px",
            data_row_padding="6px",
        )
        .tab_style(
            style=text(color=GT_TEXT, size="13px", weight="bold"),
            locations=loc.subtitle(),
        )
        .tab_style(
            style=text(weight="bold"),
            locations=loc.title(),
        )
    )
