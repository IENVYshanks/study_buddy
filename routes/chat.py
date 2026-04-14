import json

from flask import Blueprint, Response, jsonify, request, session, stream_with_context

from services.auth import get_user
from utils.os_function import normalize_username
from utils.llm import (
    generate_response as llm_generate_response,
    generate_response_stream as llm_generate_response_stream,
    reset_history,
)
from utils.rag_pipeline import query_rag

chat_bp = Blueprint("chat", __name__)


def _resolve_valid_username(payload):
    requested_username = (
        payload.get("username")
        or request.args.get("username")
        or session.get("username")
        or ""
    ).strip()
    safe_username = normalize_username(requested_username)
    user = get_user(requested_username)

    if not safe_username or user is None:
        return None, (jsonify({"message": "A valid username is required. Please sign in again."}), 401)

    session_username = (session.get("username") or "").strip()
    if session_username and session_username.lower() != user["name"].lower():
        return None, (jsonify({"message": "Username does not match the active session."}), 403)

    session["username"] = user["name"]
    return safe_username, None


def _get_rag_matches(payload, user_input):
    if not payload.get("username"):
        return []

    username, error = _resolve_valid_username(payload)
    if error:
        return error

    try:
        results = query_rag(
            username=username,
            query_text=user_input,
            collection_name=payload.get("collection_name"),
        )
        return results["matches"]
    except (PermissionError, ValueError):
        return []


@chat_bp.route("/api/query-context", methods=["POST"])
def query_context():
    payload = request.get_json(silent=True) or {}
    user_input = (payload.get("user_input") or "").strip()
    if not user_input:
        return jsonify({"message": "User input is required."}), 400

    username, error = _resolve_valid_username(payload)
    if error:
        return error

    try:
        results = query_rag(
            username=username,
            query_text=user_input,
            collection_name=payload.get("collection_name"),
            n_results=payload.get("n_results", 4),
        )
    except PermissionError as error:
        return jsonify({"message": str(error)}), 403
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except Exception as error:
        return jsonify({"message": f"Query failed: {error}"}), 500

    return jsonify(results), 200


@chat_bp.route("/api/generate-response", methods=["POST"])
def generate_response():
    payload = request.get_json(silent=True) or {}
    user_input = (payload.get("user_input") or "").strip()
    if not user_input:
        return jsonify({"message": "User input is required."}), 400

    rag_matches = _get_rag_matches(payload, user_input)
    if isinstance(rag_matches, tuple):
        return rag_matches

    response = llm_generate_response(user_input, rag_matches=rag_matches)
    return jsonify({"response": response}), 200


@chat_bp.route("/api/generate-response-stream", methods=["POST"])
def generate_response_stream():
    payload = request.get_json(silent=True) or {}
    user_input = (payload.get("user_input") or "").strip()

    if not user_input:
        return jsonify({"message": "User input is required."}), 400

    rag_matches = _get_rag_matches(payload, user_input)
    if isinstance(rag_matches, tuple):
        return rag_matches

    def event_stream():
        for event in llm_generate_response_stream(user_input, rag_matches=rag_matches):
            yield json.dumps(event) + "\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )


@chat_bp.route("/api/delete-history", methods=["POST"])
def delete_history():
    reset_history()
    return jsonify({"message": "Chat history has been reset."}), 200
