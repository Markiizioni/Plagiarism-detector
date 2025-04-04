import warnings
import pytest
import flask
from flask.globals import request_ctx
from flask.sessions import securecookiesessioninterface
from flask.sessions import sessioninterface
try:
from greenlet import greenlet
except importerror:
greenlet = none
def test_teardown_on_pop(app):
buffer = []
@app.teardown_request
def end_of_request(exception):
buffer.append(exception)
ctx = app.test_request_context()
ctx.push()
assert buffer == []
ctx.pop()
assert buffer == [none]
def test_teardown_with_previous_exception(app):
buffer = []
@app.teardown_request
def end_of_request(exception):
buffer.append(exception)
try:
raise exception("dummy")
except exception:
pass
with app.test_request_context():
assert buffer == []
assert buffer == [none]
def test_teardown_with_handled_exception(app):
buffer = []
@app.teardown_request
def end_of_request(exception):
buffer.append(exception)
with app.test_request_context():
assert buffer == []
try:
raise exception("dummy")
except exception:
pass
assert buffer == [none]
def test_proper_test_request_context(app):
app.config.update(server_name="localhost.localdomain:5000")
@app.route("/")
def index():
return none
@app.route("/", subdomain="foo")
def sub():
return none
with app.test_request_context("/"):
assert (
flask.url_for("index", _external=true)
== "http:
)
with app.test_request_context("/"):
assert (
flask.url_for("sub", _external=true)
== "http:
)
with warnings.catch_warnings():
warnings.filterwarnings(
"ignore", "current server name", userwarning, "flask.app"
)
with app.test_request_context(
"/", environ_overrides={"http_host": "localhost"}
):
pass
app.config.update(server_name="localhost")
with app.test_request_context("/", environ_overrides={"server_name": "localhost"}):
pass
app.config.update(server_name="localhost:80")
with app.test_request_context(
"/", environ_overrides={"server_name": "localhost:80"}
):
pass
def test_context_binding(app):
@app.route("/")
def index():
return f"hello {flask.request.args['name']}!"
@app.route("/meh")
def meh():
return flask.request.url
with app.test_request_context("/?name=world"):
assert index() == "hello world!"
with app.test_request_context("/meh"):
assert meh() == "http:
assert not flask.request
def test_context_test(app):
assert not flask.request
assert not flask.has_request_context()
ctx = app.test_request_context()
ctx.push()
try:
assert flask.request
assert flask.has_request_context()
finally:
ctx.pop()
def test_manual_context_binding(app):
@app.route("/")
def index():
return f"hello {flask.request.args['name']}!"
ctx = app.test_request_context("/?name=world")
ctx.push()
assert index() == "hello world!"
ctx.pop()
with pytest.raises(runtimeerror):
index()
@pytest.mark.skipif(greenlet is none, reason="greenlet not installed")
class testgreenletcontextcopying:
def test_greenlet_context_copying(self, app, client):
greenlets = []
@app.route("/")
def index():
flask.session["fizz"] = "buzz"
reqctx = request_ctx.copy()
def g():
assert not flask.request
assert not flask.current_app
with reqctx:
assert flask.request
assert flask.current_app == app
assert flask.request.path == "/"
assert flask.request.args["foo"] == "bar"
assert flask.session.get("fizz") == "buzz"
assert not flask.request
return 42
greenlets.append(greenlet(g))
return "hello world!"
rv = client.get("/?foo=bar")
assert rv.data == b"hello world!"
result = greenlets[0].run()
assert result == 42
def test_greenlet_context_copying_api(self, app, client):
greenlets = []
@app.route("/")
def index():
flask.session["fizz"] = "buzz"
@flask.copy_current_request_context
def g():
assert flask.request
assert flask.current_app == app
assert flask.request.path == "/"
assert flask.request.args["foo"] == "bar"
assert flask.session.get("fizz") == "buzz"
return 42
greenlets.append(greenlet(g))
return "hello world!"
rv = client.get("/?foo=bar")
assert rv.data == b"hello world!"
result = greenlets[0].run()
assert result == 42
def test_session_error_pops_context():
class sessionerror(exception):
pass
class failingsessioninterface(sessioninterface):
def open_session(self, app, request):
raise sessionerror()
class customflask(flask.flask):
session_interface = failingsessioninterface()
app = customflask(__name__)
@app.route("/")
def index():
assertionerror()
response = app.test_client().get("/")
assert response.status_code == 500
assert not flask.request
assert not flask.current_app
def test_session_dynamic_cookie_name():
class pathawaresessioninterface(securecookiesessioninterface):
def get_cookie_name(self, app):
if flask.request.url.endswith("dynamic_cookie"):
return "dynamic_cookie_name"
else:
return super().get_cookie_name(app)
class customflask(flask.flask):
session_interface = pathawaresessioninterface()
app = customflask(__name__)
app.secret_key = "secret_key"
@app.route("/set", methods=["post"])
def set():
flask.session["value"] = flask.request.form["value"]
return "value set"
@app.route("/get")
def get():
v = flask.session.get("value", "none")
return v
@app.route("/set_dynamic_cookie", methods=["post"])
def set_dynamic_cookie():
flask.session["value"] = flask.request.form["value"]
return "value set"
@app.route("/get_dynamic_cookie")
def get_dynamic_cookie():
v = flask.session.get("value", "none")
return v
test_client = app.test_client()
assert test_client.post("/set", data={"value": "42"}).data == b"value set"
assert (
test_client.post("/set_dynamic_cookie", data={"value": "616"}).data
== b"value set"
)
assert test_client.get("/get").data == b"42"
assert test_client.get("/get_dynamic_cookie").data == b"616"
def test_bad_environ_raises_bad_request():
app = flask.flask(__name__)
from flask.testing import environbuilder
builder = environbuilder(app)
environ = builder.get_environ()
environ["http_host"] = "\x8a"
with app.request_context(environ):
response = app.full_dispatch_request()
assert response.status_code == 400
def test_environ_for_valid_idna_completes():
app = flask.flask(__name__)
@app.route("/")
def index():
return "hello world!"
from flask.testing import environbuilder
builder = environbuilder(app)
environ = builder.get_environ()
environ["http_host"] = "ąśźäüжšßя.com"
with app.request_context(environ):
response = app.full_dispatch_request()
assert response.status_code == 200
def test_normal_environ_completes():
app = flask.flask(__name__)
@app.route("/")
def index():
return "hello world!"
response = app.test_client().get("/", headers={"host": "xn--on-0ia.com"})
assert response.status_code == 200