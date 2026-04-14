from flask import Blueprint, redirect, render_template, request, session, url_for

from services.auth import validate_user

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/", endpoint="home")
def home():
    return render_template("index.html")


@pages_bp.route("/workspace", endpoint="workspace")
def workspace():
    return render_template("workspace.html")


@pages_bp.route("/upload", endpoint="upload")
def upload():
    return render_template("workspace.html")


@pages_bp.route("/chat", endpoint="chat")
def chat():
    return render_template("workspace.html")


@pages_bp.route("/api/submit", methods=["POST"], endpoint="submit_details")
def submit_details():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()

    if validate_user(name=name, email=email):
        session["username"] = name
        return redirect(url_for("pages.workspace"))
    return render_template("index.html", error="Invalid details. Please try again.")
