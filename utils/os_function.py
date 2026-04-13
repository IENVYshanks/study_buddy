from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
FILES_DIR = BASE_DIR / "files"


def ensure_files_dir():
    FILES_DIR.mkdir(parents=True, exist_ok=True)


def list_files():
    ensure_files_dir()
    return sorted([path.name for path in FILES_DIR.iterdir() if path.is_file()])

def delete(name):
    ensure_files_dir()
    file_path = FILES_DIR / name

    if file_path.is_file():
        file_path.unlink()
        return "File deleted successfully."
    return "File not found."


def save(name, content):
    ensure_files_dir()
    file_path = FILES_DIR / name

    if file_path.is_file():
        return "File already exists. Please choose a different name."

    with open(file_path, "wb") as file_obj:
        file_obj.write(content)
    return "File saved successfully."


def delete_all():
    ensure_files_dir()
    deleted_count = 0

    for file_path in FILES_DIR.iterdir():
        if file_path.is_file():
            file_path.unlink()
            deleted_count += 1

    return deleted_count
