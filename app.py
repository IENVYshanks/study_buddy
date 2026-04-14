import os
from flask import Flask
from routes import register_blueprints
from utils.vector_db import embedding_model


class RagBackend:
    def __init__(self) -> None:
        self._embedding_model = None

    def get_embedding_model(self):
        if self._embedding_model is None:
            self._embedding_model = embedding_model()
        return self._embedding_model


def init_rag_backend(app: Flask) -> None:
    app.extensions["rag_backend"] = RagBackend()


def create_app() -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static",
        template_folder="templates",
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "study-buddy-dev-secret")
    init_rag_backend(app)
    register_blueprints(app)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
