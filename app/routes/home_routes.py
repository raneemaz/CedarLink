"""The home page's category sections.

One request rather than one per category, and the ordering decision stays
on the server where it can be explained. Open to signed-out visitors, who
get the default order.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services import home_service, shopping_preferences_service

home_bp = Blueprint("home", __name__)


@home_bp.route("/home/sections", methods=["GET"])
@jwt_required(optional=True)
def get_home_sections():
    identity = get_jwt_identity()

    # Signed out is a supported case, not an error: the default order needs
    # no account. Reading never creates a preferences row.
    user_id = int(identity) if identity else None

    language = request.args.get("lang", "en")

    sections = home_service.home_sections(user_id)

    return jsonify({
        "sections": home_service.serialize_sections(sections, language),
        # Lets the page say *why* it is in this order. False means the
        # default order — nobody has stated an interest — which is a
        # different message from "these are your categories".
        "personalized": shopping_preferences_service.has_interests(user_id),
    }), 200
