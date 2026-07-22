"""
Flask backend for the movie recommender chatbot.

Endpoints:
  GET  /api/search?q=...        -> list of matching titles (for autocomplete)
  POST /api/chat  {"message"}   -> {reply, matched_title, recommendations}
  GET  /healthz                 -> simple health check

Also serves the static frontend from ../frontend so the whole thing can be
deployed as a single web service. The frontend can also be hosted separately
and just point API_BASE at this backend's URL (see frontend/script.js).
"""
import os
import random

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from recommender import MovieRecommender

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)  # allow a separately-hosted frontend to call this API

engine = MovieRecommender()

# --- Optional Gemini integration -------------------------------------------------
# The API key must come from an environment variable. Never hardcode it in
# source control. If it's not set, the app still works, just without the
# "why you'll like these" blurb.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_gemini_model = None
if GEMINI_API_KEY:
    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("models/gemini-1.5-flash")
    except Exception as exc:  # pragma: no cover - defensive, keeps app alive
        print(f"Gemini setup failed, continuing without it: {exc}")


def ask_gemini(prompt: str):
    if not _gemini_model:
        return None
    try:
        response = _gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:  # pragma: no cover
        print(f"Gemini call failed: {exc}")
        return None


GREETINGS = [
    "Hello! I'm your movie buddy.",
    "Hi there! Ready to discover some movies?",
    "Hey! Let's find you a movie to watch.",
]


# --- API routes -------------------------------------------------------------
@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/api/search")
def search():
    q = request.args.get("q", "")
    return jsonify(results=engine.search_titles(q))


@app.get("/api/greeting")
def greeting():
    return jsonify(message=random.choice(GREETINGS))


@app.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    user_input = (payload.get("message") or "").strip()

    if not user_input:
        return jsonify(reply="Try mentioning a movie name!", matched_title=None, recommendations=[])

    if user_input.lower() in {"exit", "bye", "quit"}:
        return jsonify(reply="Goodbye! Happy watching.", matched_title=None, recommendations=[], end=True)

    matched_title = engine.resolve_title(user_input)
    if not matched_title:
        return jsonify(
            reply="I'm not sure which movie you're talking about. Try mentioning a movie name!",
            matched_title=None,
            recommendations=[],
        )

    recommendations = engine.recommend(matched_title)
    if not recommendations:
        return jsonify(
            reply=f"I found '{matched_title}' but couldn't find similar recommendations for it.",
            matched_title=matched_title,
            recommendations=[],
        )

    blurb = ask_gemini(
        f"In 2-3 sentences, tell me why someone who liked '{matched_title}' "
        f"would enjoy these: {', '.join(recommendations)}."
    )

    reply = f"Because you mentioned '{matched_title}', you might also enjoy:"
    return jsonify(
        reply=reply,
        matched_title=matched_title,
        recommendations=recommendations,
        blurb=blurb,  # may be null if Gemini isn't configured
    )


# --- Serve frontend ----------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
