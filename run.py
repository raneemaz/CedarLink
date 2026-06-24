from app import create_app
from app.extensions import db

app = create_app()


@app.route("/")
def home():
    return {"message": "CedarLink API is running 🚀"}


if __name__ == "__main__":
    app.run(debug=True)
