import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-to-a-long-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY",
                               "change-this-to-a-long-secret-key")

    SQLALCHEMY_DATABASE_URI = "sqlite:///cedarlink.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, "uploads", "products")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    MAX_IMAGES_PER_PRODUCT = 5
