import os
from flask import Flask
from app.config import Config
from .extensions import db, migrate, jwt
from flask_cors import CORS
from app.routes.user_routes import user_bp
from app.routes.address_routes import address_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        resources={r"/api/*": {"origins": "http://localhost:5173"}},
        supports_credentials=True,
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.config["UPLOAD_FOLDER"] = os.path.abspath(app.config["UPLOAD_FOLDER"])

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # import + register blueprints HERE (important fix)

    from app.routes.auth_routes import auth_bp
    from app.routes.test_routes import test_bp
    from app.routes.store_routes import store_bp
    from app.routes.category_routes import category_bp
    from app.routes.product_routes import product_bp
    from app.routes.product_image_routes import product_image_bp
    from app.routes.cart_routes import cart_bp
    from app.routes.order_routes import order_bp
    from app.routes.payment_routes import payment_bp
    from app.routes.payment_method_routes import payment_method_bp
    from app.routes.two_factor_routes import two_factor_bp
    from app.routes.delivery_routes import delivery_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.currency_routes import currency_bp
    from app.routes.notification_routes import notification_bp

    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(delivery_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(payment_method_bp)
    app.register_blueprint(two_factor_bp)
    app.register_blueprint(order_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/api/cart")
    app.register_blueprint(product_image_bp, url_prefix="/api")
    app.register_blueprint(product_bp, url_prefix="/api")
    app.register_blueprint(category_bp, url_prefix="/api")
    app.register_blueprint(address_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(currency_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(store_bp)

    # load models (safe here). Use a different name so we do not
    # overwrite the local Flask instance named `app`.
    from . import models as _models  # noqa: F401

    # custom CLI commands (e.g. `flask create-admin`)
    from app.cli import register_cli

    register_cli(app)

    print("🔵 Store routes loaded")

    print(app.url_map)
    return app
