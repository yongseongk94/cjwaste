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

function extractPath(route) {
  const result = [];

  for (const section of route?.sections || []) {
    for (const road of section?.roads || []) {
      const vertexes = road?.vertexes || [];

      for (let i = 0; i + 1 < vertexes.length; i += 2) {
        const x = Number(vertexes[i]);
        const y = Number(vertexes[i + 1]);

        if (Number.isFinite(x) && Number.isFinite(y)) {
          result.push([x, y]);
        }
      }
    }
  }

  return result;
}

async function requestRoute(points, apiKey) {
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

  const data = await response.json();

  if (!response.ok) {
    throw new Error(JSON.stringify(data));
  }

  const route = data?.routes?.[0];

  if (!route || route.result_code !== 0) {
    throw new Error(route?.result_msg || '경로를 찾지 못했습니다.');
  }

  return extractPath(route);
}

export async function onRequest(context) {
  const { request, env } = context;

  if (request.method !== 'POST') {
    return new Response(
      JSON.stringify({ error: 'POST 방식만 사용할 수 있습니다.' }),
      {
        status: 405,
        headers: { 'Content-Type': 'application/json' }
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
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }

  try {
    const body = await request.json();

    const points = Array.isArray(body.points)
      ? body.points.filter(validPoint)
      : [];

    if (points.length < 2) {
      return new Response(
        JSON.stringify({
          error: '최소 2개의 좌표가 필요합니다.'
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    const fullPath = [];

    // 너무 긴 노선은 나눠서 처리
    const MAX_POINTS = 32;

    for (
      let start = 0;
      start < points.length - 1;
      start += MAX_POINTS - 1
    ) {
      const chunk = points.slice(
        start,
        Math.min(start + MAX_POINTS, points.length)
      );

      if (chunk.length < 2) break;

      const path = await requestRoute(
        chunk,
        env.KAKAO_REST_API_KEY
      );

      fullPath.push(...path);
    }

    return new Response(
      JSON.stringify({ path: fullPath }),
      {
        status: 200,
        headers: {
          'Content-Type': 'application/json'
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
          'Content-Type': 'application/json'
        }
      }
    );
  }
}
