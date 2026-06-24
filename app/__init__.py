from flask import Flask
from .config import Config
from .extensions import db, migrate, jwt, cors


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    # register blueprints later
    # from .routes.auth_routes import auth_bp
    # app.register_blueprint(auth_bp, url_prefix="/api/auth")

    return app
