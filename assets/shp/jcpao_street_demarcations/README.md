# JCPAO Street Demarcations

Shapefile of confirmed street segments used as geographic demarcation lines in JCPAO mapping.
Exported from the U.S. Census Bureau TIGER/Line 2025 All Roads shapefile for Jackson County, MO
(`tl_2025_29095_roads`).

## Segments Included

| Label | LINEARID | FULLNAME |
|---|---|---|
| Troost Ave | 110381509740 | Troost Ave |
| Prospect Ave | 1106087449270 | Prospect Ave |
| Independence Ave | 110381524857 | Independence Ave |

---

## Understanding the TIGER/Line Roads Data

### Data Organization

The source file (`tl_2025_29095_roads.shp`) is a **county-level extract** from the U.S. Census
Bureau's TIGER/Line 2025 dataset. TIGER (Topologically Integrated Geographic Encoding and
Referencing) represents roads as individual **line segments** — a single named road like Troost Ave
is broken into many separate segments, each with its own `LINEARID`. Segments are split at
intersections, jurisdictional boundaries, and wherever road attributes change.

The file covers **Jackson County, Missouri** (FIPS state `29`, county `095`). The coordinate
reference system is **EPSG:4326** (WGS 84, decimal degrees).

---

## Column Codebook

### LINEARID — Linear Feature Identifier
- **Type:** String
- **Description:** Unique identifier for each road segment. Assigned by the Census Bureau and
  stable across TIGER editions within a release year. A single named road will have many
  LINEARIDs — one per segment.
- **Example:** `110381509740`

### FULLNAME — Full Road Name
- **Type:** String (nullable)
- **Description:** The complete road name, assembled from prefix qualifier, prefix direction,
  prefix type, base name, suffix type, suffix direction, and suffix qualifier — whichever
  components are present. May be blank for unnamed roads (alleys, ramps, etc.).
- **Example:** `Troost Ave`, `E Independence Ave`, `I- 70`

### RTTYP — Route Type Code
- **Type:** String (single character, nullable)
- **Description:** Classifies the road by its route designation system.

| Code | Meaning |
|------|---------|
| `C` | County route |
| `I` | Interstate highway |
| `M` | Common name (no official route number) |
| `O` | Other |
| `S` | State-recognized route |
| `U` | U.S. route |
| *(blank)* | Not designated |

### MTFCC — MAF/TIGER Feature Class Code
- **Type:** String
- **Description:** Classifies the road by its physical and functional type. Used to style roads
  by importance in this map (primary → secondary → local).

| Code | Class | Description |
|------|-------|-------------|
| `S1100` | Primary Road | Limited-access highways (interstates, controlled-access freeways) |
| `S1200` | Secondary Road | Arterials — U.S. and state highways not qualifying as S1100 |
| `S1400` | Local Road | Local neighborhood roads, rural roads, and city streets |
| `S1500` | Vehicular Trail | Unimproved dirt/gravel roads passable by 4WD |
| `S1630` | Ramp | On/off ramps connecting roads at different grades |
| `S1640` | Service Drive | Frontage roads and service drives alongside limited-access highways |
| `S1710` | Walkway / Pedestrian Trail | Foot paths not accessible to motor vehicles |
| `S1720` | Stairway | Pedestrian stairway |
| `S1730` | Alley | Alleyway between buildings |
| `S1740` | Private Road | Roads restricted to service or private vehicles |
| `S1750` | Internal Census Use | Census Bureau internal use only |
| `S1780` | Parking Lot Road | Road within a parking facility |
| `S1820` | Bike Path or Trail | Designated bicycle path |
| `S1830` | Bridle Path | Horse trail |
| `S2000` | Road Median | Median strip of a divided road |

### geometry — LineString
- **Type:** LineString / MultiLineString (EPSG:4326)
- **Description:** The spatial representation of the road segment as a sequence of coordinate
  pairs (longitude, latitude). Most segments are simple LineStrings; complex intersections may
  be MultiLineStrings.

---

## Source

U.S. Census Bureau, TIGER/Line Shapefiles 2025 — All Roads, Jackson County, Missouri.
Released: September 2025. Public domain.

## Links

(TIGER/Line Shapefiles)[https://www.census.gov/cgi-bin/geo/shapefiles/index.php] 
(Roads)[https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2025&layergroup=Roads]