from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.product import Product
from app.models.product_image import ProductImage

product_image_bp = Blueprint("product_image_bp", __name__)


@product_image_bp.route("/products/<int:id>/images", methods=["POST"])
def add_image(id):
    product = Product.query.get_or_404(id)
    data = request.get_json()

    image = ProductImage(
        image_url=data.get("image_url"),
        product_id=product.id
    )

    db.session.add(image)
    db.session.commit()

    return jsonify({"message": "Image added"}), 201


@product_image_bp.route("/products/<int:product_id>/images/<int:image_id>",
                        methods=["DELETE"])
def delete_image(product_id, image_id):
    image = ProductImage.query.filter_by(
        id=image_id,
        product_id=product_id
    ).first_or_404()

    db.session.delete(image)
    db.session.commit()

    return jsonify({"message": "Image deleted"}), 200
