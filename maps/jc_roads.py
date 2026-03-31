# maps/jc_roads.py
# Reference map of the Jackson County, MO road network from the TIGER/Line 2025 roads shapefile.
# Roads are styled by MTFCC class (primary, secondary, local). Local roads start hidden
# in the layer control to keep initial load fast; users can toggle them on.

import folium
import geopandas as gpd
import streamlit as st
from shapely.geometry import box as shapely_box
from streamlit_folium import st_folium

_ROADS_PATH = "assets/shp/tl_2025_29095_roads/tl_2025_29095_roads.shp"
_COUNTY_SHP_PATH = "assets/shp/tl_2025_us_county/tl_2025_us_county.shp"
_CENTER = [+39.0053640, -094.3432105]
_ZOOM = 11

# MTFCC → (layer label, color, weight, opacity, show by default)
_ROAD_CLASSES = {
    "S1100": ("Primary Road",   "#1a6fba", 2.5, 0.9, True),
    "S1200": ("Secondary Road", "#4da6ff", 1.5, 0.8, True),
    "S1400": ("Local Road",     "#6b7a99", 0.5, 0.5, False),
}
_OTHER_STYLE = ("Other Road", "#8a93a8", 0.4, 0.4, False)

# Substrings matched case-insensitively against FULLNAME within S1400 roads.
# Matching roads are pulled into their own visible layer for orientation reference.
_NAMED_STREETS_PATTERNS = ["Troost", "Independence", "Prospect"]
_NAMED_STREETS_STYLE = ("#60aeff", 1.2, 0.85)  # color, weight, opacity

# Exact FULLNAME matches for roads to verify / export. Rendered on top in a distinct style.
_HIGHLIGHT_STREETS = {"Troost Ave", "Prospect Ave"}
_HIGHLIGHT_STYLE = ("#ff6b35", 4.0, 1.0)  # orange, thick, fully opaque

# Clip highlighted streets to segments between these two east-west roads.
# Derived dynamically from the shapefile itself — no hardcoded coordinates.
_CLIP_NORTH_PATTERN = "Independence"   # cut off north of this road
_CLIP_SOUTH_PATTERN = "Bannister"      # cut off south of this road

_TOOLTIP_STYLE = (
    "background-color: #1b2e45;"
    "color: #e8edf2;"
    "border: 1px solid #2a3f5f;"
    "border-radius: 4px;"
    "font-family: Inter, sans-serif;"
    "font-size: 13px;"
)


