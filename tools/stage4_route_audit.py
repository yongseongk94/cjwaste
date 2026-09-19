from pathlib import Path
import json
import subprocess

BASELINE = "a65108eacae4ce165c12bfd258493a3cf3ff2937"


def extract_object_after(text, marker):
    pos = text.find(marker)
    if pos < 0:
        raise SystemExit(f"{marker} not found")
    start = text.find("{", pos + len(marker))
    if start < 0:
        raise SystemExit(f"{marker} object start not found")

    depth = 0
    in_string = False
    quote = ""
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == quote:
                in_string = False
                quote = ""
            continue

        if ch in ('"', "'"):
            in_string = True
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    raise SystemExit(f"{marker} object is unterminated")


def parse_direct(text):
    return json.loads(extract_object_after(text, "const DIRECT_ROUTES="))


def parse_bundle(text):
    marker = '<script id="bundledPrecomputed" type="application/json">'
    start = text.find(marker)
    if start < 0:
        raise SystemExit("bundledPrecomputed script not found")
    start += len(marker)
    end = text.find("</script>", start)
    if end < 0:
        raise SystemExit("bundledPrecomputed closing script not found")
    return json.loads(text[start:end])


def direct_map(routes):
    out = {}
    for typ, rows in routes.items():
        for row in rows:
            vehicle = str(row["vehicle"])
            for day, value in row.get("days", {}).items():
                out[(str(typ), vehicle, str(day))] = json.dumps(
                    value, ensure_ascii=False, sort_keys=True
                )
    return out


def bundle_map(bundle):
    out = {}
    for row in bundle.get("routes", []):
        key = (str(row.get("type")), str(row.get("vehicle")), str(row.get("day")))
        out[key] = json.dumps(
            row.get("data"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    return out


def compare_maps(name, baseline, current):
    baseline_keys = set(baseline)
    current_keys = set(current)
    missing = sorted(baseline_keys - current_keys)
    extra = sorted(current_keys - baseline_keys)
    changed = sorted(
        key for key in baseline_keys & current_keys
        if baseline[key] != current[key]
    )

    print(
        name,
        "baseline", len(baseline),
        "current", len(current),
        "missing", len(missing),
        "extra", len(extra),
        "changed", len(changed),
    )
    if missing:
        print(name, "MISSING", missing)
    if extra:
        print(name, "EXTRA", extra)
    if changed:
        print(name, "CHANGED", changed)

    return missing, extra, changed


current_text = Path("index.html").read_text(encoding="utf-8")
try:
    baseline_text = subprocess.check_output(
        ["git", "show", f"{BASELINE}:index.html"],
        text=True,
        encoding="utf-8",
    )
except subprocess.CalledProcessError as exc:
    raise SystemExit(f"Could not read v76 baseline {BASELINE}: {exc}")

baseline_direct = direct_map(parse_direct(baseline_text))
current_direct = direct_map(parse_direct(current_text))
baseline_bundle = bundle_map(parse_bundle(baseline_text))
current_bundle = bundle_map(parse_bundle(current_text))

direct_diff = compare_maps("DIRECT_ROUTES", baseline_direct, current_direct)
bundle_diff = compare_maps("BUNDLED_ROUTES", baseline_bundle, current_bundle)

# v76 itself intentionally leaves some 읍·면 direct routes out of the embedded bundle.
# Those routes are built on first use and then persisted to IndexedDB. Stage 4 therefore
# fails only when CURRENT introduces a newly unbundled route beyond the v76 baseline.
baseline_not_precomputed = set(baseline_direct) - set(baseline_bundle)
current_not_precomputed = set(current_direct) - set(current_bundle)
newly_unbundled = sorted(current_not_precomputed - baseline_not_precomputed)
resolved_since_v76 = sorted(baseline_not_precomputed - current_not_precomputed)
print("V76_DYNAMIC_ROUTE_KEYS", len(baseline_not_precomputed), sorted(baseline_not_precomputed))
print("CURRENT_DYNAMIC_ROUTE_KEYS", len(current_not_precomputed), sorted(current_not_precomputed))
print("NEWLY_UNBUNDLED", len(newly_unbundled), newly_unbundled)
print("RESOLVED_SINCE_V76", len(resolved_since_v76), resolved_since_v76)

# Stage 3 requirement: 오창·내수·북이는 routeRuralScope -> allDongRouteSpecs path
# so the legacy v76 dynamic route keys are actually built/cached and can be displayed.
required_stage3_tokens = [
    "const RURAL_ROUTE_LAYER_DISTRICTS=new Set(['오창읍','내수읍','북이면']);",
    "const RURAL_ROUTE_MATCH_KM=0.020;",
    "const rural=routeRuralScope(type,route.vehicle,routeDay);",
    "if(rural.length)out.push({...common,districts:rural,scopeKind:'rural'});",
]
missing_stage3 = [token for token in required_stage3_tokens if token not in current_text]
print("STAGE3_RURAL_PATH_MISSING", len(missing_stage3), missing_stage3)

required_contractors = [
    "현대환경|95오0125|내덕1동|단독",
    "제일환경|95오0147|오창읍|단독",
    "제일환경|88저7478|오창읍|단독",
]
missing_contractors = [token for token in required_contractors if token not in current_text]
print("REQUIRED_CONTRACTORS_MISSING", len(missing_contractors), missing_contractors)

if any(any(group) for group in (direct_diff, bundle_diff)):
    raise SystemExit("Stage 4 failed: current route data differs from v76 baseline")
if newly_unbundled:
    raise SystemExit("Stage 4 failed: current has newly unbundled direct vehicle/day routes")
if missing_stage3:
    raise SystemExit("Stage 4 failed: Ochang/Naesu/Bugi dynamic route layer path is incomplete")
if missing_contractors:
    raise SystemExit("Stage 4 failed: required contractor route missing")

print("STAGE4_OK")
