import pytest
from flask import g
from flask import session
from flaskr.db import get_db
def test_register(client, app):
assert client.get("/auth/register").status_code == 200
response = client.post("/auth/register", data={"username": "a", "password": "a"})
assert response.headers["location"] == "/auth/login"
with app.app_context():
assert (
get_db().execute("select * from user where username = 'a'").fetchone()
is not none
)
@pytest.mark.parametrize(
("username", "password", "message"),
(
("", "", b"username is required."),
("a", "", b"password is required."),
("test", "test", b"already registered"),
),
)
def test_register_validate_input(client, username, password, message):
response = client.post(
"/auth/register", data={"username": username, "password": password}
)
assert message in response.data
def test_login(client, auth):
assert client.get("/auth/login").status_code == 200
response = auth.login()
assert response.headers["location"] == "/"
with client:
client.get("/")
assert session["user_id"] == 1
assert g.user["username"] == "test"
@pytest.mark.parametrize(
("username", "password", "message"),
(("a", "test", b"incorrect username."), ("test", "a", b"incorrect password.")),
)
def test_login_validate_input(auth, username, password, message):
response = auth.login(username, password)
assert message in response.data
def test_logout(client, auth):
auth.login()
with client:
auth.logout()
assert "user_id" not in session