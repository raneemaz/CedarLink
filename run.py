from app import create_app
from app.extensions import db

# create the app before using @app.route
app = create_app()


@app.route("/db-test")
def db_test():
    try:
        db.session.execute("SELECT 1")
        return {"db": "connected ✅"}
    except Exception as e:
        return {"db": "failed ❌", "error": str(e)}


@app.route("/")
def home():
    return {"message": "CedarLink API is running 🚀"}


if __name__ == "__main__":
    app.run(debug=True)
