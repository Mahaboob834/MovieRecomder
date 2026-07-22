# Marquee — a movie recommender chatbot

A small Flask API (genre similarity via TF-IDF + optional Gemini "why you'll
like these" blurbs) with a themed HTML/CSS/JS frontend, wired together and
ready to deploy.

```
movie-recommender/
├── backend/
│   ├── app.py              Flask API + serves the frontend
│   ├── recommender.py      TF-IDF genre similarity engine
│   ├── movies.dat          your dataset (MovieLens format)
│   ├── requirements.txt
│   ├── Procfile             for Render/Heroku-style platforms
│   └── .env.example
└── frontend/
    ├── index.html
    ├── style.css
    └── script.js            calls the backend via fetch()
```



## Run it locally

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env         # then edit .env and paste your NEW key
export $(cat .env | grep -v '^#' | xargs)   # loads env vars into the shell

python app.py                # starts on http://localhost:5000
```

Open http://localhost:5000 — the Flask app serves the frontend directly, so
backend and frontend are already connected with nothing else to configure.


## How frontend and backend are connected

- `app.py` serves `frontend/index.html`, `style.css`, and `script.js` as
  static files, and exposes the API under `/api/...`.
- `frontend/script.js` calls `fetch('/api/chat', ...)`, `/api/search`, and
  `/api/greeting` using a relative path (`API_BASE = ''`), so it always talks
  to whatever host is serving it.
- If you ever want to host the frontend somewhere separate from the backend
  (e.g. frontend on Netlify, backend on Render), just set `API_BASE` in
  `script.js` to your backend's full URL, e.g.
  `const API_BASE = 'https://your-backend.onrender.com';` — CORS is already
  enabled server-side (`flask-cors`) to allow that.

## Deploying

### Option A — one service on Render (simplest)

1. Push this folder to a GitHub repo.
2. In Render: **New → Web Service**, connect the repo.
3. Set:
   - **Root directory**: `backend`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn app:app`
4. Add an environment variable `GEMINI_API_KEY` with your new key (Environment tab).
5. Deploy. Render gives you a URL like `https://marquee.onrender.com` serving
   both the API and the frontend.

Railway, Fly.io, and Heroku work the same way — they all recognize the
`Procfile` and `requirements.txt`.

### Option B — frontend and backend on separate hosts

1. Deploy `backend/` as above (Render/Railway/Fly/Heroku).
2. Deploy `frontend/` as a static site (Netlify, Vercel, GitHub Pages, S3 —
   any static host works since it's plain HTML/CSS/JS).
3. In `frontend/script.js`, set `API_BASE` to your backend's public URL.
4. Re-deploy the frontend.

## Notes on what changed from the original script

- **Removed the hardcoded API key** — now read from an environment variable.
- **Removed the NLTK downloads** (`punkt`, `stopwords`) — these were a common
  source of flaky first-run deploys. Replaced with a small built-in
  tokenizer/stopword list that does the same job for this use case.
- **Split into backend (API) + frontend (UI)** instead of a terminal
  `input()` loop, so it can be deployed and used from a browser.
- Free-text movie matching is a bit smarter now: it tries progressively
  shorter word-windows so "I loved Toy Story a lot" still resolves correctly,
  rather than only checking if the whole sentence is a substring of a title.
