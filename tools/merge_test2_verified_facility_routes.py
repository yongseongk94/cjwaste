"""Reuse verified service geometry, never the separate inter-village travel geometry."""
import copy
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'cjwaste-test2/data/precomputed-rural-routes-no-motorway-v1.json'
SOURCE = ROOT / 'cjwaste-test/data/precomputed-village-facility-routes-v1.json'
REPORT = ROOT / 'tools/test2-verified-facility-merge-report.json'

def key(r):
    return (r['type'], str(r['vehicle']), r['day'], r['scopeSignature'])

def segment_key(seg):
    coords = tuple((round(p['lat'], 9), round(p['lng'], 9)) for p in seg)
    return min(coords, coords[::-1])

def distance_m(p, segments):
    scale = math.cos(math.radians(p['lat']))
    best = float('inf')
    for seg in segments:
        for a, b in zip(seg, seg[1:]):
            x, y = (a['lng']-p['lng'])*111320*scale, (a['lat']-p['lat'])*111320
            dx, dy = (b['lng']-a['lng'])*111320*scale, (b['lat']-a['lat'])*111320
            t = max(0, min(1, -(x*dx+y*dy)/(dx*dx+dy*dy))) if dx*dx+dy*dy else 0
            best = min(best, math.hypot(x+t*dx, y+t*dy))
    return best

def main():
    baseline = json.loads(BUNDLE.read_text())
    source = json.loads(SOURCE.read_text())
    donors = {key(r): r for r in source['routes']}
    assert len(baseline['routes']) == 20 and len({key(r) for r in baseline['routes']}) == 20
    rows = []
    for route in baseline['routes']:
        donor = donors[key(route)]['data']
        old = copy.deepcopy(route['data'])
        assert donor.get('inferredMovementCount', 0) == 0
        assert not donor.get('finalAuditInvalidCount', 0)
        data = route['data']
        seen = {segment_key(s) for s in data['segments']}
        added = 0
        for seg in donor['segments']:
            assert len(seg) >= 2 and all(math.isfinite(p['lat']) and math.isfinite(p['lng']) for p in seg)
            sk = segment_key(seg)
            if sk not in seen:
                data['segments'].append(seg)
                seen.add(sk)
                added += 1
        # Keep original evidence, including the later v9 verified anchors.
        evidence_keys = {(p.get('term'), p['lat'], p['lng']) for p in data['zoneEvidencePoints']}
        for p in donor['zoneEvidencePoints']:
            pk = (p.get('term'), p['lat'], p['lng'])
            if pk not in evidence_keys:
                data['zoneEvidencePoints'].append(p)
                evidence_keys.add(pk)
        excluded = set(donor.get('missingTerms', [])) | set(donor.get('outsideTerms', [])) | set(donor.get('outOfCheongwonTerms', []))
        resolved = []
        for term in old['missingTerms']:
            points = [p for p in donor['zoneEvidencePoints'] if p.get('term') == term]
            if term not in excluded and points and all(distance_m(p, donor['segments']) <= 80 for p in points):
                resolved.append(term)
        data['missingTerms'] = [t for t in old['missingTerms'] if t not in resolved]
        data['facilityMergeVersion'] = 'test2-verified-facility-20261012'
        data['inferredMovementCount'] = 0
        # These are service-only segments. Do not promote travelSegments from connected-v2.
        data['distance'] = round(sum(distance_m(a, [[b, b]]) for s in data['segments'] for a, b in zip(s, s[1:])))
        data['pointsCount'] = sum(len(s) for s in data['segments'])
        route['audit'] = {'segments': len(data['segments']), 'evidence': len(data['zoneEvidencePoints']),
                          'missingTerms': data['missingTerms'], 'missingRoadTerms': data.get('missingRoadTerms', []),
                          'preservedBaselineSegments': len(old['segments']), 'addedServiceSegments': added}
        assert all(segment_key(s) in seen for s in old['segments'])
        rows.append({'type': route['type'], 'vehicle': route['vehicle'], 'day': route['day'],
                     'scope': route['scopeSignature'], 'beforeSegments': len(old['segments']),
                     'afterSegments': len(data['segments']), 'addedServiceSegments': added,
                     'resolvedTerms': resolved, 'remainingTerms': data['missingTerms']})
    report = {'source': str(SOURCE.relative_to(ROOT)), 'sourceSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'routeCount': len(rows), 'addedServiceSegments': sum(r['addedServiceSegments'] for r in rows),
              'resolvedTermOccurrences': sum(len(r['resolvedTerms']) for r in rows),
              'remainingTermOccurrences': sum(len(r['remainingTerms']) for r in rows),
              'baselinePreserved': True, 'travelSegmentsImported': False, 'routes': rows}
    BUNDLE.write_text(json.dumps(baseline, ensure_ascii=False, separators=(',', ':')))
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'routes'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
