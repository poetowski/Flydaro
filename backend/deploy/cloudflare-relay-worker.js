/**
 * Flydaro OpenSky relay -- a tiny Cloudflare Worker that proxies OpenSky
 * Network requests for a backend deployment whose own outbound network
 * path to OpenSky is blocked/throttled (seen on Render's free tier).
 *
 * Deploy this as-is on Cloudflare's free Workers tier, set a `RELAY_SECRET`
 * secret on the Worker, then point the backend's OPENSKY_RELAY_URL at this
 * Worker's *.workers.dev URL and OPENSKY_RELAY_SECRET at the same value.
 *
 * Security properties -- do not remove either of these, or this becomes an
 * open/abusable proxy to arbitrary hosts:
 *   1. Every request must carry a `X-Relay-Secret` header matching the
 *      `RELAY_SECRET` binding, or it's rejected with 401.
 *   2. The `?target=` URL's hostname must be exactly `opensky-network.org`
 *      or `auth.opensky-network.org` -- checked via URL.hostname (not a
 *      substring/prefix match), or it's rejected with 400.
 */

const ALLOWED_HOSTNAMES = new Set(["opensky-network.org", "auth.opensky-network.org"]);

export default {
  async fetch(request, env) {
    const providedSecret = request.headers.get("X-Relay-Secret");
    if (!env.RELAY_SECRET || providedSecret !== env.RELAY_SECRET) {
      return new Response("Unauthorized", { status: 401 });
    }

    const requestUrl = new URL(request.url);
    const target = requestUrl.searchParams.get("target");
    if (!target) {
      return new Response("Missing target", { status: 400 });
    }

    let targetUrl;
    try {
      targetUrl = new URL(target);
    } catch {
      return new Response("Invalid target", { status: 400 });
    }

    if (!ALLOWED_HOSTNAMES.has(targetUrl.hostname)) {
      return new Response("Target host not allowed", { status: 400 });
    }

    const forwardedHeaders = new Headers();
    const contentType = request.headers.get("Content-Type");
    const authorization = request.headers.get("Authorization");
    if (contentType) forwardedHeaders.set("Content-Type", contentType);
    if (authorization) forwardedHeaders.set("Authorization", authorization);

    const upstreamResponse = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: forwardedHeaders,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
    });

    const responseHeaders = new Headers();
    const upstreamContentType = upstreamResponse.headers.get("Content-Type");
    const rateLimitRemaining = upstreamResponse.headers.get("X-Rate-Limit-Remaining");
    if (upstreamContentType) responseHeaders.set("Content-Type", upstreamContentType);
    if (rateLimitRemaining) responseHeaders.set("X-Rate-Limit-Remaining", rateLimitRemaining);

    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      headers: responseHeaders,
    });
  },
};
