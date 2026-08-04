import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app


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


def delete_image_file(filename):
    path = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        filename
    )

    if os.path.exists(path):
        os.remove(path)
