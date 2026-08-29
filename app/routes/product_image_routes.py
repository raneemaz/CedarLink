from flask import Blueprint, request, jsonify, send_from_directory
from app.extensions import db
from app.models.product import Product
from app.models.product_image import ProductImage
from flask_jwt_extended import (
    jwt_required,
    get_jwt,
    get_jwt_identity
)

from app.utils.file_utils import (
    allowed_file,
    save_image,
    delete_image_file,
    product_image_url
)
from flask import current_app

product_image_bp = Blueprint("product_image_bp", __name__)


@product_image_bp.route("/uploads/products/<filename>", methods=["GET"])
def serve_product_image(filename):
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        filename,
    )


@product_image_bp.route("/products/<int:product_id>/images", methods=["POST"])
@jwt_required()
def add_image(product_id):
    claims = get_jwt()
    user_id = int(get_jwt_identity())

    product = Product.query.get_or_404(product_id)

    if claims.get("role") not in ["admin", "vendor"]:
        return jsonify({
            "message": "Only admins and vendors can upload product images"
        }), 403

    if (
        claims.get("role") != "admin"
        and product.store.owner_id != user_id
    ):
        return jsonify({
            "message": "Not allowed to upload images for this product"
        }), 403

    file = request.files.get("image")

    if not file:
        return jsonify({
            "message": "Image file is required"
        }), 400

    if file.filename == "":
        return jsonify({
            "message": "No image selected"
        }), 400

    if not allowed_file(file.filename):
        return jsonify({
            "message": "Invalid image format. Allowed: jpg, jpeg, png, webp"
        }), 400

    if len(product.images) >= current_app.config["MAX_IMAGES_PER_PRODUCT"]:
        return jsonify({
            "message": (
                f"You can upload a maximum of "
                f"{current_app.config['MAX_IMAGES_PER_PRODUCT']} "
                f"images for a product."
            )
        }), 400

    filename = save_image(file)
    image = ProductImage(
        image_url=filename,
        product_id=product.id
    )

    try:
        db.session.add(image)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        delete_image_file(filename)

        current_app.logger.error(str(e))

        return jsonify({
            "message": "Failed to upload image"
        }), 500

    return jsonify({
        "message": "Image uploaded successfully",
        "image": {
            "id": image.id,
            "image_url": product_image_url(image.image_url),
            "product_id": image.product_id
        }
    }), 201


@product_image_bp.route("/products/<int:product_id>/images/<int:image_id>",
                        methods=["DELETE"])
@jwt_required()
def delete_image(product_id, image_id):

    claims = get_jwt()
    user_id = int(get_jwt_identity())

    product = Product.query.get(product_id)

    if product is None:
        return jsonify({
            "message": "Product not found"
        }), 404

    image = ProductImage.query.filter_by(
        id=image_id,
        product_id=product.id
    ).first()

    if image is None:
        return jsonify({
            "message": "Image not found"
        }), 404

    if claims.get("role") != "admin":
        if product.store.owner_id != user_id:
            return jsonify({
                "message": "Not allowed to delete this image"
            }), 403

    try:
        delete_image_file(image.image_url)

        db.session.delete(image)
        db.session.commit()

        return jsonify({
            "message": "Image deleted successfully"
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "message": "Failed to delete image"
        }), 500
