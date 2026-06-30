from flask import Blueprint

test_bp = Blueprint("test", __name__)


@test_bp.route("/db-test")
def db_test():
    return {"message": "DB is working"}
