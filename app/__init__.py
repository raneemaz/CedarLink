from flask import Flask
from .config import Config
from .extensions import db, migrate


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cedarlink.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # register blueprints later
    # from .routes.auth_routes import auth_bp
    # app.register_blueprint(auth_bp, url_prefix="/api/auth")

    import app.models  # noqa: F401

    return app
