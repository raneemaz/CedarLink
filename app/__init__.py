from flask import Flask, app
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
    from app.routes.category_routes import category_bp
    from app.routes.product_routes import product_bp
    from app.routes.product_image_routes import product_image_bp
    from app.routes.cart_routes import cart_bp
    from app.routes.order_routes import order_bp
    from app.routes.payment_routes import payment_bp
    from app.routes.delivery_routes import delivery_bp
    from app.routes.admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(delivery_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(order_bp, url_prefix="/api")
    app.register_blueprint(cart_bp, url_prefix="/cart")
    app.register_blueprint(product_image_bp, url_prefix="/api")
    app.register_blueprint(product_bp, url_prefix="/api")
    app.register_blueprint(category_bp, url_prefix="/api")
    app.register_blueprint(auth_bp)
    app.register_blueprint(test_bp)
    app.register_blueprint(store_bp)

    # load models (safe here). Use a different name so we do not
    # overwrite the local Flask instance named `app`.
    from . import models as _models  # noqa: F401

    print("🔵 Store routes loaded")

    print(app.url_map)
    return app
