from flask import Flask, render_template, request, jsonify
import os
from utils.vector_db import embedding_model
import jwt
import datetime
from utils.rag_pipeline import create_rag

app = Flask(__name__)

SECRET_KEY = "super_secret_key_123"
model = None


def get_embedding_model():
    global model
    if model is None:
        model = embedding_model()
    return model


# ---------------- FILE UPLOAD ----------------
@app.route("/", methods=["GET", "POST"])
def test():
    if request.method == "POST":
        file = request.files.get("test_input")

        if not file:
            return jsonify({"error": "No file uploaded."})

        files_dir = "files"
        os.makedirs(files_dir, exist_ok=True)

        file_path = os.path.join(files_dir, file.filename)

        
        if os.path.exists(file_path):
            return jsonify({"error": f"File '{file.filename}' already exists."})

        file.save(file_path)
        return jsonify({"message": f"File '{file.filename}' uploaded successfully!"})

    return render_template("test.html")


# ---------------- DELETE ----------------
@app.route("/delete_all", methods=["POST"])
def delete_all():
    files_dir = "files"

    if os.path.exists(files_dir):
        for file_name in os.listdir(files_dir):
            file_path = os.path.join(files_dir, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)

        return jsonify({"message": "All files deleted successfully!"})

    return jsonify({"error": "Files directory does not exist."})


# ---------------- CREATE TOKEN ----------------
@app.route("/create_token", methods=["POST"])
def create_token():
    data = request.get_json()

    username = data.get("username")
    password = data.get("password")

    if username == "test_user" and password == "test_password":
        payload = {
            "user_id": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify({"token": token})

    return jsonify({"error": "Invalid credentials"})


# ---------------- PROTECTED ----------------
@app.route("/protected", methods=["GET"])
def verify_token():
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return jsonify({"error": "No token provided"}), 401

    try:
        token = auth_header.split(" ")[1]  # Bearer <token>

        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        return jsonify({
            "message": "Access granted",
            "user_id": decoded["user_id"]
        })

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401

    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401
    
    
# -----------------creation of rag ------------------------------
@app.route("/create_rag", methods = ["POST"])
def create():
    data = request.get_json()
    username = data.get("username")
    try:
        name = create_rag(username = username, embed_model = get_embedding_model())
        return jsonify({"message" :f"rag created for the uploaded files {name}"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500



# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True , use_reloader = False)
