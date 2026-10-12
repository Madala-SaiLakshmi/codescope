def auth_headers(client, email="user@example.com", password="correct-horse-1"):
    client.post("/api/auth/register", json={"email": email, "password": password})
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def login(client, email="user@example.com", password="correct-horse-1"):
    client.headers.update(auth_headers(client, email, password))
