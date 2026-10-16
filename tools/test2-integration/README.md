# TEST2 integrated improvements, 2026-10-16

TEST2 only; main page is unchanged.

- Port the main page's Cheongju-only address/business lookup, exact-name ranking, and known-name fallbacks for 청원구청 and 헤이븐헤어.
- Keep accurate TEST2 evidence wording behind a collapsed 자료·판정 기준 panel; restore apartment criteria in collection cards.
- Apply the existing user-confirmed 도원리 general-waste 6138 Monday rule to both address decisions and cached/static display zones.
- The cell containing the selected address and the corresponding route color use the same vehicle/day result as its card. This is display emphasis, not confirmation of every address in that cell.
- Resolve route priority once at build time: latest rural 20, latest Uam 15, then existing base records. Remove duplicate logical records and preserve Hyundai and weekday sharing.
- Pack 113 logical routes into 19 type/scope chunks, with shared geometries within each chunk. Total uncompressed route data is 4,812,814 bytes; general is 2,623,825 and recycle 2,188,989. Load only selected type/scope/vehicles, memoize concurrent requests, and never mark a partial load as globally complete.
- Keep rural cache v12; revise contractor keys to avoid stale Uam geometry. Main page is not modified.

Reproduce:
```
node tools/test2-integration/build.cjs
node tools/test2-integration/test.cjs
node tools/test2-contractors/test.cjs
node tools/test_test2_replacement_guard.cjs
```
Tests are offline: fetch mocks read only repository files. They verify chunk selection/reuse, unique records, unchanged rural geometry, all newest Uam segments, corrected-route coordinate bounds, Cheongju candidate filtering, Dowon card/focus agreement, apartment notice, shared weekday rendering and rapid layer switching. No route coordinates are sent to external map/routing services. Deployment verification reads public static files without executing map JavaScript.
