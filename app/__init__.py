import os
from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix
from app.config import get_config
from .extensions import db, migrate, jwt, limiter
from flask_cors import CORS
from app.routes.user_routes import user_bp
from app.routes.address_routes import address_bp


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    # Trust one layer of reverse-proxy headers so url_for(_external=True)
    # emits the public host and scheme in production rather than localhost.
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1
    )

    # Allowed browser origins for /api/*. Defaults cover the common Vite dev
    # ports (5173 drifts to 5174/5175 when a port is busy). Override with the
    # CORS_ORIGINS env var (comma-separated) in production.
    _default_cors_origins = (
        "http://localhost:5173,"
        "http://localhost:5174,"
        "http://localhost:5175"
    )
    _cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", _default_cors_origins).split(
            ","
        )
        if origin.strip()
    ]

    CORS(
        app,
        resources={r"/api/*": {"origins": _cors_origins}},
        supports_credentials=True,
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    app.config["UPLOAD_FOLDER"] = os.path.abspath(app.config["UPLOAD_FOLDER"])

    # init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)

    # import + register blueprints HERE (important fix)

    from app.routes.auth_routes import auth_bp
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
    from app.routes.vendor_routes import vendor_bp
    from app.routes.review_routes import review_bp
    from app.routes.coupon_routes import (
        admin_coupon_bp,
        vendor_coupon_bp,
    )

    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(admin_coupon_bp, url_prefix="/api/admin")
    app.register_blueprint(vendor_coupon_bp)
    # Delivery routes are defined as /delivery/... — mount them under /api so
    # they share the API surface every other blueprint uses.
    app.register_blueprint(delivery_bp, url_prefix="/api")
    app.register_blueprint(payment_bp, url_prefix="/api")
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
    app.register_blueprint(store_bp)
    app.register_blueprint(vendor_bp)
    app.register_blueprint(review_bp, url_prefix="/api")

    # load models (safe here). Use a different name so we do not
    # overwrite the local Flask instance named `app`.
    from . import models as _models  # noqa: F401

    # custom CLI commands (e.g. `flask create-admin`)
    from app.cli import register_cli

    register_cli(app)

    # One JSON error shape across every blueprint (CL-20).
    from app.utils.errors import register_error_handlers

    register_error_handlers(app)

    # JWT revocation: logout + bulk revoke on suspend / reset (CL-09).
    from app.services.token_service import register_jwt_callbacks

    register_jwt_callbacks(jwt)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(_error):
        # MAX_CONTENT_LENGTH aborts the request before the view runs, so this
        # has to be an app-level handler. Without it Flask returns HTML that
        # the axios error handler cannot read.
        return jsonify({
            "message": "Image is too large. Maximum size is 5 MB."
        }), 413

    return app
