import json

from flask import Blueprint, Response, jsonify, request, stream_with_context

try:
    from study_agent.utils.llm import (
        generate_response as llm_generate_response,
        generate_response_stream as llm_generate_response_stream,
        reset_history,
    )
except ModuleNotFoundError:
    from utils.llm import (
        generate_response as llm_generate_response,
        generate_response_stream as llm_generate_response_stream,
        reset_history,
    )

chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/api/generate-response", methods=["POST"])
def generate_response():
    payload = request.get_json(silent=True) or {}
    user_input = payload.get("user_input")
    if not user_input:
        return jsonify({"message": "User input is required."}), 400

    response = llm_generate_response(user_input)
    return jsonify({"response": response}), 200


@chat_bp.route("/api/generate-response-stream", methods=["POST"])
def generate_response_stream():
    payload = request.get_json(silent=True) or {}
    user_input = payload.get("user_input")

    if not user_input:
        return jsonify({"message": "User input is required."}), 400

    def event_stream():
        for event in llm_generate_response_stream(user_input):
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
