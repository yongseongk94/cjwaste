# TEST2 contractor weekday sharing and Hyundai correction

Scope: TEST2 only. User confirmed identical contractor routes within Mon/Wed/Fri and Tue/Thu. Source text remains intact in `CONTRACT_SOURCE_DATA`; `normalizeContractWeekdayGroups` unions the listed stops within each group for non-apartment routes. Saturday stays governed by its own source text. No missing weekday is invented. Existing Ochang industrial-boundary restrictions remain.

The old TEST2 bundle had Hyundai Tue/Thu service lengths of 1,619 / 3,108 m and did not load the corrected Hyundai bundle from `cjwaste-test`. The correction unions its verified seven landmarks, local service geometry, estimated neighborhood roads and connecting travel. The seven landmarks are 새동네경로당, 로얄볼링장, 충청북도학생수영장, 세원아파트, 청주내덕동우체국, 덕암성당, 내덕1동 행정복지센터. The apartment is a source landmark for nearby houses/stores, not an apartment collection contract.

Estimated neighborhoods and transit remain separate from `segments` and do not certify collection addresses. The geometry is a route display, not turn-by-turn navigation. No coordinates are sent to a routing service. Existing OSM attribution is retained.

Optimization:
- Compact bundle uses `geometryPool` + `dataRef`, including cross-type storage reuse.
- 54 weekday records become 28 serialized weekday groups and 20 stored geometry objects; runtime can also share Saturday when its source text is identical.
- Base bundle: 3,617,020 → 2,708,771 bytes (25.1% smaller), despite the added Hyundai neighborhood roads.
- Cache keys use a contractor-only revision; rural direct route caches stay on v12.
- Cache hydration/read/write and geometry audits are grouped; weekday aliases share polyline objects.
- Visibility uses a difference between desired/current objects. Switching identical days does not detach and reattach the same lines.

Reproduce from repository root:

```sh
python tools/test2-contractors/build.py
python tools/test2-contractors/validate.py
node tools/test_test2_replacement_guard.cjs
node tools/test2-contractors/test.cjs
TEST2_LOCAL=1 python tools/test2-contractors/audit.py
TEST2_LOCAL=1 TEST2_AUDIT_OUT=tools/test2-contractors/rural-regression.json python tools/test2_rural_route_full_audit.py
```

Build inputs: the existing v76 baseline and `cjwaste-test/data/precomputed-hyundai-v2.json`; their existing source history is retained. Python Shapely and Playwright Chromium are required for validation. Browser audits explicitly block the external routing worker. Live verification runs `audit.py` without `TEST2_LOCAL` after deployment.

2026-10-16 validation: contractor browser audit passed 54 slots, 21 runtime groups, cached restoration and zero shared-day map detach/attach calls. Additional rural/live map verification was blocked by automatic approval review over possible coordinate disclosure to the external map provider; do not rerun that check without authorization. Offline tests verify unchanged direct-route records, rapid layer switching and route toggling. Deployment can be verified by public file hashes without sending coordinates.
