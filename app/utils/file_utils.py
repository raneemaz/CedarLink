import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app, url_for


def allowed_file(filename):
    if "." not in filename:
        return False

    extension = filename.rsplit(".", 1)[1].lower()

    return extension in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]


def generate_unique_filename(filename):
    extension = filename.rsplit(".", 1)[1].lower()

    unique_filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    return secure_filename(unique_filename)


def save_image(file):
    filename = generate_unique_filename(file.filename)

    path = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

    file.save(path)

    return filename


def product_image_url(filename):
    """Turn a stored image filename into a URL the browser can load."""
    if not filename:
        return None

    return url_for(
        "product_image_bp.serve_product_image",
        filename=filename,
        _external=True,
    )


def delete_image_file(filename):
    path = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

    if os.path.exists(path):
        os.remove(path)
