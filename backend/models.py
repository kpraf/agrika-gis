"""
SQLAlchemy models mirroring the ERD.

These map to the tables created by db/schema.sql (we do NOT use create_all;
the SQL schema is the source of truth so the PostGIS geometry column is set up
correctly).
"""
from extensions import db

# NOTE: barangays.boundary_geometry (PostGIS) is intentionally not mapped yet.
# It's added once PostGIS is installed + schema_geometry.sql runs (GeoJSON import step),
# at which point we re-add the Geometry column to the Barangay model below.


class Role(db.Model):
    __tablename__ = "roles"
    role_id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), nullable=False, unique=True)

    users = db.relationship("User", back_populates="role")


class Municipality(db.Model):
    __tablename__ = "municipalities"
    municipality_id = db.Column(db.Integer, primary_key=True)
    municipality_name = db.Column(db.String(100), nullable=False, unique=True)

    users = db.relationship("User", back_populates="municipality")
    barangays = db.relationship("Barangay", back_populates="municipality")


class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150))
    status = db.Column(db.String(20), nullable=False, default="Active")
    role_id = db.Column(db.Integer, db.ForeignKey("roles.role_id"), nullable=False)
    municipality_id = db.Column(
        db.Integer, db.ForeignKey("municipalities.municipality_id"), nullable=True
    )

    role = db.relationship("Role", back_populates="users")
    municipality = db.relationship("Municipality", back_populates="users")

    def to_public_dict(self):
        """The user shape the frontend consumes — no password hash."""
        return {
            "id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "status": self.status,
            "role": self.role.role_name if self.role else None,
            "municipality": self.municipality.municipality_name if self.municipality else None,
            "municipality_id": self.municipality_id,
        }


class Barangay(db.Model):
    __tablename__ = "barangays"
    barangay_id = db.Column(db.Integer, primary_key=True)
    barangay_name = db.Column(db.String(100), nullable=False)
    # boundary_geometry added at the PostGIS step:
    #   boundary_geometry = db.Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326))
    municipality_id = db.Column(
        db.Integer, db.ForeignKey("municipalities.municipality_id"), nullable=False
    )

    municipality = db.relationship("Municipality", back_populates="barangays")


class Season(db.Model):
    __tablename__ = "seasons"
    season_id = db.Column(db.Integer, primary_key=True)
    season_type = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)


class Prediction(db.Model):
    __tablename__ = "predictions"
    prediction_id = db.Column(db.Integer, primary_key=True)
    predicted_yield = db.Column(db.Float, nullable=False)
    barangay_id = db.Column(db.Integer, db.ForeignKey("barangays.barangay_id"), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.season_id"), nullable=False)


class YieldRecord(db.Model):
    __tablename__ = "yield_records"
    yield_id = db.Column(db.Integer, primary_key=True)
    observed_yield = db.Column(db.Float, nullable=False)
    barangay_id = db.Column(db.Integer, db.ForeignKey("barangays.barangay_id"), nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey("seasons.season_id"), nullable=False)


class Residual(db.Model):
    __tablename__ = "residuals"
    residual_id = db.Column(db.Integer, primary_key=True)
    residual_value = db.Column(db.Float, nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey("predictions.prediction_id"), nullable=False)
    yield_id = db.Column(db.Integer, db.ForeignKey("yield_records.yield_id"), nullable=False)
