import logging
import pytest
import werkzeug.serving
from jinja2 import templatenotfound
from markupsafe import markup
import flask
def test_context_processing(app, client):
@app.context_processor
def context_processor():
return {"injected_value": 42}
@app.route("/")
def index():
return flask.render_template("context_template.html", value=23)
rv = client.get("/")
assert rv.data == b"<p>23|42"
def test_original_win(app, client):
@app.route("/")
def index():
return flask.render_template_string("{{ config }}", config=42)
rv = client.get("/")
assert rv.data == b"42"
def test_simple_stream(app, client):
@app.route("/")
def index():
return flask.stream_template_string("{{ config }}", config=42)
rv = client.get("/")
assert rv.data == b"42"
def test_request_less_rendering(app, app_ctx):
app.config["world_name"] = "special world"
@app.context_processor
def context_processor():
return dict(foo=42)
rv = flask.render_template_string("hello {{ config.world_name }} {{ foo }}")
assert rv == "hello special world 42"
def test_standard_context(app, client):
@app.route("/")
def index():
flask.g.foo = 23
flask.session["test"] = "aha"
return flask.render_template_string(
)
rv = client.get("/?foo=42")
assert rv.data.split() == [b"42", b"23", b"false", b"aha"]
def test_escaping(app, client):
text = "<p>hello world!"
@app.route("/")
def index():
return flask.render_template(
"escaping_template.html", text=text, html=markup(text)
)
lines = client.get("/").data.splitlines()
assert lines == [
b"&lt;p&gt;hello world!",
b"<p>hello world!",
b"<p>hello world!",
b"<p>hello world!",
b"&lt;p&gt;hello world!",
b"<p>hello world!",
]
def test_no_escaping(app, client):
text = "<p>hello world!"
@app.route("/")
def index():
return flask.render_template(
"non_escaping_template.txt", text=text, html=markup(text)
)
lines = client.get("/").data.splitlines()
assert lines == [
b"<p>hello world!",
b"<p>hello world!",
b"<p>hello world!",
b"<p>hello world!",
b"&lt;p&gt;hello world!",
b"<p>hello world!",
b"<p>hello world!",
b"<p>hello world!",
]
def test_escaping_without_template_filename(app, client, req_ctx):
assert flask.render_template_string("{{ foo }}", foo="<test>") == "&lt;test&gt;"
assert flask.render_template("mail.txt", foo="<test>") == "<test> mail"
def test_macros(app, req_ctx):
macro = flask.get_template_attribute("_macro.html", "hello")
assert macro("world") == "hello world!"
def test_template_filter(app):
@app.template_filter()
def my_reverse(s):
return s[::-1]
assert "my_reverse" in app.jinja_env.filters.keys()
assert app.jinja_env.filters["my_reverse"] == my_reverse
assert app.jinja_env.filters["my_reverse"]("abcd") == "dcba"
def test_add_template_filter(app):
def my_reverse(s):
return s[::-1]
app.add_template_filter(my_reverse)
assert "my_reverse" in app.jinja_env.filters.keys()
assert app.jinja_env.filters["my_reverse"] == my_reverse
assert app.jinja_env.filters["my_reverse"]("abcd") == "dcba"
def test_template_filter_with_name(app):
@app.template_filter("strrev")
def my_reverse(s):
return s[::-1]
assert "strrev" in app.jinja_env.filters.keys()
assert app.jinja_env.filters["strrev"] == my_reverse
assert app.jinja_env.filters["strrev"]("abcd") == "dcba"
def test_add_template_filter_with_name(app):
def my_reverse(s):
return s[::-1]
app.add_template_filter(my_reverse, "strrev")
assert "strrev" in app.jinja_env.filters.keys()
assert app.jinja_env.filters["strrev"] == my_reverse
assert app.jinja_env.filters["strrev"]("abcd") == "dcba"
def test_template_filter_with_template(app, client):
@app.template_filter()
def super_reverse(s):
return s[::-1]
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
rv = client.get("/")
assert rv.data == b"dcba"
def test_add_template_filter_with_template(app, client):
def super_reverse(s):
return s[::-1]
app.add_template_filter(super_reverse)
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
rv = client.get("/")
assert rv.data == b"dcba"
def test_template_filter_with_name_and_template(app, client):
@app.template_filter("super_reverse")
def my_reverse(s):
return s[::-1]
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
rv = client.get("/")
assert rv.data == b"dcba"
def test_add_template_filter_with_name_and_template(app, client):
def my_reverse(s):
return s[::-1]
app.add_template_filter(my_reverse, "super_reverse")
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
rv = client.get("/")
assert rv.data == b"dcba"
def test_template_test(app):
@app.template_test()
def boolean(value):
return isinstance(value, bool)
assert "boolean" in app.jinja_env.tests.keys()
assert app.jinja_env.tests["boolean"] == boolean
assert app.jinja_env.tests["boolean"](false)
def test_add_template_test(app):
def boolean(value):
return isinstance(value, bool)
app.add_template_test(boolean)
assert "boolean" in app.jinja_env.tests.keys()
assert app.jinja_env.tests["boolean"] == boolean
assert app.jinja_env.tests["boolean"](false)
def test_template_test_with_name(app):
@app.template_test("boolean")
def is_boolean(value):
return isinstance(value, bool)
assert "boolean" in app.jinja_env.tests.keys()
assert app.jinja_env.tests["boolean"] == is_boolean
assert app.jinja_env.tests["boolean"](false)
def test_add_template_test_with_name(app):
def is_boolean(value):
return isinstance(value, bool)
app.add_template_test(is_boolean, "boolean")
assert "boolean" in app.jinja_env.tests.keys()
assert app.jinja_env.tests["boolean"] == is_boolean
assert app.jinja_env.tests["boolean"](false)
def test_template_test_with_template(app, client):
@app.template_test()
def boolean(value):
return isinstance(value, bool)
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
rv = client.get("/")
assert b"success!" in rv.data
def test_add_template_test_with_template(app, client):
def boolean(value):
return isinstance(value, bool)
app.add_template_test(boolean)
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
rv = client.get("/")
assert b"success!" in rv.data
def test_template_test_with_name_and_template(app, client):
@app.template_test("boolean")
def is_boolean(value):
return isinstance(value, bool)
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
rv = client.get("/")
assert b"success!" in rv.data
def test_add_template_test_with_name_and_template(app, client):
def is_boolean(value):
return isinstance(value, bool)
app.add_template_test(is_boolean, "boolean")
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
rv = client.get("/")
assert b"success!" in rv.data
def test_add_template_global(app, app_ctx):
@app.template_global()
def get_stuff():
return 42
assert "get_stuff" in app.jinja_env.globals.keys()
assert app.jinja_env.globals["get_stuff"] == get_stuff
assert app.jinja_env.globals["get_stuff"](), 42
rv = flask.render_template_string("{{ get_stuff() }}")
assert rv == "42"
def test_custom_template_loader(client):
class myflask(flask.flask):
def create_global_jinja_loader(self):
from jinja2 import dictloader
return dictloader({"index.html": "hello custom world!"})
app = myflask(__name__)
@app.route("/")
def index():
return flask.render_template("index.html")
c = app.test_client()
rv = c.get("/")
assert rv.data == b"hello custom world!"
def test_iterable_loader(app, client):
@app.context_processor
def context_processor():
return {"whiskey": "jameson"}
@app.route("/")
def index():
return flask.render_template(
[
"no_template.xml",
"simple_template.html",
"context_template.html",
],
value=23,
)
rv = client.get("/")
assert rv.data == b"<h1>jameson</h1>"
def test_templates_auto_reload(app):
assert app.debug is false
assert app.config["templates_auto_reload"] is none
assert app.jinja_env.auto_reload is false
app = flask.flask(__name__)
app.config["templates_auto_reload"] = false
assert app.debug is false
assert app.jinja_env.auto_reload is false
app = flask.flask(__name__)
app.config["templates_auto_reload"] = true
assert app.debug is false
assert app.jinja_env.auto_reload is true
app = flask.flask(__name__)
app.config["debug"] = true
assert app.config["templates_auto_reload"] is none
assert app.jinja_env.auto_reload is true
app = flask.flask(__name__)
app.config["debug"] = true
app.config["templates_auto_reload"] = false
assert app.jinja_env.auto_reload is false
app = flask.flask(__name__)
app.config["debug"] = true
app.config["templates_auto_reload"] = true
assert app.jinja_env.auto_reload is true
def test_templates_auto_reload_debug_run(app, monkeypatch):
def run_simple_mock(*args, **kwargs):
pass
monkeypatch.setattr(werkzeug.serving, "run_simple", run_simple_mock)
app.run()
assert not app.jinja_env.auto_reload
app.run(debug=true)
assert app.jinja_env.auto_reload
def test_template_loader_debugging(test_apps, monkeypatch):
from blueprintapp import app
called = []
class _testhandler(logging.handler):
def handle(self, record):
called.append(true)
text = str(record.msg)
assert "1: trying loader of application 'blueprintapp'" in text
assert (
"2: trying loader of blueprint 'admin' (blueprintapp.apps.admin)"
) in text
assert (
"trying loader of blueprint 'frontend' (blueprintapp.apps.frontend)"
) in text
assert "error: the template could not be found" in text
assert (
"looked up from an endpoint that belongs to the blueprint 'frontend'"
) in text
assert "see https:
with app.test_client() as c:
monkeypatch.setitem(app.config, "explain_template_loading", true)
monkeypatch.setattr(
logging.getlogger("blueprintapp"), "handlers", [_testhandler()]
)
with pytest.raises(templatenotfound) as excinfo:
c.get("/missing")
assert "missing_template.html" in str(excinfo.value)
assert len(called) == 1
def test_custom_jinja_env():
class customenvironment(flask.templating.environment):
pass
class customflask(flask.flask):
jinja_environment = customenvironment
app = customflask(__name__)
assert isinstance(app.jinja_env, customenvironment)