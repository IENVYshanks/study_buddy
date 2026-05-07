import json

from flask import Blueprint, jsonify, request, session
from pathlib import Path
from werkzeug.utils import secure_filename
from src.services.auth import get_user
from src.utils.os_function import delete, delete_all, list_files, normalize_username, save
from src.utils.rag_pipeline import vectorize_uploaded_files
from src.utils.vector_db import VectorStoreManager

files_bp = Blueprint("files", __name__)
ALLOWED_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".doc", ".docx", ".csv", ".json"}


def _extract_payload():
    payload = request.get_json(silent=True)
    if isinstance(payload, dict):
        return payload

    if request.mimetype not in {"application/json", "text/plain"}:
        return {}

    try:
        decoded = (request.get_data(cache=True, as_text=True) or "").strip()
        parsed = json.loads(decoded) if decoded else {}
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _extract_username():
    payload = _extract_payload()
    return (
        request.form.get("username")
        or request.args.get("username")
        or payload.get("username")
        or session.get("username")
        or ""
    ).strip()


def _resolve_valid_username():
    requested_username = _extract_username()
    safe_username = normalize_username(requested_username)
    user = get_user(requested_username)

    if not safe_username or user is None:
        return None, (jsonify({"message": "A valid username is required. Please sign in again."}), 401)

    session_username = (session.get("username") or "").strip()
    if session_username and session_username.lower() != user["name"].lower():
        return None, (jsonify({"message": "Username does not match the active session."}), 403)

    session["username"] = user["name"]
    return safe_username, None


def _cleanup_workspace(username, collection_name=None, missing_collection_ok=True):
    deleted_collections = VectorStoreManager.delete_collection_for_user(
        username=username,
        collection_name=collection_name,
        missing_ok=missing_collection_ok,
    )
    removed_count = delete_all(username)
    return deleted_collections, removed_count


@files_bp.route("/api/upload", methods=["POST"])
def upload_file():
    username, error = _resolve_valid_username()
    if error:
        return error

    if "file" not in request.files:
        return jsonify({"message": "No file part in the request."}), 400

    file_obj = request.files["file"]
    original_name = secure_filename(file_obj.filename or "")
    if not original_name:
        return jsonify({"message": "Please select a valid file."}), 400

    file_extension = Path(original_name).suffix.lower()
    if file_extension not in ALLOWED_FILE_EXTENSIONS:
        return jsonify(
            {
                "message": "Unsupported file type. Allowed: PDF, TXT, MD, DOC, DOCX, CSV, JSON."
            }
        ), 400

    result = save(original_name, file_obj.read(), username)
    filename = f"{username}_{original_name}"
    status_code = 200 if result == "File saved successfully." else 409
    return jsonify({"message": result, "filename": filename, "files": list_files(username)}), status_code


@files_bp.route("/api/delete", methods=["POST"])
def delete_file():
    username, error = _resolve_valid_username()
    if error:
        return error

    filename = request.form.get("filename")
    
    if not filename:
        return jsonify({"message": "Filename is required."}), 400

    result = delete(filename, username)
    status_code = 200 if result == "File deleted successfully." else 404
    return jsonify({"message": result, "filename": filename, "files": list_files(username)}), status_code


@files_bp.route("/api/delete-all", methods=["POST"])
def delete_all_files():
    username, error = _resolve_valid_username()
    if error:
        return error

    removed_count = delete_all(username)
    return jsonify(
        {
            "message": f"Removed {removed_count} file{'s' if removed_count != 1 else ''}.",
            "files": list_files(username),
        }
    ), 200


@files_bp.route("/api/files", methods=["GET"])
def get_files():
    username, error = _resolve_valid_username()
    if error:
        return error

    return jsonify({"files": list_files(username)}), 200


@files_bp.route("/api/vectorize-files", methods=["POST"])
def vectorize_files():
    username, error = _resolve_valid_username()
    if error:
        return error

    current_files = list_files(username)
    if not current_files:
        return jsonify({"message": "No uploaded files found to vectorize."}), 400

    try:
        summary = vectorize_uploaded_files(username=username)
    except Exception as error:
        return jsonify({"message": f"Vectorization failed: {error}"}), 500

    message = (
        f"Vectorization complete. Processed {summary['processed_files']} file(s) "
        f"into {summary['vectorized_chunks']} chunk(s)."
    )

    return jsonify({"message": message, "summary": summary}), 200


@files_bp.route("/api/go-back", methods=["POST"])
def go_back():
    username, error = _resolve_valid_username()
    if error:
        return error

    try:
        deleted_collections, removed_count = _cleanup_workspace(
            username=username,
            collection_name=None,
            missing_collection_ok=True,
        )
    except PermissionError as error:
        return jsonify({"message": str(error)}), 403
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except Exception as error:
        return jsonify({"message": f"Unable to reset workspace: {error}"}), 500

    return jsonify(
        {
            "message": "Workspace reset. Files and RAG collection were removed.",
            "files": list_files(username),
            "deleted_files": removed_count,
            "deleted_collections": deleted_collections,
        }
    ), 200


@files_bp.route("/api/cleanup", methods=["POST"])
def cleanup_workspace():
    username, error = _resolve_valid_username()
    if error:
        return error

    try:
        deleted_collections, removed_count = _cleanup_workspace(
            username=username,
            collection_name=None,
            missing_collection_ok=True,
        )
    except PermissionError as error:
        return jsonify({"message": str(error)}), 403
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except Exception as error:
        return jsonify({"message": f"Unable to clean up workspace: {error}"}), 500

    return jsonify(
        {
            "message": "Workspace cleanup complete. Files and vector collections were removed.",
            "files": list_files(username),
            "deleted_files": removed_count,
            "deleted_collections": deleted_collections,
        }
    ), 200
