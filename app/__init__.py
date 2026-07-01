from flask import Flask
from app.config import Config
from .extensions import db, migrate, jwt


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cedarlink.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # import + register blueprints HERE (important fix)

    from app.routes.auth_routes import auth_bp
    from app.routes.test_routes import test_bp
    from app.routes.store_routes import store_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(store_bp) 

    # load models (safe here). Use a different name so we do not
    # overwrite the local Flask instance named `app`.
    from . import models as _models  # noqa: F401

    print("🔵 Store routes loaded")

    print(app.url_map)
    return app
