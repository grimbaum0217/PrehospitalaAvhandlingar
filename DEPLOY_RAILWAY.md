# Railway deployment

## Create the service

1. Push the repository to GitHub and create a Railway project from that repository.
2. Configure Railway to build the `Dockerfile` in the repository root.
3. Add a persistent volume and mount it at `/data`.
4. Generate a public Railway domain under the service's Networking settings.

## Required variables

Set these only in Railway Variables, never in GitHub or a frontend `VITE_` variable:

```text
APP_ENV=production
AUTH_ENABLED=true
DATABASE_PATH=/data/app.db
SITE_PASSWORD=<shared site password>
SESSION_SECRET=<long random value distinct from SITE_PASSWORD>
```

Generate the session secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`SITE_PASSWORD` and `SESSION_SECRET` must not use the same value. The Railway domain is public, but all content except `/login` and `/api/health` requires a valid login session.

No external API keys are currently required. If providers later need keys, add them as backend-only Railway variables. Never expose secrets through `VITE_...` variables.

Production intentionally refuses to start when authentication or either secret is missing.

## Verify

Open `https://<railway-domain>/api/health`. It should return:

```json
{"status":"ok"}
```

Opening `/` should redirect to `/login`. After login, verify the thesis list and an `/api/stats/overview` request.

## Database persistence and backup

On the first start, the bundled `backend/data/app.db` is copied to `/data/app.db`. Later deployments and restarts reuse the volume file and never overwrite it.

Before database-sensitive changes, create a Railway volume backup or copy `/data/app.db` from a one-off Railway shell to secure storage. Restore by stopping writes, replacing `/data/app.db` from the backup, and restarting the service. Never replace the volume database as part of a normal deployment.

## Local container

Build and run with a simulated volume:

```bash
docker build -t prehospitala-avhandlingar .
mkdir -p /tmp/prehospitala-data
docker run --rm -p 8000:8000 \
  -e APP_ENV=development \
  -e AUTH_ENABLED=false \
  -e DATABASE_PATH=/data/app.db \
  -v /tmp/prehospitala-data:/data \
  prehospitala-avhandlingar
```

To test authentication locally over HTTP, use `APP_ENV=test`, `AUTH_ENABLED=true`, and test-only values for `SITE_PASSWORD` and `SESSION_SECRET`. Cookies are `Secure` only when `APP_ENV=production`.

Login rate limiting is in-memory per application instance: five failed attempts from one IP within five minutes are rejected. It resets on service restart and is intended for this small deployment, not as distributed brute-force protection.
