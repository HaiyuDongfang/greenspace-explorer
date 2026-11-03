# Auckland park road network access audit

## Scope and method

- Source: `data\01raw\road_network_in_parks_auckland_overlay.gpkg`
- Source SHA-256: `a59c5194db940c5b5e2d6d094b56b9315c5f831b6ce1195a1ca99814d8091fa0`
- GeoPackage layer: `road_network_in_parks_auckland_overlay`
- CRS: `EPSG:2193`; geometry type: `MultiLineString`
- Features: 29,250; attributes: 52
- Geometry length: **2,517.640 km** summed from line geometry in EPSG:2193 (metres converted to kilometres).
- The source `length` attribute sums to 3,714,241.000 numeric units; its units and semantics were not documented, so it is excluded from all length totals. If those units are metres, its sum would be 3,714.241 km. Compared numerically with geometry length in metres, per-feature absolute differences have a 0.433 median and 14,599.864 maximum. Confirm the field's provenance before using it.
- Totals describe the features as stored, without dissolving, de-duplicating or clipping again. Repeated OSM `id` values occur on 1,565 rows (758 distinct ids); identical geometries occur on 26 rows (13 repeated geometry groups). Treat totals as represented feature-length, not a deduplicated unique-road estimate.
- Geometry QA: 0 null, 0 empty, 0 invalid geometries.

## GeoPackage structure and fields

This file contains one layer, `road_network_in_parks_auckland_overlay`, with MultiLineString geometry. Fields, in source order:

`access, area, bicycle, bicycle_road, bridge, busway, cycleway, est_width, foot, footway, highway, junction, lanes, lit, maxspeed, motorcar, motor_vehicle, name, oneway, oneway:bicycle, overtaking, path, passing_places, psv, ref, service, segregated, sidewalk, smoothness, surface, tracktype, tunnel, turn, width, visible, id, timestamp, version, tags, osm_type, length, AssetGroup, SAPID, VALIDATIONSTATE, GlobalID, DESCRIPTION, SITE, SITEDESCRIPTION, LOCALBOARD, STREETNAME, STREETNUMBER, CITY`

## Tag values, feature counts and lengths

Missing counts are shown as `(missing)`. Length is measured from geometry, not the source `length` attribute.

### `access`

| Value | Features | Geometry length (km) |
| --- | --- | --- |
| (missing) | 27465 | 2206.663 |
| no | 585 | 201.911 |
| private | 642 | 53.160 |
| yes | 277 | 27.106 |
| permissive | 81 | 14.231 |
| destination | 160 | 10.260 |
| customers | 28 | 2.190 |
| forestry | 4 | 1.047 |
| tidal | 3 | 0.671 |
| permit | 2 | 0.211 |
| emergency | 1 | 0.107 |
| foot | 2 | 0.083 |
### `foot`

| Value | Features | Geometry length (km) |
| --- | --- | --- |
| (missing) | 23689 | 1793.352 |
| yes | 2969 | 356.589 |
| designated | 2262 | 246.906 |
| no | 184 | 96.879 |
| permissive | 75 | 18.231 |
| use_sidepath | 43 | 2.576 |
| private | 11 | 1.806 |
| customers | 17 | 1.301 |
### `highway`

| Value | Features | Geometry length (km) |
| --- | --- | --- |
| footway | 14210 | 821.488 |
| path | 4618 | 751.708 |
| service | 4391 | 339.597 |
| cycleway | 2253 | 241.393 |
| track | 727 | 173.839 |
| unclassified | 285 | 56.632 |
| steps | 2018 | 28.363 |
| residential | 348 | 25.924 |
| tertiary | 73 | 20.845 |
| bridleway | 33 | 19.102 |
| secondary | 41 | 14.598 |
| pedestrian | 75 | 13.059 |
| living_street | 85 | 5.112 |
| motorway | 35 | 3.688 |
| motorway_link | 15 | 0.849 |
| corridor | 16 | 0.390 |
| primary | 11 | 0.306 |
| via_ferrata | 4 | 0.304 |
| busway | 5 | 0.278 |
| primary_link | 3 | 0.084 |
| secondary_link | 3 | 0.056 |
| trunk_link | 1 | 0.022 |
### `service`

| Value | Features | Geometry length (km) |
| --- | --- | --- |
| (missing) | 27147 | 2408.528 |
| parking_aisle | 1352 | 81.319 |
| driveway | 535 | 22.728 |
| slipway | 195 | 4.482 |
| emergency_access | 16 | 0.358 |
| alley | 3 | 0.151 |
| drive-through | 1 | 0.048 |
| shared_driveway | 1 | 0.027 |
### `bicycle`

