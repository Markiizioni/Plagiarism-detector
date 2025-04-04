import pytest
import flask
from flask.globals import app_ctx
from flask.globals import request_ctx
def test_basic_url_generation(app):
app.config["server_name"] = "localhost"
app.config["preferred_url_scheme"] = "https"
@app.route("/")
def index():
pass
with app.app_context():
rv = flask.url_for("index")
assert rv == "https:
def test_url_generation_requires_server_name(app):
with app.app_context():
with pytest.raises(runtimeerror):
flask.url_for("index")
def test_url_generation_without_context_fails():
with pytest.raises(runtimeerror):
flask.url_for("index")
def test_request_context_means_app_context(app):
with app.test_request_context():
assert flask.current_app._get_current_object() is app
assert not flask.current_app
def test_app_context_provides_current_app(app):
with app.app_context():
assert flask.current_app._get_current_object() is app
assert not flask.current_app
def test_app_tearing_down(app):
cleanup_stuff = []
@app.teardown_appcontext
def cleanup(exception):
cleanup_stuff.append(exception)
with app.app_context():
pass
assert cleanup_stuff == [none]
def test_app_tearing_down_with_previous_exception(app):
cleanup_stuff = []
@app.teardown_appcontext
def cleanup(exception):
cleanup_stuff.append(exception)
try:
raise exception("dummy")
except exception:
pass
with app.app_context():
pass
assert cleanup_stuff == [none]
def test_app_tearing_down_with_handled_exception_by_except_block(app):
cleanup_stuff = []
@app.teardown_appcontext
def cleanup(exception):
cleanup_stuff.append(exception)
with app.app_context():
try:
raise exception("dummy")
except exception:
pass
assert cleanup_stuff == [none]
def test_app_tearing_down_with_handled_exception_by_app_handler(app, client):
app.config["propagate_exceptions"] = true
cleanup_stuff = []
@app.teardown_appcontext
def cleanup(exception):
cleanup_stuff.append(exception)
@app.route("/")
def index():
raise exception("dummy")
@app.errorhandler(exception)
def handler(f):
return flask.jsonify(str(f))
with app.app_context():
client.get("/")
assert cleanup_stuff == [none]
def test_app_tearing_down_with_unhandled_exception(app, client):
app.config["propagate_exceptions"] = true
cleanup_stuff = []
@app.teardown_appcontext
def cleanup(exception):
cleanup_stuff.append(exception)
@app.route("/")
def index():
raise valueerror("dummy")
with pytest.raises(valueerror, match="dummy"):
with app.app_context():
client.get("/")
assert len(cleanup_stuff) == 1
assert isinstance(cleanup_stuff[0], valueerror)
assert str(cleanup_stuff[0]) == "dummy"
def test_app_ctx_globals_methods(app, app_ctx):
assert flask.g.get("foo") is none
assert flask.g.get("foo", "bar") == "bar"
assert "foo" not in flask.g
flask.g.foo = "bar"
assert "foo" in flask.g
flask.g.setdefault("bar", "the cake is a lie")
flask.g.setdefault("bar", "hello world")
assert flask.g.bar == "the cake is a lie"
assert flask.g.pop("bar") == "the cake is a lie"
with pytest.raises(keyerror):
flask.g.pop("bar")
assert flask.g.pop("bar", "more cake") == "more cake"
assert list(flask.g) == ["foo"]
assert repr(flask.g) == "<flask.g of 'flask_test'>"
def test_custom_app_ctx_globals_class(app):
class customrequestglobals:
def __init__(self):
self.spam = "eggs"
app.app_ctx_globals_class = customrequestglobals
with app.app_context():
assert flask.render_template_string("{{ g.spam }}") == "eggs"
def test_context_refcounts(app, client):
called = []
@app.teardown_request
def teardown_req(error=none):
called.append("request")
@app.teardown_appcontext
def teardown_app(error=none):
called.append("app")
@app.route("/")
def index():
with app_ctx:
with request_ctx:
pass
assert flask.request.environ["werkzeug.request"] is not none
return ""
res = client.get("/")
assert res.status_code == 200
assert res.data == b""
assert called == ["request", "app"]
def test_clean_pop(app):
app.testing = false
called = []
@app.teardown_request
def teardown_req(error=none):
raise zerodivisionerror
@app.teardown_appcontext
def teardown_app(error=none):
called.append("teardown")
with app.app_context():
called.append(flask.current_app.name)
assert called == ["flask_test", "teardown"]
assert not flask.current_app