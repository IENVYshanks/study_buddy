from pathlib import Path
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent.parent
FILES_DIR = BASE_DIR / "files"


def ensure_files_dir():
    FILES_DIR.mkdir(parents=True, exist_ok=True)


def normalize_username(username: str) -> str:
    return secure_filename((username or "").strip())


def build_user_filename(username: str, filename: str) -> str:
    safe_username = normalize_username(username)
    safe_filename = secure_filename(filename)

    if not safe_username or not safe_filename:
        return ""

    return f"{safe_username}_{safe_filename}"


def belongs_to_user(filename: str, username: str) -> bool:
    safe_username = normalize_username(username)
    return bool(safe_username) and filename.startswith(f"{safe_username}_")


def list_files(username: str = None):
    ensure_files_dir()
    safe_username = normalize_username(username)

    return sorted([
        path.name
        for path in FILES_DIR.iterdir()
        if path.is_file() and (not safe_username or belongs_to_user(path.name, safe_username))
    ])


def delete(name, username: str):
    ensure_files_dir()
    safe_name = secure_filename(name)
    if not belongs_to_user(safe_name, username):
        return "File not found."

    file_path = FILES_DIR / safe_name

    if file_path.is_file():
        file_path.unlink()
        return "File deleted successfully."
    return "File not found."


def save(name, content, username: str):
    ensure_files_dir()
    file_name = build_user_filename(username, name)
    if not file_name:
        return "Invalid username or file name."

    file_path = FILES_DIR / file_name

    if file_path.exists():
        return "File already exists."

    with open(file_path, "wb") as f:
        f.write(content)

    return "File saved successfully."


def delete_all(username: str):
    ensure_files_dir()
    deleted_count = 0

    for file_path in FILES_DIR.iterdir():
        if file_path.is_file() and belongs_to_user(file_path.name, username):
            file_path.unlink()
            deleted_count += 1

    return deleted_count