@st.cache_data
def _load_geodata() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Load and cache roads shapefile and Jackson County boundary."""
    roads = gpd.read_file(_ROADS_PATH).to_crs(epsg=4326)

    counties = gpd.read_file(_COUNTY_SHP_PATH).to_crs(epsg=4326)
    jc_boundary = counties[
        (counties["STATEFP"] == "29") & (counties["COUNTYFP"] == "095")
    ][["geometry"]].copy()

    return roads, jc_boundary


def _build_highlight_clip_box(roads: gpd.GeoDataFrame):
    """
    Derive a clipping envelope from the latitude of two east-west reference roads.
    Returns a shapely box, or None if either road is not found.
    """
    north_segs = roads[roads["FULLNAME"].str.contains(_CLIP_NORTH_PATTERN, case=False, na=False)]
    south_segs = roads[roads["FULLNAME"].str.contains(_CLIP_SOUTH_PATTERN, case=False, na=False)]

    if north_segs.empty or south_segs.empty:
        return None

    # Use the median miny of the northern road as the top clip edge,
    # and the median maxy of the southern road as the bottom clip edge.
    north_y = float(north_segs.geometry.bounds["miny"].median())
    south_y = float(south_segs.geometry.bounds["maxy"].median())

    # Wide x extent to cover all of Jackson County
    return shapely_box(-94.8, south_y, -94.0, north_y)


def _build_roads_map(roads: gpd.GeoDataFrame, jc_boundary: gpd.GeoDataFrame) -> folium.Map:
    m = folium.Map(
        location=_CENTER,
        zoom_start=_ZOOM,
        tiles="CartoDB positron",
        prefer_canvas=True,
    )

    folium.GeoJson(
        jc_boundary,
        name="Jackson County Boundary",
        style_function=lambda _: {
            "fillColor": "none",
            "color": "#1a6fba",
            "weight": 2.5,
            "dashArray": "6 4",
        },
    ).add_to(m)

    # Named streets: match across S1200 and S1400 so roads like Independence Ave/Blvd
    # are captured consistently regardless of how TIGER classifies each segment.
    # S1100 (primary) is always fully shown and excluded from this mask.
    pattern = "|".join(_NAMED_STREETS_PATTERNS)
    named_mask = (
        roads["MTFCC"].isin(["S1200", "S1400"]) &
        roads["FULLNAME"].str.contains(pattern, case=False, na=False)
    )
    named_streets = roads[named_mask][["FULLNAME", "MTFCC", "geometry"]].copy()

    if not named_streets.empty:
        nc, nw, no = _NAMED_STREETS_STYLE
        folium.GeoJson(
            named_streets,
            name="Named Streets",
            show=True,
            style_function=lambda _, c=nc, w=nw, o=no: {
                "color": c,
                "weight": w,
                "opacity": o,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["FULLNAME"],
                aliases=["Road"],
                localize=True,
                sticky=True,
                style=_TOOLTIP_STYLE,
            ),
        ).add_to(m)

    # One layer per road class, excluding any segments already in named streets
    for mtfcc, (label, color, weight, opacity, show) in _ROAD_CLASSES.items():
        if mtfcc in ("S1200", "S1400"):
            subset = roads[roads["MTFCC"].eq(mtfcc) & ~named_mask][["FULLNAME", "MTFCC", "geometry"]].copy()
        else:
            subset = roads[roads["MTFCC"] == mtfcc][["FULLNAME", "MTFCC", "geometry"]].copy()
        if subset.empty:
            continue
        folium.GeoJson(
            subset,
            name=label,
            show=show,
            style_function=lambda _, c=color, w=weight, o=opacity: {
                "color": c,
                "weight": w,
                "opacity": o,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["FULLNAME"],
                aliases=["Road"],
                localize=True,
                sticky=True,
                style=_TOOLTIP_STYLE,
            ),
        ).add_to(m)

    # Catch-all for any MTFCC codes not covered above
    other = roads[~roads["MTFCC"].isin(_ROAD_CLASSES)][["FULLNAME", "MTFCC", "geometry"]].copy()
    if not other.empty:
        label, color, weight, opacity, show = _OTHER_STYLE
        folium.GeoJson(
            other,
            name=label,
            show=show,
            style_function=lambda _, c=color, w=weight, o=opacity: {
                "color": c,
                "weight": w,
                "opacity": o,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["FULLNAME", "MTFCC"],
                aliases=["Road", "Class"],
                localize=True,
                sticky=True,
                style=_TOOLTIP_STYLE,
            ),
        ).add_to(m)

    # Highlight layer — exact FULLNAME matches, clipped to the band between
    # Independence Ave (north) and Bannister Road (south)
    highlight = roads[roads["FULLNAME"].isin(_HIGHLIGHT_STREETS)][["FULLNAME", "LINEARID", "geometry"]].copy()
    clip_box = _build_highlight_clip_box(roads)
    if clip_box is not None and not highlight.empty:
        highlight = highlight.clip(clip_box)
    if not highlight.empty:
        hc, hw, ho = _HIGHLIGHT_STYLE
        folium.GeoJson(
            highlight,
            name="Highlighted Streets",
            show=True,
            style_function=lambda _, c=hc, w=hw, o=ho: {
                "color": c,
                "weight": w,
                "opacity": o,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["FULLNAME", "LINEARID"],
                aliases=["Road", "Segment ID"],
                localize=True,
                sticky=True,
                style=_TOOLTIP_STYLE,
            ),
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def render_jc_roads() -> None:
    """Render the Jackson County road network reference map."""
    roads, jc_boundary = _load_geodata()

    pattern = "|".join(_NAMED_STREETS_PATTERNS)
    named_mask = (
        roads["MTFCC"].isin(["S1200", "S1400"]) &
        roads["FULLNAME"].str.contains(pattern, case=False, na=False)
    )

    with st.container(border=True):
        st.header(":material/route: Jackson County Road Network")
        st.caption(
            "Road network for Jackson County, MO from the U.S. Census Bureau TIGER/Line 2025 shapefile. "
            "Roads are grouped by class: primary (interstates / major highways), secondary (arterials), "
            "named local streets (Troost Ave, Independence Ave), and all other local streets. "
            "Other local roads are hidden by default — use the layer control to toggle them on. "
            "Hover over any road to see its name."
        )

        st_folium(
            _build_roads_map(roads, jc_boundary),
            # width="stretch",
            height=620,
            returned_objects=[],
        )

        st.subheader("Named Streets Captured")
        named_table = (
            roads[named_mask][["FULLNAME", "MTFCC"]]
            .drop_duplicates("FULLNAME")
            .rename(columns={"FULLNAME": "Road Name", "MTFCC": "Class"})
            .replace({"Class": {"S1200": "Secondary Road", "S1400": "Local Road"}})
            .sort_values("Road Name")
            .reset_index(drop=True)
        )
        st.dataframe(named_table, hide_index=True)
