"""
AgriKA-GIS Flask API — application factory + entry point.

Run (from the backend/ folder, with the virtualenv active):
    flask --app app run --debug
or:
    python app.py
"""
from flask import Flask, jsonify

from config import Config
from extensions import db, jwt, cors


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

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