| Value | Features | Geometry length (km) |
| --- | --- | --- |
| (missing) | 24481 | 1861.491 |
| no | 1582 | 245.493 |
| designated | 2066 | 230.042 |
| yes | 926 | 156.240 |
| permissive | 132 | 16.874 |
| private | 5 | 3.762 |
| dismount | 53 | 3.232 |
| discouraged | 4 | 0.498 |
| use_sidepath | 1 | 0.006 |
### `motor_vehicle`

| Value | Features | Geometry length (km) |
| --- | --- | --- |
| (missing) | 28710 | 2410.020 |
| no | 360 | 60.373 |
| private | 141 | 41.382 |
| customers | 7 | 2.440 |
| yes | 5 | 1.188 |
| destination | 14 | 1.076 |
| permit | 6 | 0.573 |
| designated | 5 | 0.513 |
| permissive | 2 | 0.076 |

## Geometry length by `highway` and general `access`

| Highway | Features | Geometry length (km) |
| --- | --- | --- |
| footway | 14210 | 821.488 |
| path | 4618 | 751.708 |
| service | 4391 | 339.597 |
| cycleway | 2253 | 241.393 |
| track | 727 | 173.839 |
| unclassified | 285 | 56.632 |
| steps | 2018 | 28.363 |
| residential | 348 | 25.924 |
| tertiary | 73 | 20.845 |
| bridleway | 33 | 19.102 |
| secondary | 41 | 14.598 |
| pedestrian | 75 | 13.059 |
| living_street | 85 | 5.112 |
| motorway | 35 | 3.688 |
| motorway_link | 15 | 0.849 |
| corridor | 16 | 0.390 |
| primary | 11 | 0.306 |
| via_ferrata | 4 | 0.304 |
| busway | 5 | 0.278 |
| primary_link | 3 | 0.084 |
| secondary_link | 3 | 0.056 |
| trunk_link | 1 | 0.022 |

| General access | Features | Geometry length (km) |
| --- | --- | --- |
| (missing) | 27465 | 2206.663 |
| no | 585 | 201.911 |
| private | 642 | 53.160 |
| yes | 277 | 27.106 |
| permissive | 81 | 14.231 |
| destination | 160 | 10.260 |
| customers | 28 | 2.190 |
| forestry | 4 | 1.047 |
| tidal | 3 | 0.671 |
| permit | 2 | 0.211 |
| emergency | 1 | 0.107 |
| foot | 2 | 0.083 |

## Proposed pedestrian-access classification

Resolve `foot` first whenever it is present; do not let a general `access` value override it. Only fall back to `access` when `foot` is missing.

| Class | `foot` value (takes precedence) | Fallback `access` value |
|---|---|---|
| Public | `yes`, `designated` | `yes`, `foot` |
| Conditional | `permissive`, `customers` | `permissive`, `destination`, `customers`, `permit`, `forestry`, `tidal`, `emergency` |
| Restricted | `no`, `private`, `use_sidepath` | `no`, `private` |
| Unspecified | missing, unknown or unrecognized value | missing, unknown or unrecognized value |

`use_sidepath` is treated as restricted on the mapped segment because it directs pedestrians to another way; flag it for review rather than assuming the alternative is present. `permissive` is conditional because permission can be withdrawn. Unrecognized non-empty values remain Unspecified and should be reviewed; they are not treated as public.

| Pedestrian access | Features | Geometry length (km) |
| --- | --- | --- |
| Unspecified | 22291 | 1602.109 |
| Public | 5317 | 608.279 |
| Restricted | 1317 | 269.780 |
| Conditional | 325 | 37.473 |

### Walkability rules

Walkability is a separate, conservative assessment of the highway form and pedestrian restrictions; it is not proof of legal public access.

1. Restricted pedestrian access (`foot=no/private/use_sidepath`, or fallback `access=no/private`) overrides highway type. In particular, `foot=no` is an explicit restriction even on a footway/path.
2. `footway`, `path`, `steps`, `pedestrian`, `track`, and `bridleway` are pedestrian-oriented highway forms. With Public access they are classified as walkable; with Conditional access as conditional; with Unspecified access as potential only, with legal access unverified.
3. `service`, `residential`, `living_street`, `unclassified`, `primary`, `secondary`, and `tertiary` are road-like/shared forms. They are classed walkable only where pedestrian access is Public; conditional access stays conditional, and unspecified access stays potential/unverified.
4. `cycleway` alone does not establish pedestrian permission. It is walkable only with explicit Public pedestrian access, conditional where access is Conditional, and otherwise uncertain.
5. `motorway`, `motorway_link`, `trunk`, and `trunk_link` are not presumed suitable for pedestrians. A positive pedestrian-specific tag on them is a conflict/review case, not an automatic walkability grant.
6. `corridor`, `via_ferrata`, `busway`, `primary_link`, `secondary_link`, and unrecognized highway values are uncertain/specialist and need review; do not infer suitability from missing tags.

