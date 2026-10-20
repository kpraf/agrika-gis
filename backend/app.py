"""
AgriKA-GIS Flask API — application factory + entry point.

Run (from the backend/ folder, with the virtualenv active):
    flask --app app run --debug
or:
    python app.py
"""
import os

from flask import Flask, jsonify, render_template_string

from config import Config
from extensions import db, jwt, cors

# Simple status landing page served at the API root. It live-checks /api/health
# and, once the API responds, enables the link through to the web app.
LANDING_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AgriKA-GIS API</title>
  <meta name="robots" content="noindex" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet" />
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; display: flex; flex-direction: column;
      font-family: "Plus Jakarta Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
      background: #0B2005; color: #191C1A;
    }
    main { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 28px; padding: 40px 20px; }
    .logo { height: 72px; width: auto; }
    .card { width: 100%; max-width: 400px; background: #fff; border-radius: 16px; overflow: hidden;
      box-shadow: 0 24px 48px rgba(0,0,0,.35); }
    .top { display: flex; flex-direction: column; gap: 18px; padding: 28px 28px 24px; }
    .eyebrow { margin: 0; font-size: 12px; font-weight: 600; letter-spacing: .7px; text-transform: uppercase; color: #6B7280; }
    .state { display: flex; align-items: flex-start; gap: 12px; }
    .dot { width: 10px; height: 10px; margin-top: 8px; border-radius: 50%; flex: none; background: #9CA3AF; }
    .title { margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -.3px; color: #1F2937; }
    .sub { margin: 4px 0 0; font-size: 14px; line-height: 21px; color: #4B5563; text-wrap: pretty; }
    .bar { position: relative; height: 3px; border-radius: 2px; background: #ECEFEA; overflow: hidden; }
    .bar::after { content: ""; position: absolute; inset: 0; width: 40%; border-radius: 2px; background: #3B9E1C;
      animation: slide 1.4s ease-in-out infinite; }
    .bottom { display: flex; flex-direction: column; gap: 10px; padding: 20px 28px 24px; border-top: 1px solid #F3F4F6; }
    .btn { display: flex; align-items: center; justify-content: center; gap: 8px; height: 46px; border-radius: 10px;
      background: #1F6306; color: #fff; font-size: 15px; font-weight: 600; text-decoration: none; transition: background .15s; }
    .btn:hover { background: #0B2005; }
    .btn[aria-disabled="true"] { background: #ECEFEA; color: #9CA3AF; pointer-events: none; }
    .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 28px; }
    .meta { font-size: 12px; color: #9CA3AF; }
    .again { padding: 5px 10px; border: 0; border-radius: 6px; background: none; font: inherit; font-size: 12px;
      font-weight: 600; color: #1F6306; cursor: pointer; }
    .again:hover { background: #F0FDF4; }
    footer { display: flex; justify-content: center; flex-wrap: wrap; gap: 16px; padding: 0 20px 28px; font-size: 12px; color: #8FA58A; }
    footer a { font-family: "JetBrains Mono", monospace; color: #C7E9C0; text-decoration: none; }
    footer a:hover { text-decoration: underline; }

    [data-state="checking"] .dot, [data-state="waking"] .dot { animation: blink 1.1s ease-in-out infinite; }
    [data-state="waking"] .dot { background: #D99A0E; }
    [data-state="ok"] .dot { background: #3B9E1C; animation: ring 1.6s ease-out infinite; }
    [data-state="down"] .dot { background: #B42318; }
    [data-state="ok"] .bar, [data-state="down"] .bar { display: none; }

    @keyframes ring { 0% { box-shadow: 0 0 0 0 rgba(59,158,28,.5); } 100% { box-shadow: 0 0 0 8px rgba(59,158,28,0); } }
    @keyframes slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(250%); } }
    @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
    @media (prefers-reduced-motion: reduce) { *, *::after { animation: none !important; } }
  </style>
</head>
<body>
  <main>
    <img class="logo" src="/static/agrika-gis-logo.png" alt="AgriKA-GIS" />
    <div class="card" id="card" data-state="checking">
      <div class="top">
        <p class="eyebrow">Backend API</p>
        <div class="state" role="status" aria-live="polite">
          <span class="dot"></span>
          <div>
            <p class="title" id="title">Checking…</p>
            <p class="sub" id="sub">Contacting the API.</p>
          </div>
        </div>
        <div class="bar"></div>
      </div>
      <div class="bottom">
        <a class="btn" id="open" href="{{ frontend }}" aria-disabled="true">
          Open AgriKA-GIS
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
        </a>
        <div class="row">
          <span class="meta" id="meta"></span>
          <button class="again" id="again" type="button">Check again</button>
        </div>
      </div>
    </div>
  </main>
  <footer>
    <span>Health check <a href="/api/health">/api/health</a></span>
    <span>Laguna Province rice yield monitoring</span>
  </footer>
  <script>
    const $ = (id) => document.getElementById(id);
    const COPY = {
      checking: ["Checking…", "Contacting the API."],
      waking: ["Waking up the server", "It sleeps when no one has used it for a while. This usually takes under a minute."],
      ok: ["Running", "The API is up and ready."],
      down: ["Not responding", "The API didn't answer. It may be restarting or under maintenance."],
    };
    let timer = null, countdown = null, attempts = 0;

    function set(state, meta) {
      $("card").dataset.state = state;
      $("title").textContent = COPY[state][0];
      $("sub").textContent = COPY[state][1];
      $("meta").textContent = meta || "";
      $("open").setAttribute("aria-disabled", state === "ok" ? "false" : "true");
    }

    function retryIn(seconds, state) {
      clearInterval(countdown);
      let left = seconds;
      const tick = () => set(state, "Trying again in " + left + " s");
      tick();
      countdown = setInterval(() => { left -= 1; if (left <= 0) { clearInterval(countdown); check(); } else tick(); }, 1000);
    }

    async function check() {
      clearInterval(countdown);
      clearTimeout(timer);
      attempts += 1;
      if (attempts === 1) set("checking");
      // After 3 s with no answer, assume a cold start rather than an outage.
      timer = setTimeout(() => set("waking", "Still trying…"), 3000);
      const started = performance.now();
      try {
        const ctrl = new AbortController();
        const abort = setTimeout(() => ctrl.abort(), 70000);
        const r = await fetch("/api/health", { cache: "no-store", signal: ctrl.signal });
        clearTimeout(abort);
        const d = await r.json();
        clearTimeout(timer);
        if (!r.ok || d.status !== "ok") throw new Error("bad status");
        const ms = Math.round(performance.now() - started);
        const at = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
        attempts = 0;
        set("ok", "Responded in " + ms + " ms · " + at);
      } catch (e) {
        clearTimeout(timer);
        // The first few failures are usually the server booting; keep calling it "waking".
        if (attempts < 4) retryIn(5, "waking");
        else retryIn(15, "down");
      }
    }

    $("again").addEventListener("click", () => { attempts = 0; check(); });
    check();
  </script>
</body>
</html>"""


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Init extensions
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    # Import models so SQLAlchemy is aware of them (tables already exist via schema.sql)
    from models import (  # noqa: F401
        Role, Municipality, User, Barangay, Season, Prediction, YieldRecord,
        MunicipalityYieldRecord, MunicipalityPrediction, Residual,
    )

    # Blueprints
    from auth import auth_bp
    from boundaries import boundaries_bp
    from users import users_bp
    from yields import yields_bp
    from features import features_bp
    from contact import contact_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(boundaries_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(yields_bp)
    app.register_blueprint(features_bp)
    app.register_blueprint(contact_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "agrika-gis-api"})

    # Where the "Open AgriKA-GIS" button points. Defaults to the first configured
    # CORS origin (the deployed frontend), overridable via FRONTEND_URL.
    origins = app.config.get("CORS_ORIGINS") or []
    frontend_url = os.environ.get("FRONTEND_URL") or (origins[0] if origins else "https://agrika-gis-web.onrender.com")

    @app.get("/")
    def index():
        return render_template_string(LANDING_HTML, frontend=frontend_url)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
