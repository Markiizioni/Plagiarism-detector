from flaskr import create_app
def test_config():
assert not create_app().testing
assert create_app({"testing": true}).testing
def test_hello(client):
response = client.get("/hello")
assert response.data == b"hello, world!"