| Walkability category | Features | Geometry length (km) |
| --- | --- | --- |
| Potential: pedestrian-oriented type, access unspecified | 17590 | 1205.968 |
| Potential: road-like type, access unspecified | 4495 | 385.204 |
| Walkable: pedestrian-oriented highway | 3134 | 354.914 |
| Restricted by pedestrian-access tag | 1317 | 269.780 |
| Walkable: pedestrian access explicit | 2008 | 219.828 |
| Conditional or purpose-limited | 322 | 37.291 |
| Walkable: shared-road highway | 175 | 33.536 |
| Uncertain: cycleway access unspecified | 193 | 10.636 |
| Uncertain: specialist or link highway | 16 | 0.482 |

## Foot/access/highway combinations

Top 25 combinations by feature count (all combinations are in `foot_access_highway_combinations.csv`).

| foot | access | highway | Features | Geometry length (km) |
| --- | --- | --- | --- | --- |
| (missing) | (missing) | footway | 12765 | 712.510 |
| (missing) | (missing) | service | 3754 | 278.907 |
| (missing) | (missing) | path | 2861 | 374.906 |
| designated | (missing) | cycleway | 1907 | 208.692 |
| (missing) | (missing) | steps | 1491 | 18.462 |
| yes | (missing) | path | 1062 | 158.617 |
| yes | (missing) | footway | 943 | 81.831 |
| (missing) | (missing) | track | 411 | 90.831 |
| yes | (missing) | steps | 409 | 7.055 |
| (missing) | (missing) | residential | 312 | 23.250 |
| (missing) | private | service | 282 | 13.261 |
| (missing) | no | path | 251 | 106.638 |
| (missing) | (missing) | unclassified | 251 | 45.923 |
| (missing) | (missing) | cycleway | 193 | 10.636 |
| designated | (missing) | path | 177 | 15.648 |
| (missing) | private | footway | 136 | 3.981 |
| (missing) | private | track | 127 | 25.057 |
| (missing) | destination | service | 127 | 9.016 |
| designated | (missing) | footway | 117 | 8.227 |
| yes | (missing) | track | 103 | 37.804 |
| yes | (missing) | cycleway | 87 | 8.221 |
| (missing) | no | footway | 84 | 3.790 |
| (missing) | (missing) | living_street | 76 | 4.966 |
| yes | (missing) | service | 75 | 19.478 |
| yes | yes | footway | 71 | 5.773 |

### `highway` and `service` combinations

| Highway | Service | Features | Geometry length (km) |
| --- | --- | --- | --- |
| footway | (missing) | 14209 | 821.486 |
| path | (missing) | 4606 | 751.594 |
| service | (missing) | 2310 | 230.837 |
| cycleway | (missing) | 2253 | 241.393 |
| steps | (missing) | 2018 | 28.363 |
| service | parking_aisle | 1351 | 81.316 |
| track | (missing) | 727 | 173.839 |
| service | driveway | 534 | 22.705 |
| residential | (missing) | 348 | 25.924 |
| unclassified | (missing) | 285 | 56.632 |
| service | slipway | 184 | 4.391 |
| living_street | (missing) | 85 | 5.112 |
| pedestrian | (missing) | 75 | 13.059 |
| tertiary | (missing) | 73 | 20.845 |
| secondary | (missing) | 41 | 14.598 |
| motorway | (missing) | 35 | 3.688 |
| bridleway | (missing) | 33 | 19.102 |
| motorway_link | (missing) | 15 | 0.849 |
| primary | (missing) | 11 | 0.306 |
| path | slipway | 11 | 0.091 |
| corridor | emergency_access | 9 | 0.236 |
| corridor | (missing) | 7 | 0.155 |
| service | emergency_access | 7 | 0.122 |
| busway | (missing) | 5 | 0.278 |
| via_ferrata | (missing) | 4 | 0.304 |

## Conflicts and ambiguous records

There are **87** records where both `foot` and `access` are populated and their independent mapped access classes disagree. Under the proposed rule, the `foot` classification wins, but these should be checked against source tagging before any production interpretation.

