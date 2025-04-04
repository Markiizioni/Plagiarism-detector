import pytest
from jinja2 import templatenotfound
from werkzeug.http import parse_cache_control_header
import flask
def test_blueprint_specific_error_handling(app, client):
frontend = flask.blueprint("frontend", __name__)
backend = flask.blueprint("backend", __name__)
sideend = flask.blueprint("sideend", __name__)
@frontend.errorhandler(403)
def frontend_forbidden(e):
return "frontend says no", 403
@frontend.route("/frontend-no")
def frontend_no():
flask.abort(403)
@backend.errorhandler(403)
def backend_forbidden(e):
return "backend says no", 403
@backend.route("/backend-no")
def backend_no():
flask.abort(403)
@sideend.route("/what-is-a-sideend")
def sideend_no():
flask.abort(403)
app.register_blueprint(frontend)
app.register_blueprint(backend)
app.register_blueprint(sideend)
@app.errorhandler(403)
def app_forbidden(e):
return "application itself says no", 403
assert client.get("/frontend-no").data == b"frontend says no"
assert client.get("/backend-no").data == b"backend says no"
assert client.get("/what-is-a-sideend").data == b"application itself says no"
def test_blueprint_specific_user_error_handling(app, client):
class mydecoratorexception(exception):
pass
class myfunctionexception(exception):
pass
blue = flask.blueprint("blue", __name__)
@blue.errorhandler(mydecoratorexception)
def my_decorator_exception_handler(e):
assert isinstance(e, mydecoratorexception)
return "boom"
def my_function_exception_handler(e):
assert isinstance(e, myfunctionexception)
return "bam"
blue.register_error_handler(myfunctionexception, my_function_exception_handler)
@blue.route("/decorator")
def blue_deco_test():
raise mydecoratorexception()
@blue.route("/function")
def blue_func_test():
raise myfunctionexception()
app.register_blueprint(blue)
assert client.get("/decorator").data == b"boom"
assert client.get("/function").data == b"bam"
def test_blueprint_app_error_handling(app, client):
errors = flask.blueprint("errors", __name__)
@errors.app_errorhandler(403)
def forbidden_handler(e):
return "you shall not pass", 403
@app.route("/forbidden")
def app_forbidden():
flask.abort(403)
forbidden_bp = flask.blueprint("forbidden_bp", __name__)
@forbidden_bp.route("/nope")
def bp_forbidden():
flask.abort(403)
app.register_blueprint(errors)
app.register_blueprint(forbidden_bp)
assert client.get("/forbidden").data == b"you shall not pass"
assert client.get("/nope").data == b"you shall not pass"
@pytest.mark.parametrize(
("prefix", "rule", "url"),
(
("", "/", "/"),
("/", "", "/"),
("/", "/", "/"),
("/foo", "", "/foo"),
("/foo/", "", "/foo/"),
("", "/bar", "/bar"),
("/foo/", "/bar", "/foo/bar"),
("/foo/", "bar", "/foo/bar"),
("/foo", "/bar", "/foo/bar"),
("/foo/", "
("/foo
),
)
def test_blueprint_prefix_slash(app, client, prefix, rule, url):
bp = flask.blueprint("test", __name__, url_prefix=prefix)
@bp.route(rule)
def index():
return "", 204
app.register_blueprint(bp)
assert client.get(url).status_code == 204
def test_blueprint_url_defaults(app, client):
bp = flask.blueprint("test", __name__)
@bp.route("/foo", defaults={"baz": 42})
def foo(bar, baz):
return f"{bar}/{baz:d}"
@bp.route("/bar")
def bar(bar):
return str(bar)
app.register_blueprint(bp, url_prefix="/1", url_defaults={"bar": 23})
app.register_blueprint(bp, name="test2", url_prefix="/2", url_defaults={"bar": 19})
assert client.get("/1/foo").data == b"23/42"
assert client.get("/2/foo").data == b"19/42"
assert client.get("/1/bar").data == b"23"
assert client.get("/2/bar").data == b"19"
def test_blueprint_url_processors(app, client):
bp = flask.blueprint("frontend", __name__, url_prefix="/<lang_code>")
@bp.url_defaults
def add_language_code(endpoint, values):
values.setdefault("lang_code", flask.g.lang_code)
@bp.url_value_preprocessor
def pull_lang_code(endpoint, values):
flask.g.lang_code = values.pop("lang_code")
@bp.route("/")
def index():
return flask.url_for(".about")
@bp.route("/about")
def about():
return flask.url_for(".index")
app.register_blueprint(bp)
assert client.get("/de/").data == b"/de/about"
assert client.get("/de/about").data == b"/de/"
def test_templates_and_static(test_apps):
from blueprintapp import app
client = app.test_client()
rv = client.get("/")
assert rv.data == b"hello from the frontend"
rv = client.get("/admin/")
assert rv.data == b"hello from the admin"
rv = client.get("/admin/index2")
assert rv.data == b"hello from the admin"
rv = client.get("/admin/static/test.txt")
assert rv.data.strip() == b"admin file"
rv.close()
rv = client.get("/admin/static/css/test.css")
assert rv.data.strip() == b""
rv.close()
max_age_default = app.config["send_file_max_age_default"]
try:
expected_max_age = 3600
if app.config["send_file_max_age_default"] == expected_max_age:
expected_max_age = 7200
app.config["send_file_max_age_default"] = expected_max_age
rv = client.get("/admin/static/css/test.css")
cc = parse_cache_control_header(rv.headers["cache-control"])
assert cc.max_age == expected_max_age
rv.close()
finally:
app.config["send_file_max_age_default"] = max_age_default
with app.test_request_context():
assert (
flask.url_for("admin.static", filename="test.txt")
== "/admin/static/test.txt"
)
with app.test_request_context():
with pytest.raises(templatenotfound) as e:
flask.render_template("missing.html")
assert e.value.name == "missing.html"
with flask.flask(__name__).test_request_context():
assert flask.render_template("nested/nested.txt") == "i'm nested"
def test_default_static_max_age(app):
class myblueprint(flask.blueprint):
def get_send_file_max_age(self, filename):
return 100
blueprint = myblueprint("blueprint", __name__, static_folder="static")
app.register_blueprint(blueprint)
max_age_default = app.config["send_file_max_age_default"]
try:
with app.test_request_context():
unexpected_max_age = 3600
if app.config["send_file_max_age_default"] == unexpected_max_age:
unexpected_max_age = 7200
app.config["send_file_max_age_default"] = unexpected_max_age
rv = blueprint.send_static_file("index.html")
cc = parse_cache_control_header(rv.headers["cache-control"])
assert cc.max_age == 100
rv.close()
finally:
app.config["send_file_max_age_default"] = max_age_default
def test_templates_list(test_apps):
from blueprintapp import app
templates = sorted(app.jinja_env.list_templates())
assert templates == ["admin/index.html", "frontend/index.html"]
def test_dotted_name_not_allowed(app, client):
with pytest.raises(valueerror):
flask.blueprint("app.ui", __name__)
def test_empty_name_not_allowed(app, client):
with pytest.raises(valueerror):
flask.blueprint("", __name__)
def test_dotted_names_from_app(app, client):
test = flask.blueprint("test", __name__)
@app.route("/")
def app_index():
return flask.url_for("test.index")
@test.route("/test/")
def index():
return flask.url_for("app_index")
app.register_blueprint(test)
rv = client.get("/")
assert rv.data == b"/test/"
def test_empty_url_defaults(app, client):
bp = flask.blueprint("bp", __name__)
@bp.route("/", defaults={"page": 1})
@bp.route("/page/<int:page>")
def something(page):
return str(page)
app.register_blueprint(bp)
assert client.get("/").data == b"1"
assert client.get("/page/2").data == b"2"
def test_route_decorator_custom_endpoint(app, client):
bp = flask.blueprint("bp", __name__)
@bp.route("/foo")
def foo():
return flask.request.endpoint
@bp.route("/bar", endpoint="bar")
def foo_bar():
return flask.request.endpoint
@bp.route("/bar/123", endpoint="123")
def foo_bar_foo():
return flask.request.endpoint
@bp.route("/bar/foo")
def bar_foo():
return flask.request.endpoint
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.request.endpoint
assert client.get("/").data == b"index"
assert client.get("/py/foo").data == b"bp.foo"
assert client.get("/py/bar").data == b"bp.bar"
assert client.get("/py/bar/123").data == b"bp.123"
assert client.get("/py/bar/foo").data == b"bp.bar_foo"
def test_route_decorator_custom_endpoint_with_dots(app, client):
bp = flask.blueprint("bp", __name__)
with pytest.raises(valueerror):
bp.route("/", endpoint="a.b")(lambda: "")
with pytest.raises(valueerror):
bp.add_url_rule("/", endpoint="a.b")
def view():
return ""
view.__name__ = "a.b"
with pytest.raises(valueerror):
bp.add_url_rule("/", view_func=view)
def test_endpoint_decorator(app, client):
from werkzeug.routing import rule
app.url_map.add(rule("/foo", endpoint="bar"))
bp = flask.blueprint("bp", __name__)
@bp.endpoint("bar")
def foobar():
return flask.request.endpoint
app.register_blueprint(bp, url_prefix="/bp_prefix")
assert client.get("/foo").data == b"bar"
assert client.get("/bp_prefix/bar").status_code == 404
def test_template_filter(app):
bp = flask.blueprint("bp", __name__)
@bp.app_template_filter()
def my_reverse(s):
return s[::-1]
app.register_blueprint(bp, url_prefix="/py")
assert "my_reverse" in app.jinja_env.filters.keys()
assert app.jinja_env.filters["my_reverse"] == my_reverse
assert app.jinja_env.filters["my_reverse"]("abcd") == "dcba"
def test_add_template_filter(app):
bp = flask.blueprint("bp", __name__)
def my_reverse(s):
return s[::-1]
bp.add_app_template_filter(my_reverse)
app.register_blueprint(bp, url_prefix="/py")
assert "my_reverse" in app.jinja_env.filters.keys()
assert app.jinja_env.filters["my_reverse"] == my_reverse
assert app.jinja_env.filters["my_reverse"]("abcd") == "dcba"
def test_template_filter_with_name(app):
bp = flask.blueprint("bp", __name__)
@bp.app_template_filter("strrev")
def my_reverse(s):
return s[::-1]
app.register_blueprint(bp, url_prefix="/py")
assert "strrev" in app.jinja_env.filters.keys()
assert app.jinja_env.filters["strrev"] == my_reverse
assert app.jinja_env.filters["strrev"]("abcd") == "dcba"
def test_add_template_filter_with_name(app):
bp = flask.blueprint("bp", __name__)
def my_reverse(s):
return s[::-1]
bp.add_app_template_filter(my_reverse, "strrev")
app.register_blueprint(bp, url_prefix="/py")
assert "strrev" in app.jinja_env.filters.keys()
assert app.jinja_env.filters["strrev"] == my_reverse
assert app.jinja_env.filters["strrev"]("abcd") == "dcba"
def test_template_filter_with_template(app, client):
bp = flask.blueprint("bp", __name__)
@bp.app_template_filter()
def super_reverse(s):
return s[::-1]
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
rv = client.get("/")
assert rv.data == b"dcba"
def test_template_filter_after_route_with_template(app, client):
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
bp = flask.blueprint("bp", __name__)
@bp.app_template_filter()
def super_reverse(s):
return s[::-1]
app.register_blueprint(bp, url_prefix="/py")
rv = client.get("/")
assert rv.data == b"dcba"
def test_add_template_filter_with_template(app, client):
bp = flask.blueprint("bp", __name__)
def super_reverse(s):
return s[::-1]
bp.add_app_template_filter(super_reverse)
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
rv = client.get("/")
assert rv.data == b"dcba"
def test_template_filter_with_name_and_template(app, client):
bp = flask.blueprint("bp", __name__)
@bp.app_template_filter("super_reverse")
def my_reverse(s):
return s[::-1]
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
rv = client.get("/")
assert rv.data == b"dcba"
def test_add_template_filter_with_name_and_template(app, client):
bp = flask.blueprint("bp", __name__)
def my_reverse(s):
return s[::-1]
bp.add_app_template_filter(my_reverse, "super_reverse")
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.render_template("template_filter.html", value="abcd")
rv = client.get("/")
assert rv.data == b"dcba"
def test_template_test(app):
bp = flask.blueprint("bp", __name__)
@bp.app_template_test()
def is_boolean(value):
return isinstance(value, bool)
app.register_blueprint(bp, url_prefix="/py")
assert "is_boolean" in app.jinja_env.tests.keys()
assert app.jinja_env.tests["is_boolean"] == is_boolean
assert app.jinja_env.tests["is_boolean"](false)
def test_add_template_test(app):
bp = flask.blueprint("bp", __name__)
def is_boolean(value):
return isinstance(value, bool)
bp.add_app_template_test(is_boolean)
app.register_blueprint(bp, url_prefix="/py")
assert "is_boolean" in app.jinja_env.tests.keys()
assert app.jinja_env.tests["is_boolean"] == is_boolean
assert app.jinja_env.tests["is_boolean"](false)
def test_template_test_with_name(app):
bp = flask.blueprint("bp", __name__)
@bp.app_template_test("boolean")
def is_boolean(value):
return isinstance(value, bool)
app.register_blueprint(bp, url_prefix="/py")
assert "boolean" in app.jinja_env.tests.keys()
assert app.jinja_env.tests["boolean"] == is_boolean
assert app.jinja_env.tests["boolean"](false)
def test_add_template_test_with_name(app):
bp = flask.blueprint("bp", __name__)
def is_boolean(value):
return isinstance(value, bool)
bp.add_app_template_test(is_boolean, "boolean")
app.register_blueprint(bp, url_prefix="/py")
assert "boolean" in app.jinja_env.tests.keys()
assert app.jinja_env.tests["boolean"] == is_boolean
assert app.jinja_env.tests["boolean"](false)
def test_template_test_with_template(app, client):
bp = flask.blueprint("bp", __name__)
@bp.app_template_test()
def boolean(value):
return isinstance(value, bool)
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
rv = client.get("/")
assert b"success!" in rv.data
def test_template_test_after_route_with_template(app, client):
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
bp = flask.blueprint("bp", __name__)
@bp.app_template_test()
def boolean(value):
return isinstance(value, bool)
app.register_blueprint(bp, url_prefix="/py")
rv = client.get("/")
assert b"success!" in rv.data
def test_add_template_test_with_template(app, client):
bp = flask.blueprint("bp", __name__)
def boolean(value):
return isinstance(value, bool)
bp.add_app_template_test(boolean)
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
rv = client.get("/")
assert b"success!" in rv.data
def test_template_test_with_name_and_template(app, client):
bp = flask.blueprint("bp", __name__)
@bp.app_template_test("boolean")
def is_boolean(value):
return isinstance(value, bool)
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
rv = client.get("/")
assert b"success!" in rv.data
def test_add_template_test_with_name_and_template(app, client):
bp = flask.blueprint("bp", __name__)
def is_boolean(value):
return isinstance(value, bool)
bp.add_app_template_test(is_boolean, "boolean")
app.register_blueprint(bp, url_prefix="/py")
@app.route("/")
def index():
return flask.render_template("template_test.html", value=false)
rv = client.get("/")
assert b"success!" in rv.data
def test_context_processing(app, client):
answer_bp = flask.blueprint("answer_bp", __name__)
def template_string():
return flask.render_template_string(
"{% if notanswer %}{{ notanswer }} is not the answer. {% endif %}"
"{% if answer %}{{ answer }} is the answer.{% endif %}"
)
@answer_bp.app_context_processor
def not_answer_context_processor():
return {"notanswer": 43}
@answer_bp.context_processor
def answer_context_processor():
return {"answer": 42}
@answer_bp.route("/bp")
def bp_page():
return template_string()
@app.route("/")
def app_page():
return template_string()
app.register_blueprint(answer_bp)
app_page_bytes = client.get("/").data
answer_page_bytes = client.get("/bp").data
assert b"43" in app_page_bytes
assert b"42" not in app_page_bytes
assert b"42" in answer_page_bytes
assert b"43" in answer_page_bytes
def test_template_global(app):
bp = flask.blueprint("bp", __name__)
@bp.app_template_global()
def get_answer():
return 42
assert "get_answer" not in app.jinja_env.globals.keys()
app.register_blueprint(bp)
assert "get_answer" in app.jinja_env.globals.keys()
assert app.jinja_env.globals["get_answer"] is get_answer
assert app.jinja_env.globals["get_answer"]() == 42
with app.app_context():
rv = flask.render_template_string("{{ get_answer() }}")
assert rv == "42"
def test_request_processing(app, client):
bp = flask.blueprint("bp", __name__)
evts = []
@bp.before_request
def before_bp():
evts.append("before")
@bp.after_request
def after_bp(response):
response.data += b"|after"
evts.append("after")
return response
@bp.teardown_request
def teardown_bp(exc):
evts.append("teardown")
@bp.route("/bp")
def bp_endpoint():
return "request"
app.register_blueprint(bp)
assert evts == []
rv = client.get("/bp")
assert rv.data == b"request|after"
assert evts == ["before", "after", "teardown"]
def test_app_request_processing(app, client):
bp = flask.blueprint("bp", __name__)
evts = []
@bp.before_app_request
def before_app():
evts.append("before")
@bp.after_app_request
def after_app(response):
response.data += b"|after"
evts.append("after")
return response
@bp.teardown_app_request
def teardown_app(exc):
evts.append("teardown")
app.register_blueprint(bp)
@app.route("/")
def bp_endpoint():
return "request"
assert evts == []
resp = client.get("/").data
assert resp == b"request|after"
assert evts == ["before", "after", "teardown"]
resp = client.get("/").data
assert resp == b"request|after"
assert evts == ["before", "after", "teardown"] * 2
def test_app_url_processors(app, client):
bp = flask.blueprint("bp", __name__)
@bp.app_url_defaults
def add_language_code(endpoint, values):
values.setdefault("lang_code", flask.g.lang_code)
@bp.app_url_value_preprocessor
def pull_lang_code(endpoint, values):
flask.g.lang_code = values.pop("lang_code")
@app.route("/<lang_code>/")
def index():
return flask.url_for("about")
@app.route("/<lang_code>/about")
def about():
return flask.url_for("index")
app.register_blueprint(bp)
assert client.get("/de/").data == b"/de/about"
assert client.get("/de/about").data == b"/de/"
def test_nested_blueprint(app, client):
parent = flask.blueprint("parent", __name__)
child = flask.blueprint("child", __name__)
grandchild = flask.blueprint("grandchild", __name__)
@parent.errorhandler(403)
def forbidden(e):
return "parent no", 403
@parent.route("/")
def parent_index():
return "parent yes"
@parent.route("/no")
def parent_no():
flask.abort(403)
@child.route("/")
def child_index():
return "child yes"
@child.route("/no")
def child_no():
flask.abort(403)
@grandchild.errorhandler(403)
def grandchild_forbidden(e):
return "grandchild no", 403
@grandchild.route("/")
def grandchild_index():
return "grandchild yes"
@grandchild.route("/no")
def grandchild_no():
flask.abort(403)
child.register_blueprint(grandchild, url_prefix="/grandchild")
parent.register_blueprint(child, url_prefix="/child")
app.register_blueprint(parent, url_prefix="/parent")
assert client.get("/parent/").data == b"parent yes"
assert client.get("/parent/child/").data == b"child yes"
assert client.get("/parent/child/grandchild/").data == b"grandchild yes"
assert client.get("/parent/no").data == b"parent no"
assert client.get("/parent/child/no").data == b"parent no"
assert client.get("/parent/child/grandchild/no").data == b"grandchild no"
def test_nested_callback_order(app, client):
parent = flask.blueprint("parent", __name__)
child = flask.blueprint("child", __name__)
@app.before_request
def app_before1():
flask.g.setdefault("seen", []).append("app_1")
@app.teardown_request
def app_teardown1(e=none):
assert flask.g.seen.pop() == "app_1"
@app.before_request
def app_before2():
flask.g.setdefault("seen", []).append("app_2")
@app.teardown_request
def app_teardown2(e=none):
assert flask.g.seen.pop() == "app_2"
@app.context_processor
def app_ctx():
return dict(key="app")
@parent.before_request
def parent_before1():
flask.g.setdefault("seen", []).append("parent_1")
@parent.teardown_request
def parent_teardown1(e=none):
assert flask.g.seen.pop() == "parent_1"
@parent.before_request
def parent_before2():
flask.g.setdefault("seen", []).append("parent_2")
@parent.teardown_request
def parent_teardown2(e=none):
assert flask.g.seen.pop() == "parent_2"
@parent.context_processor
def parent_ctx():
return dict(key="parent")
@child.before_request
def child_before1():
flask.g.setdefault("seen", []).append("child_1")
@child.teardown_request
def child_teardown1(e=none):
assert flask.g.seen.pop() == "child_1"
@child.before_request
def child_before2():
flask.g.setdefault("seen", []).append("child_2")
@child.teardown_request
def child_teardown2(e=none):
assert flask.g.seen.pop() == "child_2"
@child.context_processor
def child_ctx():
return dict(key="child")
@child.route("/a")
def a():
return ", ".join(flask.g.seen)
@child.route("/b")
def b():
return flask.render_template_string("{{ key }}")
parent.register_blueprint(child)
app.register_blueprint(parent)
assert (
client.get("/a").data == b"app_1, app_2, parent_1, parent_2, child_1, child_2"
)
assert client.get("/b").data == b"child"
@pytest.mark.parametrize(
"parent_init, child_init, parent_registration, child_registration",
[
("/parent", "/child", none, none),
("/parent", none, none, "/child"),
(none, none, "/parent", "/child"),
("/other", "/something", "/parent", "/child"),
],
)
def test_nesting_url_prefixes(
parent_init,
child_init,
parent_registration,
child_registration,
app,
client,
) -> none:
parent = flask.blueprint("parent", __name__, url_prefix=parent_init)
child = flask.blueprint("child", __name__, url_prefix=child_init)
@child.route("/")
def index():
return "index"
parent.register_blueprint(child, url_prefix=child_registration)
app.register_blueprint(parent, url_prefix=parent_registration)
response = client.get("/parent/child/")
assert response.status_code == 200
def test_nesting_subdomains(app, client) -> none:
app.subdomain_matching = true
app.config["server_name"] = "example.test"
client.allow_subdomain_redirects = true
parent = flask.blueprint("parent", __name__)
child = flask.blueprint("child", __name__)
@child.route("/child/")
def index():
return "child"
parent.register_blueprint(child)
app.register_blueprint(parent, subdomain="api")
response = client.get("/child/", base_url="http:
assert response.status_code == 200
def test_child_and_parent_subdomain(app, client) -> none:
app.subdomain_matching = true
app.config["server_name"] = "example.test"
client.allow_subdomain_redirects = true
parent = flask.blueprint("parent", __name__)
child = flask.blueprint("child", __name__, subdomain="api")
@child.route("/")
def index():
return "child"
parent.register_blueprint(child)
app.register_blueprint(parent, subdomain="parent")
response = client.get("/", base_url="http:
assert response.status_code == 200
response = client.get("/", base_url="http:
assert response.status_code == 404
def test_unique_blueprint_names(app, client) -> none:
bp = flask.blueprint("bp", __name__)
bp2 = flask.blueprint("bp", __name__)
app.register_blueprint(bp)
with pytest.raises(valueerror):
app.register_blueprint(bp)
app.register_blueprint(bp, name="again")
with pytest.raises(valueerror):
app.register_blueprint(bp2)
app.register_blueprint(bp2, name="alt")
def test_self_registration(app, client) -> none:
bp = flask.blueprint("bp", __name__)
with pytest.raises(valueerror):
bp.register_blueprint(bp)
def test_blueprint_renaming(app, client) -> none:
bp = flask.blueprint("bp", __name__)
bp2 = flask.blueprint("bp2", __name__)
@bp.get("/")
def index():
return flask.request.endpoint
@bp.get("/error")
def error():
flask.abort(403)
@bp.errorhandler(403)
def forbidden(_: exception):
return "error", 403
@bp2.get("/")
def index2():
return flask.request.endpoint
bp.register_blueprint(bp2, url_prefix="/a", name="sub")
app.register_blueprint(bp, url_prefix="/a")
app.register_blueprint(bp, url_prefix="/b", name="alt")
assert client.get("/a/").data == b"bp.index"
assert client.get("/b/").data == b"alt.index"
assert client.get("/a/a/").data == b"bp.sub.index2"
assert client.get("/b/a/").data == b"alt.sub.index2"
assert client.get("/a/error").data == b"error"
assert client.get("/b/error").data == b"error"