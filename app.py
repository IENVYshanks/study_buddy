import os
from flask import Flask
from routes import register_blueprints


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static",
        template_folder="templates",
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "study-buddy-dev-secret")
    register_blueprints(app)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
