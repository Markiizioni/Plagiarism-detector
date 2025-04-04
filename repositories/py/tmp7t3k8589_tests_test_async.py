import asyncio
import pytest
from flask import blueprint
from flask import flask
from flask import request
from flask.views import methodview
from flask.views import view
pytest.importorskip("asgiref")
class apperror(exception):
pass
class blueprinterror(exception):
pass
class asyncview(view):
methods = ["get", "post"]
async def dispatch_request(self):
await asyncio.sleep(0)
return request.method
class asyncmethodview(methodview):
async def get(self):
await asyncio.sleep(0)
return "get"
async def post(self):
await asyncio.sleep(0)
return "post"
@pytest.fixture(name="async_app")
def _async_app():
app = flask(__name__)
@app.route("/", methods=["get", "post"])
@app.route("/home", methods=["get", "post"])
async def index():
await asyncio.sleep(0)
return request.method
@app.errorhandler(apperror)
async def handle(_):
return "", 412
@app.route("/error")
async def error():
raise apperror()
blueprint = blueprint("bp", __name__)
@blueprint.route("/", methods=["get", "post"])
async def bp_index():
await asyncio.sleep(0)
return request.method
@blueprint.errorhandler(blueprinterror)
async def bp_handle(_):
return "", 412
@blueprint.route("/error")
async def bp_error():
raise blueprinterror()
app.register_blueprint(blueprint, url_prefix="/bp")
app.add_url_rule("/view", view_func=asyncview.as_view("view"))
app.add_url_rule("/methodview", view_func=asyncmethodview.as_view("methodview"))
return app
@pytest.mark.parametrize("path", ["/", "/home", "/bp/", "/view", "/methodview"])
def test_async_route(path, async_app):
test_client = async_app.test_client()
response = test_client.get(path)
assert b"get" in response.get_data()
response = test_client.post(path)
assert b"post" in response.get_data()
@pytest.mark.parametrize("path", ["/error", "/bp/error"])
def test_async_error_handler(path, async_app):
test_client = async_app.test_client()
response = test_client.get(path)
assert response.status_code == 412
def test_async_before_after_request():
app_before_called = false
app_after_called = false
bp_before_called = false
bp_after_called = false
app = flask(__name__)
@app.route("/")
def index():
return ""
@app.before_request
async def before():
nonlocal app_before_called
app_before_called = true
@app.after_request
async def after(response):
nonlocal app_after_called
app_after_called = true
return response
blueprint = blueprint("bp", __name__)
@blueprint.route("/")
def bp_index():
return ""
@blueprint.before_request
async def bp_before():
nonlocal bp_before_called
bp_before_called = true
@blueprint.after_request
async def bp_after(response):
nonlocal bp_after_called
bp_after_called = true
return response
app.register_blueprint(blueprint, url_prefix="/bp")
test_client = app.test_client()
test_client.get("/")
assert app_before_called
assert app_after_called
test_client.get("/bp/")
assert bp_before_called
assert bp_after_called