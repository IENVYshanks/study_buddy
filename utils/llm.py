import os
from flask import jsonify
try:
    from langchain_community.chat_models import ChatOllama
except ModuleNotFoundError:
    ollama = None

model = os.getenv("OLLAMA_MODEL")
history = []
DEFAULT_MODEL = model if model else "qwen3.5:0.8b"


def generate_response(user_input):
    if ollama is None:
        return "Ollama is not installed on the server."

    history.append({"role": "user", "content": user_input})

    try:
        chat = ChatOllama(model ="qwen3.5:0.8b")
        response = chat.invoke(
            messages= user_input
        )
        if response :
            return jsonify(response.content.strip())

        if not response_text:
            response_text = "I could not generate a response right now."

        history.append({"role": "assistant", "content": response_text})
        return response_text
    except Exception as e:
        print(f"Error during response generation: {e}")
        return "Sorry, there was an error generating the response."


def generate_response_stream(user_input):
    if ollama is None:
        yield {"type": "error", "message": "Ollama is not installed on the server."}
        return

    history.append({"role": "user", "content": user_input})
    chunks = []

    try:
        stream = ollama.chat(
            model=DEFAULT_MODEL,
            messages=list(history),
            stream=True
        )

        for chunk in stream:
            text = ""
            if isinstance(chunk, dict):
                text = chunk.get("message", {}).get("content", "")

            if text:
                chunks.append(text)
                yield {"type": "chunk", "content": text}

        full_response = "".join(chunks).strip()
        if not full_response:
            full_response = "I could not generate a response right now."
            yield {"type": "chunk", "content": full_response}

        history.append({"role": "assistant", "content": full_response})
        yield {"type": "done"}
    except Exception as e:
        print(f"Error during streaming response generation: {e}")
        yield {"type": "error", "message": "Sorry, there was an error generating the response."}
    
def reset_history():
    global history
    history.clear()
