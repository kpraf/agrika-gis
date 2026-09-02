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
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; display: flex; flex-direction: column;
      font-family: "Plus Jakarta Sans", system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: #F8FAF5; color: #191C1A;
    }
    header { background: #0B2005; padding: 18px 24px; display: flex; justify-content: center; }
    header img { height: 56px; width: auto; object-fit: contain; }
    main { flex: 1; display: flex; align-items: center; justify-content: center; padding: 32px 24px; }
    .card {
      width: 100%; max-width: 440px; background: #fff; border: 1px solid #C3C8BD;
      border-radius: 16px; padding: 40px 32px; text-align: center;
      display: flex; flex-direction: column; align-items: center;
      box-shadow: 0 10px 15px -3px rgba(0,0,0,0.06), 0 4px 6px -4px rgba(0,0,0,0.06);
    }
    .eyebrow { margin: 0 0 20px; font-size: 12px; font-weight: 600; letter-spacing: 0.7px;
      text-transform: uppercase; color: #434840; }
    .status {
      display: inline-flex; align-items: center; gap: 10px; padding: 10px 18px; border-radius: 999px;
      font-size: 14px; font-weight: 600; border: 1px solid transparent;
    }
    .status .dot { width: 10px; height: 10px; border-radius: 50%; flex: none; }
    .status.checking { background: #FEF3C7; border-color: #FDE68A; color: #92400E; }
    .status.checking .dot { background: #F59E0B; animation: pulse 1.1s ease-in-out infinite; }
    .status.ok { background: #ECFDF3; border-color: #A7E1A1; color: #1B6D24; }
    .status.ok .dot { background: #3B9E1C; box-shadow: 0 0 0 0 rgba(59,158,28,0.5); animation: ring 1.6s ease-out infinite; }
    .status.bad { background: #FEE2E2; border-color: #FECACA; color: #991B1B; }
    .status.bad .dot { background: #EF4444; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.35; } }
    @keyframes ring { 0% { box-shadow: 0 0 0 0 rgba(59,158,28,0.5);} 100% { box-shadow: 0 0 0 10px rgba(59,158,28,0);} }
    .btn {
      display: inline-flex; align-items: center; gap: 8px; margin: 26px auto 0; padding: 13px 26px;
      border-radius: 999px; background: #286A11; color: #fff; font-weight: 600; font-size: 15px;
      text-decoration: none; transition: transform 0.08s ease, background 0.15s ease, opacity 0.2s ease;
    }
    .btn:hover { background: #1F6306; transform: translateY(-1px); }
    .btn.disabled { opacity: 0.45; pointer-events: none; }
    .hint { margin-top: 14px; font-size: 12px; color: #6B7280; min-height: 16px; }
    footer { padding: 18px 24px 28px; text-align: center; font-size: 12px; color: #9CA3AF; }
    footer a { color: #6B7280; }
  </style>
</head>
<body>
  <header>
    <img src="/static/agrika-gis-logo.png" alt="AgriKA-GIS" />
  </header>
  <main>
    <div class="card">
      <p class="eyebrow">Backend API</p>
      <div id="status" class="status checking">
        <span class="dot"></span>
        <span id="status-text">Checking API status…</span>
      </div>
      <a id="proceed" class="btn disabled" href="{{ frontend }}" aria-disabled="true">Open AgriKA-GIS &rarr;</a>
      <p class="hint" id="hint"></p>
    </div>
  </main>
  <footer>Health endpoint: <a href="/api/health">/api/health</a></footer>
  <script>
    const statusEl = document.getElementById("status");
    const textEl = document.getElementById("status-text");
    const btn = document.getElementById("proceed");
    const hint = document.getElementById("hint");
    async function check() {
      try {
        const r = await fetch("/api/health", { cache: "no-store" });
        const d = await r.json();
        if (r.ok && d.status === "ok") {
          statusEl.className = "status ok";
          textEl.textContent = "API is running";
          btn.classList.remove("disabled");
          btn.removeAttribute("aria-disabled");
          hint.textContent = "You can proceed to the web app.";
          return;
        }
        throw new Error("bad status");
      } catch (e) {
        statusEl.className = "status bad";
        textEl.textContent = "API is not responding";
        hint.textContent = "Try refreshing in a moment.";
      }
    }
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
    app.register_blueprint(auth_bp)
    app.register_blueprint(boundaries_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(yields_bp)

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
