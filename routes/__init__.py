from flask import Flask

from .chat import chat_bp
from .files import files_bp
from .pages import pages_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(pages_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(chat_bp)
