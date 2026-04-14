USERS = [
    {"name": "ronit", "email": "ronit@123"},
    {"name": "sawai", "email": "sawai@123"},
]


def get_user(name: str):
    if not name:
        return None

    normalized_name = name.strip().lower()
    return next(
        (user for user in USERS if user["name"].strip().lower() == normalized_name),
        None,
    )


def validate_user(name: str, email: str) -> bool:
    user = get_user(name)
    if not user or not email:
        return False

    return user["email"] == email.strip()
