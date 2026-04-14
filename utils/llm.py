import os
from dotenv import load_dotenv

load_dotenv()

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_ollama import ChatOllama
except ModuleNotFoundError:
    AIMessage = None
    HumanMessage = None
    SystemMessage = None
    ChatOllama = None

model = os.getenv("OLLAMA_MODEL")
history = []
DEFAULT_MODEL = model if model else "qwen3.5:0.8b"
SYSTEM_PROMPT = ("""format
    You are Study Agent, a helpful study assistant. 
    Use the retrieved context when it is relevant to the user's question. 
    If the retrieved context is insufficient, say so clearly and avoid inventing facts.
    also say if you used the context given 
    """
)


def _build_context_block(rag_matches):
    if not rag_matches:
        return ""

    lines = ["Retrieved context:"]
    for index, match in enumerate(rag_matches, start=1):
        content = (match.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"[Context {index}] {content}")

    return "\n".join(lines)


def _build_messages(user_input, rag_matches=None):
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    messages.extend(history)

    context_block = _build_context_block(rag_matches)
    if context_block:
        prompt = f"{context_block}\n\nUser question:\n{user_input}"
    else:
        prompt = user_input

    messages.append(HumanMessage(content=prompt))
    return messages


def generate_response(user_input, rag_matches=None):
    if ChatOllama is None or HumanMessage is None:
        return "Ollama is not installed on the server."

    try:
        chat = ChatOllama(model=DEFAULT_MODEL)
        messages = _build_messages(user_input, rag_matches=rag_matches)
        response = chat.invoke(messages)
        response_text = (response.content or "").strip()

        if not response_text:
            response_text = "I could not generate a response right now."

        history.append(HumanMessage(content=user_input))
        history.append(AIMessage(content=response_text))
        return response_text
    except Exception as e:
        print(f"Error during response generation: {e}")
        return "Sorry, there was an error generating the response."


def generate_response_stream(user_input, rag_matches=None):
    if ChatOllama is None or HumanMessage is None:
        yield {"type": "error", "message": "Ollama is not installed on the server."}
        return

    chat = ChatOllama(model=DEFAULT_MODEL)
    chunks = []

    try:
        messages = _build_messages(user_input, rag_matches=rag_matches)
        for chunk in chat.stream(messages):
            text = getattr(chunk, "content", "") or ""

            if text:
                chunks.append(text)
                yield {"type": "chunk", "content": text}

        full_response = "".join(chunks).strip()
        if not full_response:
            full_response = "I could not generate a response right now."
            yield {"type": "chunk", "content": full_response}

        history.append(HumanMessage(content=user_input))
        history.append(AIMessage(content=full_response))
        yield {"type": "done"}
    except Exception as e:
        print(f"Error during streaming response generation: {e}")
        yield {"type": "error", "message": "Sorry, there was an error generating the response."}
    
def reset_history():
    global history
    history.clear()
