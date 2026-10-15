# TEST2 connected routes (2026-10-15)

Only `cjwaste-test2` is updated. Twenty vehicle/weekday routes keep service lines separate from estimated service areas and inferred transit connections. Transit never certifies a collection address. The seven previously unresolved occurrences are explicit estimates:

| Area | Vehicle/day | Estimate |
|---|---|---|
| 도암리 | 3344 Wed | 도암길 settlement roads, 380 m search radius |
| 장재문화마을 | 6138 Fri | 장재마을회관/장재토성길, 350 m |
| 초정구길 | 6138/6544 Thu | 초정길 and settlement roads, 500 m |
| 3산업단지 | 3344/0262 Fri | 오창제3산업단지 public access roads, 650 m |
| 증평IC | 0262 Tue | 여천3길 outside IC, 400 m; no highway ramps |

Connections are an undirected road-network display, **not turn-by-turn navigation**. Published service geometry is retained except road edges overlapping identified expressways. OSM motorway/motorway_link, expressway=yes, motorroad=yes, trunk foot=no and restricted motor access are excluded. A 60 m administrative boundary-road tolerance applies only to transit; service remains in assigned districts. Short alignment seams are at most 35 m.

Build inputs: pinned repository commit `a2b405a1f576875af6cfb265546e8f52098d8527`, saved district/context data, and `road-source.json.gz`. Public OSM snapshot was downloaded from `https://overpass.kumi.systems/api/interpreter` on 2026-10-15 with the generic regional query `[out:json][timeout:45];way[highway](36.66,127.29,36.86,127.68);out geom;`. © OpenStreetMap contributors, ODbL 1.0: https://www.openstreetmap.org/copyright. Existing published Kakao geometry is read locally from the pinned commit. No route coordinates are submitted to external routing services.

From repository root, with Python numpy/scipy/networkx/shapely installed:

```sh
python tools/test2-connected/build.py
cp tools/test2-connected/connected-bundle.json cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json
python tools/test2-connected/validate.py
node tools/test_test2_replacement_guard.cjs
TEST2_LOCAL=1 TEST2_AUDIT_OUT=tools/test2-connected/local-audit.json python tools/test2_rural_route_full_audit.py
```

Browser audit requires Playwright Chromium. It checks all twenty selections, coordinate scope, seven explicit estimates, transit/address separation and IndexedDB restoration. `allRiCovered` intentionally measures verified coverage only (162/163); 도암리 remains an estimate, not a newly verified village. `geometry-audit.json` independently checks that rendered service/estimated/transit geometries form one connected component per route with 0.5 m rounding tolerance.
