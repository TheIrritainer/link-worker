# Shortlink Worker (Cloudflare + Python)

## Setup

1. Install dependencies:
```bash
make sync
```

2. Configure KV namespace IDs in `wrangler.jsonc`:
- Replace `<KV_NAMESPACE_ID>`
- Replace `<KV_PREVIEW_NAMESPACE_ID>`

3. Configure local env vars:
```bash
cp .dev.vars.example .dev.vars
```
- Set `DOMAIN_NAME` (for example: `go.example.com`)
- Set `STATIC_ACCESS_TOKEN` (any strong token)

4. Configure deployed env vars (Cloudflare):
```bash
UV_CACHE_DIR=/tmp/.uv-cache uv run pywrangler secret put DOMAIN_NAME
UV_CACHE_DIR=/tmp/.uv-cache uv run pywrangler secret put STATIC_ACCESS_TOKEN
```

5. Run locally:
```bash
make dev
```

6. Run tests:
```bash
make test
```

## Step-by-step: set up the link redirect

1. Pick the redirect host and set `DOMAIN_NAME` to that host (for example `go.example.com`) in both `.dev.vars` and Cloudflare secrets.

2. Deploy the worker:
```bash
make deploy
```

If deploying through Cloudflare's Git integration, set the build command to:
```bash
uv run build
```

3. In Cloudflare, route your host to this worker:
- Go to `Workers & Pages` > your worker > `Settings` > `Triggers`
- Add a route matching `DOMAIN_NAME/*` (example: `go.example.com/*`)
- Ensure DNS for that host exists and is proxied by Cloudflare

4. Create a shortlink via API:
```bash
curl -i -X POST "https://<DOMAIN_NAME>/api/link" \
  -H "Authorization: Bearer <STATIC_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"code":"gh","link":"https://github.com"}'
```

5. Verify redirect:
```bash
curl -i "https://<DOMAIN_NAME>/gh"
```
- Expected: `HTTP/1.1 302 Found`
- Expected `Location` header: `https://github.com`

## API

All `/api/*` routes require one of:
- `Authorization: Bearer <STATIC_ACCESS_TOKEN>`
- `X-Access-Token: <STATIC_ACCESS_TOKEN>`

Routes:
- `GET /api/link` list all shortlinks
- `GET /api/link/{code}` fetch one shortlink
- `POST /api/link` create a shortlink (`code` optional)
- `PUT /api/link/{code}` update destination link
- `DELETE /api/link/{code}` delete a shortlink

Request models:
- `code`: lowercase alphanumeric, max 12 chars
- `link`: max 1024 chars

`POST /api/link`:
- if `code` is omitted, a random code is generated
- returns `Location: https://<DOMAIN_NAME>/<code>`

## Redirect behavior

Any non-`/api/*` route is treated as a short code and resolved from Cloudflare KV:
- found: HTTP 302 redirect to stored `link`
- not found: HTTP 404
