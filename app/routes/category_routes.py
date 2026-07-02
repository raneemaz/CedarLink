from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.category import Category
from flask_jwt_extended import jwt_required, get_jwt

category_bp = Blueprint("category_bp", __name__)


@category_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.all()

    result = []
    for cat in categories:
        result.append({
            "id": cat.id,
            "name": cat.name,
            "description": cat.description
        })
    return jsonify(result), 200


@category_bp.route("/categories", methods=["POST"])
@jwt_required()
def create_category():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin only"}), 403
    data = request.get_json()

    new_category = Category(
        name=data.get("name"),
        description=data.get("description")
    )

    db.session.add(new_category)
    db.session.commit()

    return jsonify({
        "message": "Category created successfully",
        "id": new_category.id
    }), 201


@category_bp.route("/categories/<int:id>", methods=["PUT"])
@jwt_required()
def update_category(id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin only"}), 403
    category = Category.query.get_or_404(id)
    data = request.get_json()

    category.name = data.get("name", category.name)
    category.description = data.get("description", category.description)

    db.session.commit()

    return jsonify({
        "message": "Category updated successfully"
    }), 200


@category_bp.route("/categories/<int:id>", methods=["DELETE"])
@jwt_required()
def delete_category(id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"message": "Admin only"}), 403
    category = Category.query.get_or_404(id)

    db.session.delete(category)
    db.session.commit()

    return jsonify({"message": "Category deleted"}), 200
