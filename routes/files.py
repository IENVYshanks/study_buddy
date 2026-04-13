from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename
from pathlib import Path
import os

try:
    from study_agent.utils.os_function import delete, delete_all, list_files, save
    from study_agent.utils.rag_pipeline import vectorize_uploaded_files
except ModuleNotFoundError:
    from utils.os_function import delete, delete_all, list_files, save
    from utils.rag_pipeline import vectorize_uploaded_files

files_bp = Blueprint("files", __name__)
ALLOWED_FILE_EXTENSIONS = {".pdf", ".txt", ".md", ".doc", ".docx", ".csv", ".json"}


@files_bp.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"message": "No file part in the request."}), 400

    file_obj = request.files["file"]
    filename = secure_filename(file_obj.filename or "")

    if not filename:
        return jsonify({"message": "Please select a valid file."}), 400

    file_extension = Path(filename).suffix.lower()
    if file_extension not in ALLOWED_FILE_EXTENSIONS:
        return jsonify(
            {
                "message": "Unsupported file type. Allowed: PDF, TXT, MD, DOC, DOCX, CSV, JSON."
            }
        ), 400

    result = save(filename, file_obj.read())
    status_code = 200 if result == "File saved successfully." else 409
    return jsonify({"message": result, "filename": filename, "files": list_files()}), status_code


@files_bp.route("/api/delete", methods=["POST"])
def delete_file():
    filename = request.form.get("filename")
    
    if not filename:
        return jsonify({"message": "Filename is required."}), 400

    result = delete(filename)
    status_code = 200 if result == "File deleted successfully." else 404
    return jsonify({"message": result, "filename": filename, "files": list_files()}), status_code


@files_bp.route("/api/delete-all", methods=["POST"])
def delete_all_files():
    removed_count = delete_all()
    return jsonify(
        {
            "message": f"Removed {removed_count} file{'s' if removed_count != 1 else ''}.",
            "files": list_files(),
        }
    ), 200


@files_bp.route("/api/files", methods=["GET"])
def get_files():
    return jsonify({"files": list_files()}), 200


@files_bp.route("/api/vectorize-files", methods=["POST"])
def vectorize_files():
    current_files = list_files()
    if not current_files:
        return jsonify({"message": "No uploaded files found to vectorize."}), 400

    payload = request.get_json(silent=True) or {}
    username = payload.get("username")

    try:
        rag_backend = current_app.extensions["rag_backend"]
        summary = vectorize_uploaded_files(
            username=username,
            embed_model=rag_backend.get_embedding_model(),
        )
    except (KeyError, RuntimeError) as error:
        return jsonify({"message": f"RAG backend is unavailable: {error}"}), 500
    except Exception as error:
        return jsonify({"message": f"Vectorization failed: {error}"}), 500

    message = (
        f"Vectorization complete. Processed {summary['processed_files']} file(s) "
        f"into {summary['vectorized_chunks']} chunk(s)."
    )

    return jsonify({"message": message, "summary": summary}), 200
