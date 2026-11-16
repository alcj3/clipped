# clipped

## Run locally

Start the API from the repository root:

```sh
python3 -m venv .venv
.venv/bin/pip install -r api/requirements.txt
.venv/bin/uvicorn api.main:app
```

In another terminal, start the web app:

```sh
cd web
npm ci
npm run dev
```

Open http://localhost:5173. The Vite server proxies `/api` requests to port 8000.
