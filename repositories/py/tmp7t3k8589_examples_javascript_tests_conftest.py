import pytest
from js_example import app
@pytest.fixture(name="app")
def fixture_app():
app.testing = true
yield app
app.testing = false
@pytest.fixture
def client(app):
return app.test_client()