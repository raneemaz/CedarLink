from flask import Blueprint, request, jsonify
from app.extensions import db
from app.models.category import Category
from flask_jwt_extended import jwt_required, get_jwt
from app.models.product import Product

category_bp = Blueprint("category_bp", __name__)


# The three interface languages; English is required, ar/fr optional. The
# API returns every translation and the client picks (C.5). See
# docs/decisions/0012-product-category-translation.md.
_LANGUAGES = ("en", "ar", "fr")
_MISSING = object()


def _read_names(data, existing=None):
    """name_en/ar/fr out of a request body, `name` accepted for name_en.

    Returns (values, error). English must be non-empty on create; on update
    an absent key is left untouched and a blank ar/fr clears that translation.
    """
    values = {}

    for lang in _LANGUAGES:
        keys = (f"name_{lang}", "name") if lang == "en" else (f"name_{lang}",)
        raw = next((data[k] for k in keys if k in data), _MISSING)
        if raw is _MISSING:
            continue
        text = (raw or "").strip() if isinstance(raw, (str, type(None))) \
            else None
        if text is None:
            return None, f"name_{lang} must be a string"
        if lang == "en" and not text:
            return None, "Category name is required"
        values[f"name_{lang}"] = text or None

    if existing is None and "name_en" not in values:
        return None, "Category name is required"
    return values, None


@category_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = Category.query.all()
    return jsonify([cat.to_dict() for cat in categories]), 200


@category_bp.route("/categories", methods=["POST"])
@jwt_required()
def create_category():
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"message": "Admin only"}), 403

    data = request.get_json() or {}

    names, error = _read_names(data)
    if error:
        return jsonify({"message": error}), 400

    existing_category = Category.query.filter_by(
        name_en=names["name_en"]
    ).first()

    if existing_category:
        return jsonify({
            "message": "Category already exists"
        }), 400

    new_category = Category(
        description=data.get("description"),
        **names,
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
    category = db.session.get(Category, id)

    if not category:
        return jsonify({"message": "Category not found"}), 404

    data = request.get_json() or {}

    names, error = _read_names(data, existing=category)
    if error:
        return jsonify({"message": error}), 400

    if "name_en" in names:
        clash = Category.query.filter_by(name_en=names["name_en"]).first()
        if clash and clash.id != category.id:
            return jsonify({
                "message": "Category already exists"
            }), 400

    for column, value in names.items():
        setattr(category, column, value)
    if "description" in data:
        category.description = data.get("description")

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
    category = db.session.get(Category, id)

    if not category:
        return jsonify({
            "message": "Category not found"
        }), 404

    if Product.query.filter_by(category_id=id).first():
        return jsonify({
            "message": "Cannot delete category because it contains products"
        }), 400
    db.session.delete(category)
    db.session.commit()

    return jsonify({"message": "Category deleted"}), 200
