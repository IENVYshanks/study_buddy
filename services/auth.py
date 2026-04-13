USERS = [
    {"name": "ronit", "email": "ronit@123"},
    {"name": "sawai", "email": "sawai@123"},
]


def validate_user(name: str, email: str) -> bool:
    return any(user["name"] == name and user["email"] == email for user in USERS)
