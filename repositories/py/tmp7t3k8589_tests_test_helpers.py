import io
import os
import pytest
import werkzeug.exceptions
import flask
from flask.helpers import get_debug_flag
class fakepath:
def __init__(self, path):
self.path = path
def __fspath__(self):
return self.path
class pybytesio:
def __init__(self, *args, **kwargs):
self._io = io.bytesio(*args, **kwargs)
def __getattr__(self, name):
return getattr(self._io, name)
class testsendfile:
def test_send_file(self, app, req_ctx):
rv = flask.send_file("static/index.html")
assert rv.direct_passthrough
assert rv.mimetype == "text/html"
with app.open_resource("static/index.html") as f:
rv.direct_passthrough = false
assert rv.data == f.read()
rv.close()
def test_static_file(self, app, req_ctx):
rv = app.send_static_file("index.html")
assert rv.cache_control.max_age is none
rv.close()
rv = flask.send_file("static/index.html")
assert rv.cache_control.max_age is none
rv.close()
app.config["send_file_max_age_default"] = 3600
rv = app.send_static_file("index.html")
assert rv.cache_control.max_age == 3600
rv.close()
rv = flask.send_file("static/index.html")
assert rv.cache_control.max_age == 3600
rv.close()
rv = app.send_static_file(fakepath("index.html"))
assert rv.cache_control.max_age == 3600
rv.close()
class staticfileapp(flask.flask):
def get_send_file_max_age(self, filename):
return 10
app = staticfileapp(__name__)
with app.test_request_context():
rv = app.send_static_file("index.html")
assert rv.cache_control.max_age == 10
rv.close()
rv = flask.send_file("static/index.html")
assert rv.cache_control.max_age == 10
rv.close()
def test_send_from_directory(self, app, req_ctx):
app.root_path = os.path.join(
os.path.dirname(__file__), "test_apps", "subdomaintestmodule"
)
rv = flask.send_from_directory("static", "hello.txt")
rv.direct_passthrough = false
assert rv.data.strip() == b"hello subdomain"
rv.close()
class testurlfor:
def test_url_for_with_anchor(self, app, req_ctx):
@app.route("/")
def index():
return "42"
assert flask.url_for("index", _anchor="x y") == "/
def test_url_for_with_scheme(self, app, req_ctx):
@app.route("/")
def index():
return "42"
assert (
flask.url_for("index", _external=true, _scheme="https")
== "https:
)
def test_url_for_with_scheme_not_external(self, app, req_ctx):
app.add_url_rule("/", endpoint="index")
url = flask.url_for("index", _scheme="https")
assert url == "https:
with pytest.raises(valueerror):
flask.url_for("index", _scheme="https", _external=false)
def test_url_for_with_alternating_schemes(self, app, req_ctx):
@app.route("/")
def index():
return "42"
assert flask.url_for("index", _external=true) == "http:
assert (
flask.url_for("index", _external=true, _scheme="https")
== "https:
)
assert flask.url_for("index", _external=true) == "http:
def test_url_with_method(self, app, req_ctx):
from flask.views import methodview
class myview(methodview):
def get(self, id=none):
if id is none:
return "list"
return f"get {id:d}"
def post(self):
return "create"
myview = myview.as_view("myview")
app.add_url_rule("/myview/", methods=["get"], view_func=myview)
app.add_url_rule("/myview/<int:id>", methods=["get"], view_func=myview)
app.add_url_rule("/myview/create", methods=["post"], view_func=myview)
assert flask.url_for("myview", _method="get") == "/myview/"
assert flask.url_for("myview", id=42, _method="get") == "/myview/42"
assert flask.url_for("myview", _method="post") == "/myview/create"
def test_url_for_with_self(self, app, req_ctx):
@app.route("/<self>")
def index(self):
return "42"
assert flask.url_for("index", self="2") == "/2"
def test_redirect_no_app():
response = flask.redirect("https:
assert response.location == "https:
assert response.status_code == 307
def test_redirect_with_app(app):
def redirect(location, code=302):
raise valueerror
app.redirect = redirect
with app.app_context(), pytest.raises(valueerror):
flask.redirect("other")
def test_abort_no_app():
with pytest.raises(werkzeug.exceptions.unauthorized):
flask.abort(401)
with pytest.raises(lookuperror):
flask.abort(900)
def test_app_aborter_class():
class myaborter(werkzeug.exceptions.aborter):
pass
class myflask(flask.flask):
aborter_class = myaborter
app = myflask(__name__)
assert isinstance(app.aborter, myaborter)
def test_abort_with_app(app):
class my900error(werkzeug.exceptions.httpexception):
code = 900
app.aborter.mapping[900] = my900error
with app.app_context(), pytest.raises(my900error):
flask.abort(900)
class testnoimports:
def test_name_with_import_error(self, modules_tmp_path):
(modules_tmp_path / "importerror.py").write_text("raise notimplementederror()")
try:
flask.flask("importerror")
except notimplementederror:
assertionerror("flask(import_name) is importing import_name.")
class teststreaming:
def test_streaming_with_context(self, app, client):
@app.route("/")
def index():
def generate():
yield "hello "
yield flask.request.args["name"]
yield "!"
return flask.response(flask.stream_with_context(generate()))
rv = client.get("/?name=world")
assert rv.data == b"hello world!"
def test_streaming_with_context_as_decorator(self, app, client):
@app.route("/")
def index():
@flask.stream_with_context
def generate(hello):
yield hello
yield flask.request.args["name"]
yield "!"
return flask.response(generate("hello "))
rv = client.get("/?name=world")
assert rv.data == b"hello world!"
def test_streaming_with_context_and_custom_close(self, app, client):
called = []
class wrapper:
def __init__(self, gen):
self._gen = gen
def __iter__(self):
return self
def close(self):
called.append(42)
def __next__(self):
return next(self._gen)
next = __next__
@app.route("/")
def index():
def generate():
yield "hello "
yield flask.request.args["name"]
yield "!"
return flask.response(flask.stream_with_context(wrapper(generate())))
rv = client.get("/?name=world")
assert rv.data == b"hello world!"
assert called == [42]
def test_stream_keeps_session(self, app, client):
@app.route("/")
def index():
flask.session["test"] = "flask"
@flask.stream_with_context
def gen():
yield flask.session["test"]
return flask.response(gen())
rv = client.get("/")
assert rv.data == b"flask"
class testhelpers:
@pytest.mark.parametrize(
("debug", "expect"),
[
("", false),
("0", false),
("false", false),
("no", false),
("true", true),
],
)
def test_get_debug_flag(self, monkeypatch, debug, expect):
monkeypatch.setenv("flask_debug", debug)
assert get_debug_flag() == expect
def test_make_response(self):
app = flask.flask(__name__)
with app.test_request_context():
rv = flask.helpers.make_response()
assert rv.status_code == 200
assert rv.mimetype == "text/html"
rv = flask.helpers.make_response("hello")
assert rv.status_code == 200
assert rv.data == b"hello"
assert rv.mimetype == "text/html"
@pytest.mark.parametrize("mode", ("r", "rb", "rt"))
def test_open_resource(mode):
app = flask.flask(__name__)
with app.open_resource("static/index.html", mode) as f:
assert "<h1>hello world!</h1>" in str(f.read())
@pytest.mark.parametrize("mode", ("w", "x", "a", "r+"))
def test_open_resource_exceptions(mode):
app = flask.flask(__name__)
with pytest.raises(valueerror):
app.open_resource("static/index.html", mode)
@pytest.mark.parametrize("encoding", ("utf-8", "utf-16-le"))
def test_open_resource_with_encoding(tmp_path, encoding):
app = flask.flask(__name__, root_path=os.fspath(tmp_path))
(tmp_path / "test").write_text("test", encoding=encoding)
with app.open_resource("test", mode="rt", encoding=encoding) as f:
assert f.read() == "test"