| foot | access | highway | Features | Geometry length (km) |
| --- | --- | --- | --- | --- |
| yes | no | path | 17 | 2.384 |
| yes | no | footway | 12 | 0.564 |
| yes | destination | service | 11 | 0.993 |
| customers | private | footway | 6 | 0.837 |
| customers | private | steps | 6 | 0.249 |
| yes | private | footway | 5 | 0.443 |
| yes | no | steps | 5 | 0.099 |
| customers | private | path | 4 | 0.169 |
| yes | private | service | 4 | 0.079 |
| yes | no | service | 3 | 0.067 |
| yes | permissive | path | 2 | 0.381 |
| designated | no | cycleway | 2 | 0.165 |
| yes | private | pedestrian | 2 | 0.146 |
| yes | permissive | footway | 2 | 0.038 |
| permissive | private | service | 1 | 1.400 |
| permissive | private | path | 1 | 0.035 |
| yes | permit | service | 1 | 0.017 |
| yes | permissive | service | 1 | 0.009 |
| designated | permissive | cycleway | 1 | 0.006 |
| permissive | no | unclassified | 1 | 0.000 |

Other important review cases:

- `foot=no` occurs on 184 features (96.879 km), including footways, paths, cycleways, steps and motorways; it must remain a restriction.
- `cycleway` with no pedestrian access classification is kept uncertain rather than assumed walkable.
- Motorway and specialist/link highway tags are rare and/or have unexpected tag combinations. Counts by access and walkability assessment:

| Highway | Pedestrian access | Walkability | Features | Geometry length (km) |
| --- | --- | --- | --- | --- |
| cycleway | Public | Walkable: pedestrian access explicit | 2008 | 219.828 |
| cycleway | Unspecified | Uncertain: cycleway access unspecified | 193 | 10.636 |
| cycleway | Restricted | Restricted by pedestrian-access tag | 52 | 10.929 |
| motorway | Restricted | Restricted by pedestrian-access tag | 35 | 3.688 |
| motorway_link | Restricted | Restricted by pedestrian-access tag | 15 | 0.849 |
| corridor | Restricted | Restricted by pedestrian-access tag | 10 | 0.267 |
| corridor | Unspecified | Uncertain: specialist or link highway | 6 | 0.123 |
| via_ferrata | Restricted | Restricted by pedestrian-access tag | 3 | 0.267 |
| busway | Conditional | Uncertain: specialist or link highway | 3 | 0.182 |
| primary_link | Unspecified | Uncertain: specialist or link highway | 3 | 0.084 |
| secondary_link | Unspecified | Uncertain: specialist or link highway | 3 | 0.056 |
| busway | Restricted | Restricted by pedestrian-access tag | 2 | 0.097 |
| via_ferrata | Unspecified | Uncertain: specialist or link highway | 1 | 0.037 |
| trunk_link | Restricted | Restricted by pedestrian-access tag | 1 | 0.022 |

- `foot=use_sidepath` is not evidence that the sidepath is included in this dataset or usable.
- `bicycle` and `motor_vehicle` tags describe other modes; they are not used to infer pedestrian permission. A segment marked `motor_vehicle=no` can still have Unspecified pedestrian access.
- The source includes repeated OSM ids and exact geometry duplicates. Assess whether those represent separate park overlays or duplicate records before treating summed lengths as unique network length.
- `review_examples.csv` includes up to five representative rows for each review flag; `audit_row_number` identifies source read order, while `id` is the OSM id and may repeat.

## Recommended map styling (proposal only)

- Use distinct, legible styles for Public, Conditional, Restricted and Unspecified access; avoid styling Unspecified as publicly available.
- Within accessible segments, differentiate pedestrian-oriented paths from road-like/shared segments.
- Render Restricted segments muted or dashed, conditional segments with a separate dash/pattern, and Unspecified/uncertain features with a subdued review style.
- Use a high-contrast warning style and/or exclude from default pedestrian routes for motor-highway classes and unresolved specialist types.
- Keep access state and walkability state as separate attributes so a visually pedestrian-friendly path is not mistaken for verified public access.

## Output files

- `tag_value_counts.csv`: all observed values, counts and geometry lengths for the six requested tags.
- `length_by_highway.csv` and `length_by_access_raw.csv`: category totals.
- `pedestrian_access_counts.csv` and `walkability_counts.csv`: proposed classification totals.
- `foot_access_highway_combinations.csv`: full three-tag combination table.
- `highway_service_combinations.csv`: `service` subtype by highway.
- `highway_review_summary.csv`: cycleway, motor-highway and specialist/link counts by access and walkability.
- `foot_access_conflicts.csv`: records where `foot` and general `access` resolve to different classes.
- `review_examples.csv`: representative edge cases.
- Run this audit with `python audits/road_network_access_audit/audit_road_network.py [path-to-gpkg]`.
