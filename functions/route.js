const KAKAO_URL =
  'https://apis-navi.kakaomobility.com/v1/waypoints/directions';

function validPoint(p) {
  const x = Number(p?.x);
  const y = Number(p?.y);

  return (
    Number.isFinite(x) &&
    Number.isFinite(y) &&
    x >= 124 && x <= 132 &&
    y >= 33 && y <= 39
  );
}

function kakaoPoint(p) {
  const point = {
    x: Number(p.x),
    y: Number(p.y)
  };

  if (p.name) point.name = String(p.name).slice(0, 80);

  return point;
}

function dedupeConsecutive(points) {
  const out = [];
  for (const p of points || []) {
    if (!validPoint(p)) continue;
    const q = kakaoPoint(p);
    const prev = out[out.length - 1];
    if (prev && Math.abs(prev.x - q.x) < 1e-7 && Math.abs(prev.y - q.y) < 1e-7) {
      continue;
    }
    out.push(q);
  }
  return out;
}

function extractPath(route) {
  const result = [];

  for (const section of route?.sections || []) {
    for (const road of section?.roads || []) {
      const vertexes = road?.vertexes || [];

      for (let i = 0; i + 1 < vertexes.length; i += 2) {
        const x = Number(vertexes[i]);
        const y = Number(vertexes[i + 1]);

        if (Number.isFinite(x) && Number.isFinite(y)) {
          const prev = result[result.length - 1];
          if (!prev || Math.abs(prev[0] - x) > 1e-8 || Math.abs(prev[1] - y) > 1e-8) {
            result.push([x, y]);
          }
        }
      }
    }
  }

  return result;
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function requestRouteOnce(points, apiKey) {
  const response = await fetch(KAKAO_URL, {
    method: 'POST',
    headers: {
      Authorization: `KakaoAK ${apiKey}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      origin: kakaoPoint(points[0]),
      destination: kakaoPoint(points[points.length - 1]),
      waypoints: points.slice(1, -1).map(kakaoPoint),
      priority: 'RECOMMEND'
    })
  });

  const raw = await response.text();
  let data;
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = { raw: raw.slice(0, 300) };
  }

  if (!response.ok) {
    throw new Error(`Kakao ${response.status}: ${JSON.stringify(data).slice(0, 500)}`);
  }

  const route = data?.routes?.[0];

  if (!route || route.result_code !== 0) {
    throw new Error(route?.result_msg || '경로를 찾지 못했습니다.');
  }

  const path = extractPath(route);
  if (path.length < 2) throw new Error('도로망 좌표가 비어 있습니다.');
  return path;
}

async function requestRouteWithRetry(points, apiKey) {
  let lastError;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      return await requestRouteOnce(points, apiKey);
    } catch (error) {
      lastError = error;
      if (attempt < 2) await sleep(attempt === 0 ? 250 : 700);
    }
  }
  throw lastError;
}

function mergePaths(a, b) {
  if (!a?.length) return b || [];
  if (!b?.length) return a || [];
  const out = [...a];
  const last = out[out.length - 1];
  const first = b[0];
  const start = last && first && Math.abs(last[0] - first[0]) < 1e-8 && Math.abs(last[1] - first[1]) < 1e-8 ? 1 : 0;
  out.push(...b.slice(start));
  return out;
}

async function requestRouteResilient(points, apiKey, depth = 0) {
  try {
    return await requestRouteWithRetry(points, apiKey);
  } catch (error) {
    if (points.length <= 2 || depth >= 6) throw error;

    // 다중 경유지 중 한 지점 때문에 전체 요청이 실패하면 구간을 반으로 나눠
    // 실제 도로망 경로만 이어 붙입니다. 직선 보간은 하지 않습니다.
    const mid = Math.floor((points.length - 1) / 2);
    const leftPoints = points.slice(0, mid + 1);
    const rightPoints = points.slice(mid);
    const left = await requestRouteResilient(leftPoints, apiKey, depth + 1);
    const right = await requestRouteResilient(rightPoints, apiKey, depth + 1);
    return mergePaths(left, right);
  }
}

export async function onRequest(context) {
  const { request, env } = context;

  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
      }
    });
  }

  if (request.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'POST 방식만 사용할 수 있습니다.' }),
      {
        status: 405,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      }
    );
  }

  if (!env.KAKAO_REST_API_KEY) {
    return new Response(
      JSON.stringify({
        error: 'KAKAO_REST_API_KEY가 설정되지 않았습니다.'
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      }
    );
  }

  try {
    const body = await request.json();
    const points = dedupeConsecutive(Array.isArray(body.points) ? body.points : []);

    if (points.length < 2) {
      return new Response(
        JSON.stringify({
          error: '최소 2개의 좌표가 필요합니다.'
        }),
        {
          status: 400,
          headers: {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
          }
        }
      );
    }

    const fullPath = [];
    let chunkCount = 0;

    // 공개 다중 경유지 API는 최대 30개 경유지를 지원하지만,
    // 현장 노선은 지점 오차가 섞일 수 있어 18개 좌표 단위로 보수적으로 나눕니다.
    const MAX_POINTS = 18;

    for (let start = 0; start < points.length - 1; start += MAX_POINTS - 1) {
      const chunk = points.slice(start, Math.min(start + MAX_POINTS, points.length));
      if (chunk.length < 2) break;

      const path = await requestRouteResilient(chunk, env.KAKAO_REST_API_KEY);
      const merged = mergePaths(fullPath, path);
      fullPath.length = 0;
      fullPath.push(...merged);
      chunkCount++;
    }

    if (fullPath.length < 2) throw new Error('완성된 도로망 경로가 없습니다.');

    return new Response(
      JSON.stringify({ path: fullPath, chunks: chunkCount }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Cache-Control': 'no-store'
        }
      }
    );

  } catch (error) {
    return new Response(
      JSON.stringify({
        error: 'route_failed',
        detail: String(error?.message || error)
      }),
      {
        status: 502,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*'
        }
      }
    );
  }
}
