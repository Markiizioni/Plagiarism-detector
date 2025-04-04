import importlib.metadata
import click
import pytest
import flask
from flask import appcontext_popped
from flask.cli import scriptinfo
from flask.globals import _cv_request
from flask.json import jsonify
from flask.testing import environbuilder
from flask.testing import flaskclirunner
def test_environ_defaults_from_config(app, client):
app.config["server_name"] = "example.com:1234"
app.config["application_root"] = "/foo"
@app.route("/")
def index():
return flask.request.url
ctx = app.test_request_context()
assert ctx.request.url == "http:
rv = client.get("/")
assert rv.data == b"http:
def test_environ_defaults(app, client, app_ctx, req_ctx):
@app.route("/")
def index():
return flask.request.url
ctx = app.test_request_context()
assert ctx.request.url == "http:
with client:
rv = client.get("/")
assert rv.data == b"http:
def test_environ_base_default(app, client):
@app.route("/")
def index():
flask.g.remote_addr = flask.request.remote_addr
flask.g.user_agent = flask.request.user_agent.string
return ""
with client:
client.get("/")
assert flask.g.remote_addr == "127.0.0.1"
assert flask.g.user_agent == (
f"werkzeug/{importlib.metadata.version('werkzeug')}"
)
def test_environ_base_modified(app, client):
@app.route("/")
def index():
flask.g.remote_addr = flask.request.remote_addr
flask.g.user_agent = flask.request.user_agent.string
return ""
client.environ_base["remote_addr"] = "192.168.0.22"
client.environ_base["http_user_agent"] = "foo"
with client:
client.get("/")
assert flask.g.remote_addr == "192.168.0.22"
assert flask.g.user_agent == "foo"
def test_client_open_environ(app, client, request):
@app.route("/index")
def index():
return flask.request.remote_addr
builder = environbuilder(app, path="/index", method="get")
request.addfinalizer(builder.close)
rv = client.open(builder)
assert rv.data == b"127.0.0.1"
environ = builder.get_environ()
client.environ_base["remote_addr"] = "127.0.0.2"
rv = client.open(environ)
assert rv.data == b"127.0.0.2"
def test_specify_url_scheme(app, client):
@app.route("/")
def index():
return flask.request.url
ctx = app.test_request_context(url_scheme="https")
assert ctx.request.url == "https:
rv = client.get("/", url_scheme="https")
assert rv.data == b"https:
def test_path_is_url(app):
eb = environbuilder(app, "https:
assert eb.url_scheme == "https"
assert eb.host == "example.com"
assert eb.script_root == ""
assert eb.path == "/"
def test_environbuilder_json_dumps(app):
app.json.ensure_ascii = false
eb = environbuilder(app, json="\u20ac")
assert eb.input_stream.read().decode("utf8") == '"\u20ac"'
def test_blueprint_with_subdomain():
app = flask.flask(__name__, subdomain_matching=true)
app.config["server_name"] = "example.com:1234"
app.config["application_root"] = "/foo"
client = app.test_client()
bp = flask.blueprint("company", __name__, subdomain="xxx")
@bp.route("/")
def index():
return flask.request.url
app.register_blueprint(bp)
ctx = app.test_request_context("/", subdomain="xxx")
assert ctx.request.url == "http:
with ctx:
assert ctx.request.blueprint == bp.name
rv = client.get("/", subdomain="xxx")
assert rv.data == b"http:
def test_redirect_keep_session(app, client, app_ctx):
@app.route("/", methods=["get", "post"])
def index():
if flask.request.method == "post":
return flask.redirect("/getsession")
flask.session["data"] = "foo"
return "index"
@app.route("/getsession")
def get_session():
return flask.session.get("data", "<missing>")
with client:
rv = client.get("/getsession")
assert rv.data == b"<missing>"
rv = client.get("/")
assert rv.data == b"index"
assert flask.session.get("data") == "foo"
rv = client.post("/", data={}, follow_redirects=true)
assert rv.data == b"foo"
assert flask.session.get("data") == "foo"
rv = client.get("/getsession")
assert rv.data == b"foo"
def test_session_transactions(app, client):
@app.route("/")
def index():
return str(flask.session["foo"])
with client:
with client.session_transaction() as sess:
assert len(sess) == 0
sess["foo"] = [42]
assert len(sess) == 1
rv = client.get("/")
assert rv.data == b"[42]"
with client.session_transaction() as sess:
assert len(sess) == 1
assert sess["foo"] == [42]
def test_session_transactions_no_null_sessions():
app = flask.flask(__name__)
with app.test_client() as c:
with pytest.raises(runtimeerror) as e:
with c.session_transaction():
pass
assert "session backend did not open a session" in str(e.value)
def test_session_transactions_keep_context(app, client, req_ctx):
client.get("/")
req = flask.request._get_current_object()
assert req is not none
with client.session_transaction():
assert req is flask.request._get_current_object()
def test_session_transaction_needs_cookies(app):
c = app.test_client(use_cookies=false)
with pytest.raises(typeerror, match="cookies are disabled."):
with c.session_transaction():
pass
def test_test_client_context_binding(app, client):
app.testing = false
@app.route("/")
def index():
flask.g.value = 42
return "hello world!"
@app.route("/other")
def other():
raise zerodivisionerror
with client:
resp = client.get("/")
assert flask.g.value == 42
assert resp.data == b"hello world!"
assert resp.status_code == 200
with client:
resp = client.get("/other")
assert not hasattr(flask.g, "value")
assert b"internal server error" in resp.data
assert resp.status_code == 500
flask.g.value = 23
with pytest.raises(runtimeerror):
flask.g.value
def test_reuse_client(client):
c = client
with c:
assert client.get("/").status_code == 404
with c:
assert client.get("/").status_code == 404
def test_full_url_request(app, client):
@app.route("/action", methods=["post"])
def action():
return "x"
with client:
rv = client.post("http:
assert rv.status_code == 200
assert "gin" in flask.request.form
assert "vodka" in flask.request.args
def test_json_request_and_response(app, client):
@app.route("/echo", methods=["post"])
def echo():
return jsonify(flask.request.get_json())
with client:
json_data = {"drink": {"gin": 1, "tonic": true}, "price": 10}
rv = client.post("/echo", json=json_data)
assert flask.request.is_json
assert flask.request.get_json() == json_data
assert rv.status_code == 200
assert rv.is_json
assert rv.get_json() == json_data
def test_client_json_no_app_context(app, client):
@app.route("/hello", methods=["post"])
def hello():
return f"hello, {flask.request.json['name']}!"
class namespace:
count = 0
def add(self, app):
self.count += 1
ns = namespace()
with appcontext_popped.connected_to(ns.add, app):
rv = client.post("/hello", json={"name": "flask"})
assert rv.get_data(as_text=true) == "hello, flask!"
assert ns.count == 1
def test_subdomain():
app = flask.flask(__name__, subdomain_matching=true)
app.config["server_name"] = "example.com"
client = app.test_client()
@app.route("/", subdomain="<company_id>")
def view(company_id):
return company_id
with app.test_request_context():
url = flask.url_for("view", company_id="xxx")
with client:
response = client.get(url)
assert 200 == response.status_code
assert b"xxx" == response.data
def test_nosubdomain(app, client):
app.config["server_name"] = "example.com"
@app.route("/<company_id>")
def view(company_id):
return company_id
with app.test_request_context():
url = flask.url_for("view", company_id="xxx")
with client:
response = client.get(url)
assert 200 == response.status_code
assert b"xxx" == response.data
def test_cli_runner_class(app):
runner = app.test_cli_runner()
assert isinstance(runner, flaskclirunner)
class subrunner(flaskclirunner):
pass
app.test_cli_runner_class = subrunner
runner = app.test_cli_runner()
assert isinstance(runner, subrunner)
def test_cli_invoke(app):
@app.cli.command("hello")
def hello_command():
click.echo("hello, world!")
runner = app.test_cli_runner()
result = runner.invoke(args=["hello"])
assert "hello" in result.output
result = runner.invoke(hello_command)
assert "hello" in result.output
def test_cli_custom_obj(app):
class ns:
called = false
def create_app():
ns.called = true
return app
@app.cli.command("hello")
def hello_command():
click.echo("hello, world!")
script_info = scriptinfo(create_app=create_app)
runner = app.test_cli_runner()
runner.invoke(hello_command, obj=script_info)
assert ns.called
def test_client_pop_all_preserved(app, req_ctx, client):
@app.route("/")
def index():
return flask.stream_with_context("hello")
with client:
rv = client.get("/")
rv.close()
assert _cv_request.get(none) is req_ctx