# Shortlink Worker (Cloudflare + Python)

Shortlink service backed by Cloudflare Workers KV, with a FastAPI app running on Python Workers.

## Local development

1. Install dependencies:
```bash
make sync
```

2. Create local env vars:
```bash
cp .dev.vars.example .dev.vars
```
- Set `DOMAIN_NAME` (for example `go.example.com`)
- Set `STATIC_ACCESS_TOKEN` (any strong token)

3. Generate `wrangler.jsonc` from the template:
```bash
export KV_NAMESPACE_ID=<your-kv-namespace-id>
export KV_PREVIEW_NAMESPACE_ID=<your-kv-preview-namespace-id>
./build.sh
```

`./build.sh` renders `wrangler.template.jsonc` into `wrangler.jsonc` and then runs `uv run build`.

4. Run locally:
```bash
make dev
```

5. Run tests:
```bash
make test
```

## Deploy to Cloudflare Workers

`wrangler.jsonc` is generated from `wrangler.template.jsonc`. Do not edit `wrangler.jsonc` manually.

### Cloudflare Workers build settings

If you deploy through Cloudflare's Git-based Workers build:

1. Set the build command to:
```bash
./build.sh
```

2. Add these build arguments:
- `KV_NAMESPACE_ID`
- `KV_PREVIEW_NAMESPACE_ID`

3. Set `STATIC_ACCESS_TOKEN` as a Worker secret.

4. Set `DOMAIN_NAME` on the Worker runtime as a variable or secret.

### CLI deploy

If you deploy from your local machine:

1. Export the KV IDs and generate `wrangler.jsonc`:
```bash
export KV_NAMESPACE_ID=<your-kv-namespace-id>
export KV_PREVIEW_NAMESPACE_ID=<your-kv-preview-namespace-id>
./build.sh
```

2. Configure runtime values on the Worker:
```bash
UV_CACHE_DIR=/tmp/.uv-cache uv run pywrangler secret put DOMAIN_NAME
UV_CACHE_DIR=/tmp/.uv-cache uv run pywrangler secret put STATIC_ACCESS_TOKEN
```

3. Deploy:
```bash
make deploy
```

## Route setup

1. Pick the redirect host and set `DOMAIN_NAME` to that host.

2. In Cloudflare, route that host to this Worker:
- Go to `Workers & Pages` > your Worker > `Settings` > `Triggers`
- Add a route matching `DOMAIN_NAME/*` (example `go.example.com/*`)
- Ensure DNS for that host exists and is proxied by Cloudflare

## Create and verify a shortlink

Create a shortlink:
```bash
curl -i -X POST "https://<DOMAIN_NAME>/api/link" \
  -H "Authorization: Bearer <STATIC_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"code":"gh","link":"https://github.com"}'
```

Verify the redirect:
```bash
curl -i "https://<DOMAIN_NAME>/gh"
```

Expected result:
- `HTTP/1.1 302 Found`
- `Location: https://github.com`

## API

All `/api/*` routes require one of:
- `Authorization: Bearer <STATIC_ACCESS_TOKEN>`
- `X-Access-Token: <STATIC_ACCESS_TOKEN>`

Routes:
- `GET /api/link` list all shortlinks
- `GET /api/link/{code}` fetch one shortlink
- `POST /api/link` create a shortlink (`code` optional)
- `PUT /api/link/{code}` update the destination link
- `DELETE /api/link/{code}` delete a shortlink

Validation rules:
- `code`: lowercase letters and digits only, 1 to 12 characters
- `link`: absolute `http` or `https` URL, max 1024 characters

`POST /api/link`:
- if `code` is omitted, a random lowercase alphanumeric code is generated
- returns `Location: https://<DOMAIN_NAME>/<code>`

## Redirect behavior

Any non-`/api/*` route is treated as a short code and resolved from Cloudflare KV:
- found: HTTP `302` redirect to the stored `link`
- not found or invalid target: HTTP `404`
