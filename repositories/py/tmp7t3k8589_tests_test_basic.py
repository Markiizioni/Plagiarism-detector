import gc
import re
import typing as t
import uuid
import warnings
import weakref
from contextlib import nullcontext
from datetime import datetime
from datetime import timezone
from platform import python_implementation
import pytest
import werkzeug.serving
from markupsafe import markup
from werkzeug.exceptions import badrequest
from werkzeug.exceptions import forbidden
from werkzeug.exceptions import notfound
from werkzeug.http import parse_date
from werkzeug.routing import builderror
from werkzeug.routing import requestredirect
import flask
require_cpython_gc = pytest.mark.skipif(
python_implementation() != "cpython",
reason="requires cpython gc behavior",
)
def test_options_work(app, client):
@app.route("/", methods=["get", "post"])
def index():
return "hello world"
rv = client.open("/", method="options")
assert sorted(rv.allow) == ["get", "head", "options", "post"]
assert rv.data == b""
def test_options_on_multiple_rules(app, client):
@app.route("/", methods=["get", "post"])
def index():
return "hello world"
@app.route("/", methods=["put"])
def index_put():
return "aha!"
rv = client.open("/", method="options")
assert sorted(rv.allow) == ["get", "head", "options", "post", "put"]
@pytest.mark.parametrize("method", ["get", "post", "put", "delete", "patch"])
def test_method_route(app, client, method):
method_route = getattr(app, method)
client_method = getattr(client, method)
@method_route("/")
def hello():
return "hello"
assert client_method("/").data == b"hello"
def test_method_route_no_methods(app):
with pytest.raises(typeerror):
app.get("/", methods=["get", "post"])
def test_provide_automatic_options_attr():
app = flask.flask(__name__)
def index():
return "hello world!"
index.provide_automatic_options = false
app.route("/")(index)
rv = app.test_client().open("/", method="options")
assert rv.status_code == 405
app = flask.flask(__name__)
def index2():
return "hello world!"
index2.provide_automatic_options = true
app.route("/", methods=["options"])(index2)
rv = app.test_client().open("/", method="options")
assert sorted(rv.allow) == ["options"]
def test_provide_automatic_options_kwarg(app, client):
def index():
return flask.request.method
def more():
return flask.request.method
app.add_url_rule("/", view_func=index, provide_automatic_options=false)
app.add_url_rule(
"/more",
view_func=more,
methods=["get", "post"],
provide_automatic_options=false,
)
assert client.get("/").data == b"get"
rv = client.post("/")
assert rv.status_code == 405
assert sorted(rv.allow) == ["get", "head"]
rv = client.open("/", method="options")
assert rv.status_code == 405
rv = client.head("/")
assert rv.status_code == 200
assert not rv.data
assert client.post("/more").data == b"post"
assert client.get("/more").data == b"get"
rv = client.delete("/more")
assert rv.status_code == 405
assert sorted(rv.allow) == ["get", "head", "post"]
rv = client.open("/more", method="options")
assert rv.status_code == 405
def test_request_dispatching(app, client):
@app.route("/")
def index():
return flask.request.method
@app.route("/more", methods=["get", "post"])
def more():
return flask.request.method
assert client.get("/").data == b"get"
rv = client.post("/")
assert rv.status_code == 405
assert sorted(rv.allow) == ["get", "head", "options"]
rv = client.head("/")
assert rv.status_code == 200
assert not rv.data
assert client.post("/more").data == b"post"
assert client.get("/more").data == b"get"
rv = client.delete("/more")
assert rv.status_code == 405
assert sorted(rv.allow) == ["get", "head", "options", "post"]
def test_disallow_string_for_allowed_methods(app):
with pytest.raises(typeerror):
app.add_url_rule("/", methods="get post", endpoint="test")
def test_url_mapping(app, client):
random_uuid4 = "7eb41166-9ebf-4d26-b771-ea3f54f8b383"
def index():
return flask.request.method
def more():
return flask.request.method
def options():
return random_uuid4
app.add_url_rule("/", "index", index)
app.add_url_rule("/more", "more", more, methods=["get", "post"])
app.add_url_rule("/options", "options", options, methods=["options"])
assert client.get("/").data == b"get"
rv = client.post("/")
assert rv.status_code == 405
assert sorted(rv.allow) == ["get", "head", "options"]
rv = client.head("/")
assert rv.status_code == 200
assert not rv.data
assert client.post("/more").data == b"post"
assert client.get("/more").data == b"get"
rv = client.delete("/more")
assert rv.status_code == 405
assert sorted(rv.allow) == ["get", "head", "options", "post"]
rv = client.open("/options", method="options")
assert rv.status_code == 200
assert random_uuid4 in rv.data.decode("utf-8")
def test_werkzeug_routing(app, client):
from werkzeug.routing import rule
from werkzeug.routing import submount
app.url_map.add(
submount("/foo", [rule("/bar", endpoint="bar"), rule("/", endpoint="index")])
)
def bar():
return "bar"
def index():
return "index"
app.view_functions["bar"] = bar
app.view_functions["index"] = index
assert client.get("/foo/").data == b"index"
assert client.get("/foo/bar").data == b"bar"
def test_endpoint_decorator(app, client):
from werkzeug.routing import rule
from werkzeug.routing import submount
app.url_map.add(
submount("/foo", [rule("/bar", endpoint="bar"), rule("/", endpoint="index")])
)
@app.endpoint("bar")
def bar():
return "bar"
@app.endpoint("index")
def index():
return "index"
assert client.get("/foo/").data == b"index"
assert client.get("/foo/bar").data == b"bar"
def test_session(app, client):
@app.route("/set", methods=["post"])
def set():
assert not flask.session.accessed
assert not flask.session.modified
flask.session["value"] = flask.request.form["value"]
assert flask.session.accessed
assert flask.session.modified
return "value set"
@app.route("/get")
def get():
assert not flask.session.accessed
assert not flask.session.modified
v = flask.session.get("value", "none")
assert flask.session.accessed
assert not flask.session.modified
return v
assert client.post("/set", data={"value": "42"}).data == b"value set"
assert client.get("/get").data == b"42"
def test_session_path(app, client):
app.config.update(application_root="/foo")
@app.route("/")
def index():
flask.session["testing"] = 42
return "hello world"
rv = client.get("/", "http:
assert "path=/foo" in rv.headers["set-cookie"].lower()
def test_session_using_application_root(app, client):
class prefixpathmiddleware:
def __init__(self, app, prefix):
self.app = app
self.prefix = prefix
def __call__(self, environ, start_response):
environ["script_name"] = self.prefix
return self.app(environ, start_response)
app.wsgi_app = prefixpathmiddleware(app.wsgi_app, "/bar")
app.config.update(application_root="/bar")
@app.route("/")
def index():
flask.session["testing"] = 42
return "hello world"
rv = client.get("/", "http:
assert "path=/bar" in rv.headers["set-cookie"].lower()
def test_session_using_session_settings(app, client):
app.config.update(
server_name="www.example.com:8080",
application_root="/test",
session_cookie_domain=".example.com",
session_cookie_httponly=false,
session_cookie_secure=true,
session_cookie_partitioned=true,
session_cookie_samesite="lax",
session_cookie_path="/",
)
@app.route("/")
def index():
flask.session["testing"] = 42
return "hello world"
@app.route("/clear")
def clear():
flask.session.pop("testing", none)
return "goodbye world"
rv = client.get("/", "http:
cookie = rv.headers["set-cookie"].lower()
assert "domain=example.com" in cookie or "domain=.example.com" in cookie
assert "path=/" in cookie
assert "secure" in cookie
assert "httponly" not in cookie
assert "samesite" in cookie
assert "partitioned" in cookie
rv = client.get("/clear", "http:
cookie = rv.headers["set-cookie"].lower()
assert "session=;" in cookie
assert "domain=example.com" in cookie or "domain=.example.com" in cookie
assert "path=/" in cookie
assert "secure" in cookie
assert "samesite" in cookie
assert "partitioned" in cookie
def test_session_using_samesite_attribute(app, client):
@app.route("/")
def index():
flask.session["testing"] = 42
return "hello world"
app.config.update(session_cookie_samesite="invalid")
with pytest.raises(valueerror):
client.get("/")
app.config.update(session_cookie_samesite=none)
rv = client.get("/")
cookie = rv.headers["set-cookie"].lower()
assert "samesite" not in cookie
app.config.update(session_cookie_samesite="strict")
rv = client.get("/")
cookie = rv.headers["set-cookie"].lower()
assert "samesite=strict" in cookie
app.config.update(session_cookie_samesite="lax")
rv = client.get("/")
cookie = rv.headers["set-cookie"].lower()
assert "samesite=lax" in cookie
def test_missing_session(app):
app.secret_key = none
def expect_exception(f, *args, **kwargs):
e = pytest.raises(runtimeerror, f, *args, **kwargs)
assert e.value.args and "session is unavailable" in e.value.args[0]
with app.test_request_context():
assert flask.session.get("missing_key") is none
expect_exception(flask.session.__setitem__, "foo", 42)
expect_exception(flask.session.pop, "foo")
def test_session_secret_key_fallbacks(app, client) -> none:
@app.post("/")
def set_session() -> str:
flask.session["a"] = 1
return ""
@app.get("/")
def get_session() -> dict[str, t.any]:
return dict(flask.session)
client.post()
assert client.get().json == {"a": 1}
app.secret_key = "new test key"
assert client.get().json == {}
app.config["secret_key_fallbacks"] = ["test key"]
assert client.get().json == {"a": 1}
def test_session_expiration(app, client):
permanent = true
@app.route("/")
def index():
flask.session["test"] = 42
flask.session.permanent = permanent
return ""
@app.route("/test")
def test():
return str(flask.session.permanent)
rv = client.get("/")
assert "set-cookie" in rv.headers
match = re.search(r"(?i)\bexpires=([^;]+)", rv.headers["set-cookie"])
expires = parse_date(match.group())
expected = datetime.now(timezone.utc) + app.permanent_session_lifetime
assert expires.year == expected.year
assert expires.month == expected.month
assert expires.day == expected.day
rv = client.get("/test")
assert rv.data == b"true"
permanent = false
rv = client.get("/")
assert "set-cookie" in rv.headers
match = re.search(r"\bexpires=([^;]+)", rv.headers["set-cookie"])
assert match is none
def test_session_stored_last(app, client):
@app.after_request
def modify_session(response):
flask.session["foo"] = 42
return response
@app.route("/")
def dump_session_contents():
return repr(flask.session.get("foo"))
assert client.get("/").data == b"none"
assert client.get("/").data == b"42"
def test_session_special_types(app, client):
now = datetime.now(timezone.utc).replace(microsecond=0)
the_uuid = uuid.uuid4()
@app.route("/")
def dump_session_contents():
flask.session["t"] = (1, 2, 3)
flask.session["b"] = b"\xff"
flask.session["m"] = markup("<html>")
flask.session["u"] = the_uuid
flask.session["d"] = now
flask.session["t_tag"] = {" t": "not-a-tuple"}
flask.session["di_t_tag"] = {" t__": "not-a-tuple"}
flask.session["di_tag"] = {" di": "not-a-dict"}
return "", 204
with client:
client.get("/")
s = flask.session
assert s["t"] == (1, 2, 3)
assert type(s["b"]) is bytes
assert s["b"] == b"\xff"
assert type(s["m"]) is markup
assert s["m"] == markup("<html>")
assert s["u"] == the_uuid
assert s["d"] == now
assert s["t_tag"] == {" t": "not-a-tuple"}
assert s["di_t_tag"] == {" t__": "not-a-tuple"}
assert s["di_tag"] == {" di": "not-a-dict"}
def test_session_cookie_setting(app):
is_permanent = true
@app.route("/bump")
def bump():
rv = flask.session["foo"] = flask.session.get("foo", 0) + 1
flask.session.permanent = is_permanent
return str(rv)
@app.route("/read")
def read():
return str(flask.session.get("foo", 0))
def run_test(expect_header):
with app.test_client() as c:
assert c.get("/bump").data == b"1"
assert c.get("/bump").data == b"2"
assert c.get("/bump").data == b"3"
rv = c.get("/read")
set_cookie = rv.headers.get("set-cookie")
assert (set_cookie is not none) == expect_header
assert rv.data == b"3"
is_permanent = true
app.config["session_refresh_each_request"] = true
run_test(expect_header=true)
is_permanent = true
app.config["session_refresh_each_request"] = false
run_test(expect_header=false)
is_permanent = false
app.config["session_refresh_each_request"] = true
run_test(expect_header=false)
is_permanent = false
app.config["session_refresh_each_request"] = false
run_test(expect_header=false)
def test_session_vary_cookie(app, client):
@app.route("/set")
def set_session():
flask.session["test"] = "test"
return ""
@app.route("/get")
def get():
return flask.session.get("test")
@app.route("/getitem")
def getitem():
return flask.session["test"]
@app.route("/setdefault")
def setdefault():
return flask.session.setdefault("test", "default")
@app.route("/clear")
def clear():
flask.session.clear()
return ""
@app.route("/vary-cookie-header-set")
def vary_cookie_header_set():
response = flask.response()
response.vary.add("cookie")
flask.session["test"] = "test"
return response
@app.route("/vary-header-set")
def vary_header_set():
response = flask.response()
response.vary.update(("accept-encoding", "accept-language"))
flask.session["test"] = "test"
return response
@app.route("/no-vary-header")
def no_vary_header():
return ""
def expect(path, header_value="cookie"):
rv = client.get(path)
if header_value:
assert len(rv.headers.get_all("vary")) == 1
assert rv.headers["vary"] == header_value
else:
assert "vary" not in rv.headers
expect("/set")
expect("/get")
expect("/getitem")
expect("/setdefault")
expect("/clear")
expect("/vary-cookie-header-set")
expect("/vary-header-set", "accept-encoding, accept-language, cookie")
expect("/no-vary-header", none)
def test_session_refresh_vary(app, client):
@app.get("/login")
def login():
flask.session["user_id"] = 1
flask.session.permanent = true
return ""
@app.get("/ignored")
def ignored():
return ""
rv = client.get("/login")
assert rv.headers["vary"] == "cookie"
rv = client.get("/ignored")
assert rv.headers["vary"] == "cookie"
def test_flashes(app, req_ctx):
assert not flask.session.modified
flask.flash("zap")
flask.session.modified = false
flask.flash("zip")
assert flask.session.modified
assert list(flask.get_flashed_messages()) == ["zap", "zip"]
def test_extended_flashing(app):
@app.route("/")
def index():
flask.flash("hello world")
flask.flash("hello world", "error")
flask.flash(markup("<em>testing</em>"), "warning")
return ""
@app.route("/test/")
def test():
messages = flask.get_flashed_messages()
assert list(messages) == [
"hello world",
"hello world",
markup("<em>testing</em>"),
]
return ""
@app.route("/test_with_categories/")
def test_with_categories():
messages = flask.get_flashed_messages(with_categories=true)
assert len(messages) == 3
assert list(messages) == [
("message", "hello world"),
("error", "hello world"),
("warning", markup("<em>testing</em>")),
]
return ""
@app.route("/test_filter/")
def test_filter():
messages = flask.get_flashed_messages(
category_filter=["message"], with_categories=true
)
assert list(messages) == [("message", "hello world")]
return ""
@app.route("/test_filters/")
def test_filters():
messages = flask.get_flashed_messages(
category_filter=["message", "warning"], with_categories=true
)
assert list(messages) == [
("message", "hello world"),
("warning", markup("<em>testing</em>")),
]
return ""
@app.route("/test_filters_without_returning_categories/")
def test_filters2():
messages = flask.get_flashed_messages(category_filter=["message", "warning"])
assert len(messages) == 2
assert messages[0] == "hello world"
assert messages[1] == markup("<em>testing</em>")
return ""
client = app.test_client()
client.get("/")
client.get("/test_with_categories/")
client = app.test_client()
client.get("/")
client.get("/test_filter/")
client = app.test_client()
client.get("/")
client.get("/test_filters/")
client = app.test_client()
client.get("/")
client.get("/test_filters_without_returning_categories/")
def test_request_processing(app, client):
evts = []
@app.before_request
def before_request():
evts.append("before")
@app.after_request
def after_request(response):
response.data += b"|after"
evts.append("after")
return response
@app.route("/")
def index():
assert "before" in evts
assert "after" not in evts
return "request"
assert "after" not in evts
rv = client.get("/").data
assert "after" in evts
assert rv == b"request|after"
def test_request_preprocessing_early_return(app, client):
evts = []
@app.before_request
def before_request1():
evts.append(1)
@app.before_request
def before_request2():
evts.append(2)
return "hello"
@app.before_request
def before_request3():
evts.append(3)
return "bye"
@app.route("/")
def index():
evts.append("index")
return "damnit"
rv = client.get("/").data.strip()
assert rv == b"hello"
assert evts == [1, 2]
def test_after_request_processing(app, client):
@app.route("/")
def index():
@flask.after_this_request
def foo(response):
response.headers["x-foo"] = "a header"
return response
return "test"
resp = client.get("/")
assert resp.status_code == 200
assert resp.headers["x-foo"] == "a header"
def test_teardown_request_handler(app, client):
called = []
@app.teardown_request
def teardown_request(exc):
called.append(true)
return "ignored"
@app.route("/")
def root():
return "response"
rv = client.get("/")
assert rv.status_code == 200
assert b"response" in rv.data
assert len(called) == 1
def test_teardown_request_handler_debug_mode(app, client):
called = []
@app.teardown_request
def teardown_request(exc):
called.append(true)
return "ignored"
@app.route("/")
def root():
return "response"
rv = client.get("/")
assert rv.status_code == 200
assert b"response" in rv.data
assert len(called) == 1
def test_teardown_request_handler_error(app, client):
called = []
app.testing = false
@app.teardown_request
def teardown_request1(exc):
assert type(exc) is zerodivisionerror
called.append(true)
try:
raise typeerror()
except exception:
pass
@app.teardown_request
def teardown_request2(exc):
assert type(exc) is zerodivisionerror
called.append(true)
try:
raise typeerror()
except exception:
pass
@app.route("/")
def fails():
raise zerodivisionerror
rv = client.get("/")
assert rv.status_code == 500
assert b"internal server error" in rv.data
assert len(called) == 2
def test_before_after_request_order(app, client):
called = []
@app.before_request
def before1():
called.append(1)
@app.before_request
def before2():
called.append(2)
@app.after_request
def after1(response):
called.append(4)
return response
@app.after_request
def after2(response):
called.append(3)
return response
@app.teardown_request
def finish1(exc):
called.append(6)
@app.teardown_request
def finish2(exc):
called.append(5)
@app.route("/")
def index():
return "42"
rv = client.get("/")
assert rv.data == b"42"
assert called == [1, 2, 3, 4, 5, 6]
def test_error_handling(app, client):
app.testing = false
@app.errorhandler(404)
def not_found(e):
return "not found", 404
@app.errorhandler(500)
def internal_server_error(e):
return "internal server error", 500
@app.errorhandler(forbidden)
def forbidden(e):
return "forbidden", 403
@app.route("/")
def index():
flask.abort(404)
@app.route("/error")
def error():
raise zerodivisionerror
@app.route("/forbidden")
def error2():
flask.abort(403)
rv = client.get("/")
assert rv.status_code == 404
assert rv.data == b"not found"
rv = client.get("/error")
assert rv.status_code == 500
assert b"internal server error" == rv.data
rv = client.get("/forbidden")
assert rv.status_code == 403
assert b"forbidden" == rv.data
def test_error_handling_processing(app, client):
app.testing = false
@app.errorhandler(500)
def internal_server_error(e):
return "internal server error", 500
@app.route("/")
def broken_func():
raise zerodivisionerror
@app.after_request
def after_request(resp):
resp.mimetype = "text/x-special"
return resp
resp = client.get("/")
assert resp.mimetype == "text/x-special"
assert resp.data == b"internal server error"
def test_baseexception_error_handling(app, client):
app.testing = false
@app.route("/")
def broken_func():
raise keyboardinterrupt()
with pytest.raises(keyboardinterrupt):
client.get("/")
def test_before_request_and_routing_errors(app, client):
@app.before_request
def attach_something():
flask.g.something = "value"
@app.errorhandler(404)
def return_something(error):
return flask.g.something, 404
rv = client.get("/")
assert rv.status_code == 404
assert rv.data == b"value"
def test_user_error_handling(app, client):
class myexception(exception):
pass
@app.errorhandler(myexception)
def handle_my_exception(e):
assert isinstance(e, myexception)
return "42"
@app.route("/")
def index():
raise myexception()
assert client.get("/").data == b"42"
def test_http_error_subclass_handling(app, client):
class forbiddensubclass(forbidden):
pass
@app.errorhandler(forbiddensubclass)
def handle_forbidden_subclass(e):
assert isinstance(e, forbiddensubclass)
return "banana"
@app.errorhandler(403)
def handle_403(e):
assert not isinstance(e, forbiddensubclass)
assert isinstance(e, forbidden)
return "apple"
@app.route("/1")
def index1():
raise forbiddensubclass()
@app.route("/2")
def index2():
flask.abort(403)
@app.route("/3")
def index3():
raise forbidden()
assert client.get("/1").data == b"banana"
assert client.get("/2").data == b"apple"
assert client.get("/3").data == b"apple"
def test_errorhandler_precedence(app, client):
class e1(exception):
pass
class e2(exception):
pass
class e3(e1, e2):
pass
@app.errorhandler(e2)
def handle_e2(e):
return "e2"
@app.errorhandler(exception)
def handle_exception(e):
return "exception"
@app.route("/e1")
def raise_e1():
raise e1
@app.route("/e3")
def raise_e3():
raise e3
rv = client.get("/e1")
assert rv.data == b"exception"
rv = client.get("/e3")
assert rv.data == b"e2"
@pytest.mark.parametrize(
("debug", "trap", "expect_key", "expect_abort"),
[(false, none, true, true), (true, none, false, true), (false, true, false, false)],
)
def test_trap_bad_request_key_error(app, client, debug, trap, expect_key, expect_abort):
app.config["debug"] = debug
app.config["trap_bad_request_errors"] = trap
@app.route("/key")
def fail():
flask.request.form["missing_key"]
@app.route("/abort")
def allow_abort():
flask.abort(400)
if expect_key:
rv = client.get("/key")
assert rv.status_code == 400
assert b"missing_key" not in rv.data
else:
with pytest.raises(keyerror) as exc_info:
client.get("/key")
assert exc_info.errisinstance(badrequest)
assert "missing_key" in exc_info.value.get_description()
if expect_abort:
rv = client.get("/abort")
assert rv.status_code == 400
else:
with pytest.raises(badrequest):
client.get("/abort")
def test_trapping_of_all_http_exceptions(app, client):
app.config["trap_http_exceptions"] = true
@app.route("/fail")
def fail():
flask.abort(404)
with pytest.raises(notfound):
client.get("/fail")
def test_error_handler_after_processor_error(app, client):
app.testing = false
@app.before_request
def before_request():
if _trigger == "before":
raise zerodivisionerror
@app.after_request
def after_request(response):
if _trigger == "after":
raise zerodivisionerror
return response
@app.route("/")
def index():
return "foo"
@app.errorhandler(500)
def internal_server_error(e):
return "hello server error", 500
for _trigger in "before", "after":
rv = client.get("/")
assert rv.status_code == 500
assert rv.data == b"hello server error"
def test_enctype_debug_helper(app, client):
from flask.debughelpers import debugfileskeyerror
app.debug = true
@app.route("/fail", methods=["post"])
def index():
return flask.request.files["foo"].filename
with pytest.raises(debugfileskeyerror) as e:
client.post("/fail", data={"foo": "index.txt"})
assert "no file contents were transmitted" in str(e.value)
assert "this was submitted: 'index.txt'" in str(e.value)
def test_response_types(app, client):
@app.route("/text")
def from_text():
return "hällo wörld"
@app.route("/bytes")
def from_bytes():
return "hällo wörld".encode()
@app.route("/full_tuple")
def from_full_tuple():
return (
"meh",
400,
{"x-foo": "testing", "content-type": "text/plain; charset=utf-8"},
)
@app.route("/text_headers")
def from_text_headers():
return "hello", {"x-foo": "test", "content-type": "text/plain; charset=utf-8"}
@app.route("/text_status")
def from_text_status():
return "hi, status!", 400
@app.route("/response_headers")
def from_response_headers():
return (
flask.response(
"hello world", 404, {"content-type": "text/html", "x-foo": "baz"}
),
{"content-type": "text/plain", "x-foo": "bar", "x-bar": "foo"},
)
@app.route("/response_status")
def from_response_status():
return app.response_class("hello world", 400), 500
@app.route("/wsgi")
def from_wsgi():
return notfound()
@app.route("/dict")
def from_dict():
return {"foo": "bar"}, 201
@app.route("/list")
def from_list():
return ["foo", "bar"], 201
assert client.get("/text").data == "hällo wörld".encode()
assert client.get("/bytes").data == "hällo wörld".encode()
rv = client.get("/full_tuple")
assert rv.data == b"meh"
assert rv.headers["x-foo"] == "testing"
assert rv.status_code == 400
assert rv.mimetype == "text/plain"
rv = client.get("/text_headers")
assert rv.data == b"hello"
assert rv.headers["x-foo"] == "test"
assert rv.status_code == 200
assert rv.mimetype == "text/plain"
rv = client.get("/text_status")
assert rv.data == b"hi, status!"
assert rv.status_code == 400
assert rv.mimetype == "text/html"
rv = client.get("/response_headers")
assert rv.data == b"hello world"
assert rv.content_type == "text/plain"
assert rv.headers.getlist("x-foo") == ["bar"]
assert rv.headers["x-bar"] == "foo"
assert rv.status_code == 404
rv = client.get("/response_status")
assert rv.data == b"hello world"
assert rv.status_code == 500
rv = client.get("/wsgi")
assert b"not found" in rv.data
assert rv.status_code == 404
rv = client.get("/dict")
assert rv.json == {"foo": "bar"}
assert rv.status_code == 201
rv = client.get("/list")
assert rv.json == ["foo", "bar"]
assert rv.status_code == 201
def test_response_type_errors():
app = flask.flask(__name__)
app.testing = true
@app.route("/none")
def from_none():
pass
@app.route("/small_tuple")
def from_small_tuple():
return ("hello",)
@app.route("/large_tuple")
def from_large_tuple():
return "hello", 234, {"x-foo": "bar"}, "???"
@app.route("/bad_type")
def from_bad_type():
return true
@app.route("/bad_wsgi")
def from_bad_wsgi():
return lambda: none
c = app.test_client()
with pytest.raises(typeerror) as e:
c.get("/none")
assert "returned none" in str(e.value)
assert "from_none" in str(e.value)
with pytest.raises(typeerror) as e:
c.get("/small_tuple")
assert "tuple must have the form" in str(e.value)
with pytest.raises(typeerror):
c.get("/large_tuple")
with pytest.raises(typeerror) as e:
c.get("/bad_type")
assert "it was a bool" in str(e.value)
with pytest.raises(typeerror):
c.get("/bad_wsgi")
def test_make_response(app, req_ctx):
rv = flask.make_response()
assert rv.status_code == 200
assert rv.data == b""
assert rv.mimetype == "text/html"
rv = flask.make_response("awesome")
assert rv.status_code == 200
assert rv.data == b"awesome"
assert rv.mimetype == "text/html"
rv = flask.make_response("w00t", 404)
assert rv.status_code == 404
assert rv.data == b"w00t"
assert rv.mimetype == "text/html"
rv = flask.make_response(c for c in "hello")
assert rv.status_code == 200
assert rv.data == b"hello"
assert rv.mimetype == "text/html"
def test_make_response_with_response_instance(app, req_ctx):
rv = flask.make_response(flask.jsonify({"msg": "w00t"}), 400)
assert rv.status_code == 400
assert rv.data == b'{"msg":"w00t"}\n'
assert rv.mimetype == "application/json"
rv = flask.make_response(flask.response(""), 400)
assert rv.status_code == 400
assert rv.data == b""
assert rv.mimetype == "text/html"
rv = flask.make_response(
flask.response("", headers={"content-type": "text/html"}),
400,
[("x-foo", "bar")],
)
assert rv.status_code == 400
assert rv.headers["content-type"] == "text/html"
assert rv.headers["x-foo"] == "bar"
@pytest.mark.parametrize("compact", [true, false])
def test_jsonify_no_prettyprint(app, compact):
app.json.compact = compact
rv = app.json.response({"msg": {"submsg": "w00t"}, "msg2": "foobar"})
data = rv.data.strip()
assert (b" " not in data) is compact
assert (b"\n" not in data) is compact
def test_jsonify_mimetype(app, req_ctx):
app.json.mimetype = "application/vnd.api+json"
msg = {"msg": {"submsg": "w00t"}}
rv = flask.make_response(flask.jsonify(msg), 200)
assert rv.mimetype == "application/vnd.api+json"
def test_json_dump_dataclass(app, req_ctx):
from dataclasses import make_dataclass
data = make_dataclass("data", [("name", str)])
value = app.json.dumps(data("flask"))
value = app.json.loads(value)
assert value == {"name": "flask"}
def test_jsonify_args_and_kwargs_check(app, req_ctx):
with pytest.raises(typeerror) as e:
flask.jsonify("fake args", kwargs="fake")
assert "args or kwargs" in str(e.value)
def test_url_generation(app, req_ctx):
@app.route("/hello/<name>", methods=["post"])
def hello():
pass
assert flask.url_for("hello", name="test x") == "/hello/test%20x"
assert (
flask.url_for("hello", name="test x", _external=true)
== "http:
)
def test_build_error_handler(app):
with app.test_request_context():
pytest.raises(builderror, flask.url_for, "spam")
try:
with app.test_request_context():
flask.url_for("spam")
except builderror as err:
error = err
try:
raise runtimeerror("test case where builderror is not current.")
except runtimeerror:
pytest.raises(builderror, app.handle_url_build_error, error, "spam", {})
def handler(error, endpoint, values):
return "/test_handler/"
app.url_build_error_handlers.append(handler)
with app.test_request_context():
assert flask.url_for("spam") == "/test_handler/"
def test_build_error_handler_reraise(app):
def handler_raises_build_error(error, endpoint, values):
raise error
app.url_build_error_handlers.append(handler_raises_build_error)
with app.test_request_context():
pytest.raises(builderror, flask.url_for, "not.existing")
def test_url_for_passes_special_values_to_build_error_handler(app):
@app.url_build_error_handlers.append
def handler(error, endpoint, values):
assert values == {
"_external": false,
"_anchor": none,
"_method": none,
"_scheme": none,
}
return "handled"
with app.test_request_context():
flask.url_for("/")
def test_static_files(app, client):
rv = client.get("/static/index.html")
assert rv.status_code == 200
assert rv.data.strip() == b"<h1>hello world!</h1>"
with app.test_request_context():
assert flask.url_for("static", filename="index.html") == "/static/index.html"
rv.close()
def test_static_url_path():
app = flask.flask(__name__, static_url_path="/foo")
app.testing = true
rv = app.test_client().get("/foo/index.html")
assert rv.status_code == 200
rv.close()
with app.test_request_context():
assert flask.url_for("static", filename="index.html") == "/foo/index.html"
def test_static_url_path_with_ending_slash():
app = flask.flask(__name__, static_url_path="/foo/")
app.testing = true
rv = app.test_client().get("/foo/index.html")
assert rv.status_code == 200
rv.close()
with app.test_request_context():
assert flask.url_for("static", filename="index.html") == "/foo/index.html"
def test_static_url_empty_path(app):
app = flask.flask(__name__, static_folder="", static_url_path="")
rv = app.test_client().open("/static/index.html", method="get")
assert rv.status_code == 200
rv.close()
def test_static_url_empty_path_default(app):
app = flask.flask(__name__, static_folder="")
rv = app.test_client().open("/static/index.html", method="get")
assert rv.status_code == 200
rv.close()
def test_static_folder_with_pathlib_path(app):
from pathlib import path
app = flask.flask(__name__, static_folder=path("static"))
rv = app.test_client().open("/static/index.html", method="get")
assert rv.status_code == 200
rv.close()
def test_static_folder_with_ending_slash():
app = flask.flask(__name__, static_folder="static/")
@app.route("/<path:path>")
def catch_all(path):
return path
rv = app.test_client().get("/catch/all")
assert rv.data == b"catch/all"
def test_static_route_with_host_matching():
app = flask.flask(__name__, host_matching=true, static_host="example.com")
c = app.test_client()
rv = c.get("http:
assert rv.status_code == 200
rv.close()
with app.test_request_context():
rv = flask.url_for("static", filename="index.html", _external=true)
assert rv == "http:
with pytest.raises(assertionerror):
flask.flask(__name__, static_host="example.com")
with pytest.raises(assertionerror):
flask.flask(__name__, host_matching=true)
flask.flask(__name__, host_matching=true, static_folder=none)
def test_request_locals():
assert repr(flask.g) == "<localproxy unbound>"
assert not flask.g
@pytest.mark.parametrize(
("subdomain_matching", "host_matching", "expect_base", "expect_abc", "expect_xyz"),
[
(false, false, "default", "default", "default"),
(true, false, "default", "abc", "<invalid>"),
(false, true, "default", "abc", "default"),
],
)
def test_server_name_matching(
subdomain_matching: bool,
host_matching: bool,
expect_base: str,
expect_abc: str,
expect_xyz: str,
) -> none:
app = flask.flask(
__name__,
subdomain_matching=subdomain_matching,
host_matching=host_matching,
static_host="example.test" if host_matching else none,
)
app.config["server_name"] = "example.test"
@app.route("/", defaults={"name": "default"}, host="<name>")
@app.route("/", subdomain="<name>", host="<name>.example.test")
def index(name: str) -> str:
return name
client = app.test_client()
r = client.get(base_url="http:
assert r.text == expect_base
r = client.get(base_url="http:
assert r.text == expect_abc
with pytest.warns() if subdomain_matching else nullcontext():
r = client.get(base_url="http:
assert r.text == expect_xyz
def test_server_name_subdomain():
app = flask.flask(__name__, subdomain_matching=true)
client = app.test_client()
@app.route("/")
def index():
return "default"
@app.route("/", subdomain="foo")
def subdomain():
return "subdomain"
app.config["server_name"] = "dev.local:5000"
rv = client.get("/")
assert rv.data == b"default"
rv = client.get("/", "http:
assert rv.data == b"default"
rv = client.get("/", "https:
assert rv.data == b"default"
app.config["server_name"] = "dev.local:443"
rv = client.get("/", "https:
if rv.status_code != 404:
assert rv.data == b"default"
app.config["server_name"] = "dev.local"
rv = client.get("/", "https:
assert rv.data == b"default"
with warnings.catch_warnings():
warnings.filterwarnings(
"ignore", "current server name", userwarning, "flask.app"
)
rv = client.get("/", "http:
assert rv.status_code == 404
rv = client.get("/", "http:
assert rv.data == b"subdomain"
@pytest.mark.parametrize("key", ["testing", "propagate_exceptions", "debug", none])
def test_exception_propagation(app, client, key):
app.testing = false
@app.route("/")
def index():
raise zerodivisionerror
if key is not none:
app.config[key] = true
with pytest.raises(zerodivisionerror):
client.get("/")
else:
assert client.get("/").status_code == 500
@pytest.mark.parametrize("debug", [true, false])
@pytest.mark.parametrize("use_debugger", [true, false])
@pytest.mark.parametrize("use_reloader", [true, false])
@pytest.mark.parametrize("propagate_exceptions", [none, true, false])
def test_werkzeug_passthrough_errors(
monkeypatch, debug, use_debugger, use_reloader, propagate_exceptions, app
):
rv = {}
def run_simple_mock(*args, **kwargs):
rv["passthrough_errors"] = kwargs.get("passthrough_errors")
monkeypatch.setattr(werkzeug.serving, "run_simple", run_simple_mock)
app.config["propagate_exceptions"] = propagate_exceptions
app.run(debug=debug, use_debugger=use_debugger, use_reloader=use_reloader)
def test_url_processors(app, client):
@app.url_defaults
def add_language_code(endpoint, values):
if flask.g.lang_code is not none and app.url_map.is_endpoint_expecting(
endpoint, "lang_code"
):
values.setdefault("lang_code", flask.g.lang_code)
@app.url_value_preprocessor
def pull_lang_code(endpoint, values):
flask.g.lang_code = values.pop("lang_code", none)
@app.route("/<lang_code>/")
def index():
return flask.url_for("about")
@app.route("/<lang_code>/about")
def about():
return flask.url_for("something_else")
@app.route("/foo")
def something_else():
return flask.url_for("about", lang_code="en")
assert client.get("/de/").data == b"/de/about"
assert client.get("/de/about").data == b"/foo"
assert client.get("/foo").data == b"/en/about"
def test_inject_blueprint_url_defaults(app):
bp = flask.blueprint("foo", __name__, template_folder="template")
@bp.url_defaults
def bp_defaults(endpoint, values):
values["page"] = "login"
@bp.route("/<page>")
def view(page):
pass
app.register_blueprint(bp)
values = dict()
app.inject_url_defaults("foo.view", values)
expected = dict(page="login")
assert values == expected
with app.test_request_context("/somepage"):
url = flask.url_for("foo.view")
expected = "/login"
assert url == expected
def test_nonascii_pathinfo(app, client):
@app.route("/киртест")
def index():
return "hello world!"
rv = client.get("/киртест")
assert rv.data == b"hello world!"
def test_no_setup_after_first_request(app, client):
app.debug = true
@app.route("/")
def index():
return "awesome"
assert client.get("/").data == b"awesome"
with pytest.raises(assertionerror) as exc_info:
app.add_url_rule("/foo", endpoint="late")
assert "setup method 'add_url_rule'" in str(exc_info.value)
def test_routing_redirect_debugging(monkeypatch, app, client):
app.config["debug"] = true
@app.route("/user/", methods=["get", "post"])
def user():
return flask.request.form["status"]
rv = client.post("/user", data={"status": "success"}, follow_redirects=true)
assert rv.data == b"success"
monkeypatch.setattr(requestredirect, "code", 301)
with client, pytest.raises(assertionerror) as exc_info:
client.post("/user", data={"status": "error"}, follow_redirects=true)
assert "canonical url 'http:
def test_route_decorator_custom_endpoint(app, client):
app.debug = true
@app.route("/foo/")
def foo():
return flask.request.endpoint
@app.route("/bar/", endpoint="bar")
def for_bar():
return flask.request.endpoint
@app.route("/bar/123", endpoint="123")
def for_bar_foo():
return flask.request.endpoint
with app.test_request_context():
assert flask.url_for("foo") == "/foo/"
assert flask.url_for("bar") == "/bar/"
assert flask.url_for("123") == "/bar/123"
assert client.get("/foo/").data == b"foo"
assert client.get("/bar/").data == b"bar"
assert client.get("/bar/123").data == b"123"
def test_get_method_on_g(app_ctx):
assert flask.g.get("x") is none
assert flask.g.get("x", 11) == 11
flask.g.x = 42
assert flask.g.get("x") == 42
assert flask.g.x == 42
def test_g_iteration_protocol(app_ctx):
flask.g.foo = 23
flask.g.bar = 42
assert "foo" in flask.g
assert "foos" not in flask.g
assert sorted(flask.g) == ["bar", "foo"]
def test_subdomain_basic_support():
app = flask.flask(__name__, subdomain_matching=true)
app.config["server_name"] = "localhost.localdomain"
client = app.test_client()
@app.route("/")
def normal_index():
return "normal index"
@app.route("/", subdomain="test")
def test_index():
return "test index"
rv = client.get("/", "http:
assert rv.data == b"normal index"
rv = client.get("/", "http:
assert rv.data == b"test index"
def test_subdomain_matching():
app = flask.flask(__name__, subdomain_matching=true)
client = app.test_client()
app.config["server_name"] = "localhost.localdomain"
@app.route("/", subdomain="<user>")
def index(user):
return f"index for {user}"
rv = client.get("/", "http:
assert rv.data == b"index for mitsuhiko"
def test_subdomain_matching_with_ports():
app = flask.flask(__name__, subdomain_matching=true)
app.config["server_name"] = "localhost.localdomain:3000"
client = app.test_client()
@app.route("/", subdomain="<user>")
def index(user):
return f"index for {user}"
rv = client.get("/", "http:
assert rv.data == b"index for mitsuhiko"
@pytest.mark.parametrize("matching", (false, true))
def test_subdomain_matching_other_name(matching):
app = flask.flask(__name__, subdomain_matching=matching)
app.config["server_name"] = "localhost.localdomain:3000"
client = app.test_client()
@app.route("/")
def index():
return "", 204
with warnings.catch_warnings():
warnings.filterwarnings(
"ignore", "current server name", userwarning, "flask.app"
)
rv = client.get("/", "http:
assert rv.status_code == 404 if matching else 204
rv = client.get("/", "http:
assert rv.status_code == 404 if matching else 204
def test_multi_route_rules(app, client):
@app.route("/")
@app.route("/<test>/")
def index(test="a"):
return test
rv = client.open("/")
assert rv.data == b"a"
rv = client.open("/b/")
assert rv.data == b"b"
def test_multi_route_class_views(app, client):
class view:
def __init__(self, app):
app.add_url_rule("/", "index", self.index)
app.add_url_rule("/<test>/", "index", self.index)
def index(self, test="a"):
return test
_ = view(app)
rv = client.open("/")
assert rv.data == b"a"
rv = client.open("/b/")
assert rv.data == b"b"
def test_run_defaults(monkeypatch, app):
rv = {}
def run_simple_mock(*args, **kwargs):
rv["result"] = "running..."
monkeypatch.setattr(werkzeug.serving, "run_simple", run_simple_mock)
app.run()
assert rv["result"] == "running..."
def test_run_server_port(monkeypatch, app):
rv = {}
def run_simple_mock(hostname, port, application, *args, **kwargs):
rv["result"] = f"running on {hostname}:{port} ..."
monkeypatch.setattr(werkzeug.serving, "run_simple", run_simple_mock)
hostname, port = "localhost", 8000
app.run(hostname, port, debug=true)
assert rv["result"] == f"running on {hostname}:{port} ..."
@pytest.mark.parametrize(
"host,port,server_name,expect_host,expect_port",
(
(none, none, "pocoo.org:8080", "pocoo.org", 8080),
("localhost", none, "pocoo.org:8080", "localhost", 8080),
(none, 80, "pocoo.org:8080", "pocoo.org", 80),
("localhost", 80, "pocoo.org:8080", "localhost", 80),
("localhost", 0, "localhost:8080", "localhost", 0),
(none, none, "localhost:8080", "localhost", 8080),
(none, none, "localhost:0", "localhost", 0),
),
)
def test_run_from_config(
monkeypatch, host, port, server_name, expect_host, expect_port, app
):
def run_simple_mock(hostname, port, *args, **kwargs):
assert hostname == expect_host
assert port == expect_port
monkeypatch.setattr(werkzeug.serving, "run_simple", run_simple_mock)
app.config["server_name"] = server_name
app.run(host, port)
def test_max_cookie_size(app, client, recwarn):
app.config["max_cookie_size"] = 100
response = flask.response()
default = flask.flask.default_config["max_cookie_size"]
assert response.max_cookie_size == default
with app.app_context():
assert flask.response().max_cookie_size == 100
@app.route("/")
def index():
r = flask.response("", status=204)
r.set_cookie("foo", "bar" * 100)
return r
client.get("/")
assert len(recwarn) == 1
w = recwarn.pop()
assert "cookie is too large" in str(w.message)
app.config["max_cookie_size"] = 0
client.get("/")
assert len(recwarn) == 0
@require_cpython_gc
def test_app_freed_on_zero_refcount():
gc.disable()
try:
app = flask.flask(__name__)
assert app.view_functions["static"]
weak = weakref.ref(app)
assert weak() is not none
del app
assert weak() is none
finally:
gc.enable()