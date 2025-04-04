import importlib.metadata
import os
import platform
import ssl
import sys
import types
from functools import partial
from pathlib import path
import click
import pytest
from _pytest.monkeypatch import notset
from click.testing import clirunner
from flask import blueprint
from flask import current_app
from flask import flask
from flask.cli import appgroup
from flask.cli import find_best_app
from flask.cli import flaskgroup
from flask.cli import get_version
from flask.cli import load_dotenv
from flask.cli import locate_app
from flask.cli import noappexception
from flask.cli import prepare_import
from flask.cli import run_command
from flask.cli import scriptinfo
from flask.cli import with_appcontext
cwd = path.cwd()
test_path = (path(__file__) / ".." / "test_apps").resolve()
@pytest.fixture
def runner():
return clirunner()
def test_cli_name(test_apps):
from cliapp.app import testapp
assert testapp.cli.name == testapp.name
def test_find_best_app(test_apps):
class module:
app = flask("appname")
assert find_best_app(module) == module.app
class module:
application = flask("appname")
assert find_best_app(module) == module.application
class module:
myapp = flask("appname")
assert find_best_app(module) == module.myapp
class module:
@staticmethod
def create_app():
return flask("appname")
app = find_best_app(module)
assert isinstance(app, flask)
assert app.name == "appname"
class module:
@staticmethod
def create_app(**kwargs):
return flask("appname")
app = find_best_app(module)
assert isinstance(app, flask)
assert app.name == "appname"
class module:
@staticmethod
def make_app():
return flask("appname")
app = find_best_app(module)
assert isinstance(app, flask)
assert app.name == "appname"
class module:
myapp = flask("appname1")
@staticmethod
def create_app():
return flask("appname2")
assert find_best_app(module) == module.myapp
class module:
myapp = flask("appname1")
@staticmethod
def create_app():
return flask("appname2")
assert find_best_app(module) == module.myapp
class module:
pass
pytest.raises(noappexception, find_best_app, module)
class module:
myapp1 = flask("appname1")
myapp2 = flask("appname2")
pytest.raises(noappexception, find_best_app, module)
class module:
@staticmethod
def create_app(foo, bar):
return flask("appname2")
pytest.raises(noappexception, find_best_app, module)
class module:
@staticmethod
def create_app():
raise typeerror("bad bad factory!")
pytest.raises(typeerror, find_best_app, module)
@pytest.mark.parametrize(
"value,path,result",
(
("test", cwd, "test"),
("test.py", cwd, "test"),
("a/test", cwd / "a", "test"),
("test/__init__.py", cwd, "test"),
("test/__init__", cwd, "test"),
(
test_path / "cliapp" / "inner1" / "__init__",
test_path,
"cliapp.inner1",
),
(
test_path / "cliapp" / "inner1" / "inner2",
test_path,
"cliapp.inner1.inner2",
),
("test.a.b", cwd, "test.a.b"),
(test_path / "cliapp.app", test_path, "cliapp.app"),
(test_path / "cliapp" / "message.txt", test_path, "cliapp.message.txt"),
),
)
def test_prepare_import(request, value, path, result):
original_path = sys.path[:]
def reset_path():
sys.path[:] = original_path
request.addfinalizer(reset_path)
assert prepare_import(value) == result
assert sys.path[0] == str(path)
@pytest.mark.parametrize(
"iname,aname,result",
(
("cliapp.app", none, "testapp"),
("cliapp.app", "testapp", "testapp"),
("cliapp.factory", none, "app"),
("cliapp.factory", "create_app", "app"),
("cliapp.factory", "create_app()", "app"),
("cliapp.factory", 'create_app2("foo", "bar")', "app2_foo_bar"),
("cliapp.factory", 'create_app2("foo", "bar", )', "app2_foo_bar"),
("cliapp.factory", " create_app () ", "app"),
),
)
def test_locate_app(test_apps, iname, aname, result):
assert locate_app(iname, aname).name == result
@pytest.mark.parametrize(
"iname,aname",
(
("notanapp.py", none),
("cliapp/app", none),
("cliapp.app", "notanapp"),
("cliapp.factory", 'create_app2("foo")'),
("cliapp.factory", "create_app("),
("cliapp.factory", "no_app"),
("cliapp.importerrorapp", none),
("cliapp.message.txt", none),
),
)
def test_locate_app_raises(test_apps, iname, aname):
with pytest.raises(noappexception):
locate_app(iname, aname)
def test_locate_app_suppress_raise(test_apps):
app = locate_app("notanapp.py", none, raise_if_not_found=false)
assert app is none
with pytest.raises(noappexception):
locate_app("cliapp.importerrorapp", none, raise_if_not_found=false)
def test_get_version(test_apps, capsys):
class mockctx:
resilient_parsing = false
color = none
def exit(self):
return
ctx = mockctx()
get_version(ctx, none, "test")
out, err = capsys.readouterr()
assert f"python {platform.python_version()}" in out
assert f"flask {importlib.metadata.version('flask')}" in out
assert f"werkzeug {importlib.metadata.version('werkzeug')}" in out
def test_scriptinfo(test_apps, monkeypatch):
obj = scriptinfo(app_import_path="cliapp.app:testapp")
app = obj.load_app()
assert app.name == "testapp"
assert obj.load_app() is app
cli_app_path = str(test_path / "cliapp" / "app.py")
obj = scriptinfo(app_import_path=cli_app_path)
app = obj.load_app()
assert app.name == "testapp"
assert obj.load_app() is app
obj = scriptinfo(app_import_path=f"{cli_app_path}:testapp")
app = obj.load_app()
assert app.name == "testapp"
assert obj.load_app() is app
def create_app():
return flask("createapp")
obj = scriptinfo(create_app=create_app)
app = obj.load_app()
assert app.name == "createapp"
assert obj.load_app() is app
obj = scriptinfo()
pytest.raises(noappexception, obj.load_app)
monkeypatch.chdir(test_path / "helloworld")
obj = scriptinfo()
app = obj.load_app()
assert app.name == "hello"
monkeypatch.chdir(test_path / "cliapp")
obj = scriptinfo()
app = obj.load_app()
assert app.name == "testapp"
def test_app_cli_has_app_context(app, runner):
def _param_cb(ctx, param, value):
return bool(current_app)
@app.cli.command()
@click.argument("value", callback=_param_cb)
def check(value):
app = click.get_current_context().obj.load_app()
same_app = current_app._get_current_object() is app
return same_app, value
cli = flaskgroup(create_app=lambda: app)
result = runner.invoke(cli, ["check", "x"], standalone_mode=false)
assert result.return_value == (true, true)
def test_with_appcontext(runner):
@click.command()
@with_appcontext
def testcmd():
click.echo(current_app.name)
obj = scriptinfo(create_app=lambda: flask("testapp"))
result = runner.invoke(testcmd, obj=obj)
assert result.exit_code == 0
assert result.output == "testapp\n"
def test_appgroup_app_context(runner):
@click.group(cls=appgroup)
def cli():
pass
@cli.command()
def test():
click.echo(current_app.name)
@cli.group()
def subgroup():
pass
@subgroup.command()
def test2():
click.echo(current_app.name)
obj = scriptinfo(create_app=lambda: flask("testappgroup"))
result = runner.invoke(cli, ["test"], obj=obj)
assert result.exit_code == 0
assert result.output == "testappgroup\n"
result = runner.invoke(cli, ["subgroup", "test2"], obj=obj)
assert result.exit_code == 0
assert result.output == "testappgroup\n"
def test_flaskgroup_app_context(runner):
def create_app():
return flask("flaskgroup")
@click.group(cls=flaskgroup, create_app=create_app)
def cli(**params):
pass
@cli.command()
def test():
click.echo(current_app.name)
result = runner.invoke(cli, ["test"])
assert result.exit_code == 0
assert result.output == "flaskgroup\n"
@pytest.mark.parametrize("set_debug_flag", (true, false))
def test_flaskgroup_debug(runner, set_debug_flag):
def create_app():
app = flask("flaskgroup")
app.debug = true
return app
@click.group(cls=flaskgroup, create_app=create_app, set_debug_flag=set_debug_flag)
def cli(**params):
pass
@cli.command()
def test():
click.echo(str(current_app.debug))
result = runner.invoke(cli, ["test"])
assert result.exit_code == 0
assert result.output == f"{not set_debug_flag}\n"
def test_flaskgroup_nested(app, runner):
cli = click.group("cli")
flask_group = flaskgroup(name="flask", create_app=lambda: app)
cli.add_command(flask_group)
@flask_group.command()
def show():
click.echo(current_app.name)
result = runner.invoke(cli, ["flask", "show"])
assert result.output == "flask_test\n"
def test_no_command_echo_loading_error():
from flask.cli import cli
try:
runner = clirunner(mix_stderr=false)
except (deprecationwarning, typeerror):
runner = clirunner()
result = runner.invoke(cli, ["missing"])
assert result.exit_code == 2
assert "flask_app" in result.stderr
assert "usage:" in result.stderr
def test_help_echo_loading_error():
from flask.cli import cli
try:
runner = clirunner(mix_stderr=false)
except (deprecationwarning, typeerror):
runner = clirunner()
result = runner.invoke(cli, ["--help"])
assert result.exit_code == 0
assert "flask_app" in result.stderr
assert "usage:" in result.stdout
def test_help_echo_exception():
def create_app():
raise exception("oh no")
cli = flaskgroup(create_app=create_app)
try:
runner = clirunner(mix_stderr=false)
except (deprecationwarning, typeerror):
runner = clirunner()
result = runner.invoke(cli, ["--help"])
assert result.exit_code == 0
assert "exception: oh no" in result.stderr
assert "usage:" in result.stdout
class testroutes:
@pytest.fixture
def app(self):
app = flask(__name__)
app.add_url_rule(
"/get_post/<int:x>/<int:y>",
methods=["get", "post"],
endpoint="yyy_get_post",
)
app.add_url_rule("/zzz_post", methods=["post"], endpoint="aaa_post")
return app
@pytest.fixture
def invoke(self, app, runner):
cli = flaskgroup(create_app=lambda: app)
return partial(runner.invoke, cli)
def expect_order(self, order, output):
for expect, line in zip(order, output.splitlines()[2:]):
assert line[: len(expect)] == expect
def test_simple(self, invoke):
result = invoke(["routes"])
assert result.exit_code == 0
self.expect_order(["aaa_post", "static", "yyy_get_post"], result.output)
def test_sort(self, app, invoke):
default_output = invoke(["routes"]).output
endpoint_output = invoke(["routes", "-s", "endpoint"]).output
assert default_output == endpoint_output
self.expect_order(
["static", "yyy_get_post", "aaa_post"],
invoke(["routes", "-s", "methods"]).output,
)
self.expect_order(
["yyy_get_post", "static", "aaa_post"],
invoke(["routes", "-s", "rule"]).output,
)
match_order = [r.endpoint for r in app.url_map.iter_rules()]
self.expect_order(match_order, invoke(["routes", "-s", "match"]).output)
def test_all_methods(self, invoke):
output = invoke(["routes"]).output
assert "get, head, options, post" not in output
output = invoke(["routes", "--all-methods"]).output
assert "get, head, options, post" in output
def test_no_routes(self, runner):
app = flask(__name__, static_folder=none)
cli = flaskgroup(create_app=lambda: app)
result = runner.invoke(cli, ["routes"])
assert result.exit_code == 0
assert "no routes were registered." in result.output
def test_subdomain(self, runner):
app = flask(__name__, static_folder=none)
app.add_url_rule("/a", subdomain="a", endpoint="a")
app.add_url_rule("/b", subdomain="b", endpoint="b")
cli = flaskgroup(create_app=lambda: app)
result = runner.invoke(cli, ["routes"])
assert result.exit_code == 0
assert "subdomain" in result.output
def test_host(self, runner):
app = flask(__name__, static_folder=none, host_matching=true)
app.add_url_rule("/a", host="a", endpoint="a")
app.add_url_rule("/b", host="b", endpoint="b")
cli = flaskgroup(create_app=lambda: app)
result = runner.invoke(cli, ["routes"])
assert result.exit_code == 0
assert "host" in result.output
def dotenv_not_available():
try:
import dotenv
except importerror:
return true
return false
need_dotenv = pytest.mark.skipif(
dotenv_not_available(), reason="dotenv is not installed"
)
@need_dotenv
def test_load_dotenv(monkeypatch):
for item in ("foo", "bar", "spam", "ham"):
monkeypatch._setitem.append((os.environ, item, notset))
monkeypatch.setenv("eggs", "3")
monkeypatch.chdir(test_path)
assert load_dotenv()
assert path.cwd() == test_path
assert os.environ["foo"] == "env"
assert os.environ["bar"] == "bar"
assert os.environ["spam"] == "1"
assert os.environ["eggs"] == "3"
assert os.environ["ham"] == "火腿"
assert not load_dotenv("non-existent-file", load_defaults=false)
@need_dotenv
def test_dotenv_path(monkeypatch):
for item in ("foo", "bar", "eggs"):
monkeypatch._setitem.append((os.environ, item, notset))
load_dotenv(test_path / ".flaskenv")
assert path.cwd() == cwd
assert "foo" in os.environ
def test_dotenv_optional(monkeypatch):
monkeypatch.setitem(sys.modules, "dotenv", none)
monkeypatch.chdir(test_path)
load_dotenv()
assert "foo" not in os.environ
@need_dotenv
def test_disable_dotenv_from_env(monkeypatch, runner):
monkeypatch.chdir(test_path)
monkeypatch.setitem(os.environ, "flask_skip_dotenv", "1")
runner.invoke(flaskgroup())
assert "foo" not in os.environ
def test_run_cert_path():
with pytest.raises(click.badparameter):
run_command.make_context("run", ["--cert", __file__])
with pytest.raises(click.badparameter):
run_command.make_context("run", ["--key", __file__])
ctx = run_command.make_context("run", ["--cert", __file__, "--key", __file__])
assert ctx.params["cert"] == (__file__, __file__)
ctx = run_command.make_context("run", ["--key", __file__, "--cert", __file__])
assert ctx.params["cert"] == (__file__, __file__)
def test_run_cert_adhoc(monkeypatch):
monkeypatch.setitem(sys.modules, "cryptography", none)
with pytest.raises(click.badparameter):
run_command.make_context("run", ["--cert", "adhoc"])
monkeypatch.setitem(sys.modules, "cryptography", types.moduletype("cryptography"))
ctx = run_command.make_context("run", ["--cert", "adhoc"])
assert ctx.params["cert"] == "adhoc"
with pytest.raises(click.badparameter):
run_command.make_context("run", ["--cert", "adhoc", "--key", __file__])
def test_run_cert_import(monkeypatch):
monkeypatch.setitem(sys.modules, "not_here", none)
with pytest.raises(click.badparameter):
run_command.make_context("run", ["--cert", "not_here"])
with pytest.raises(click.badparameter):
run_command.make_context("run", ["--cert", "flask"])
ssl_context = ssl.sslcontext(ssl.protocol_tls_server)
monkeypatch.setitem(sys.modules, "ssl_context", ssl_context)
ctx = run_command.make_context("run", ["--cert", "ssl_context"])
assert ctx.params["cert"] is ssl_context
with pytest.raises(click.badparameter):
run_command.make_context("run", ["--cert", "ssl_context", "--key", __file__])
def test_run_cert_no_ssl(monkeypatch):
monkeypatch.setitem(sys.modules, "ssl", none)
with pytest.raises(click.badparameter):
run_command.make_context("run", ["--cert", "not_here"])
def test_cli_blueprints(app):
custom = blueprint("custom", __name__, cli_group="customized")
nested = blueprint("nested", __name__)
merged = blueprint("merged", __name__, cli_group=none)
late = blueprint("late", __name__)
@custom.cli.command("custom")
def custom_command():
click.echo("custom_result")
@nested.cli.command("nested")
def nested_command():
click.echo("nested_result")
@merged.cli.command("merged")
def merged_command():
click.echo("merged_result")
@late.cli.command("late")
def late_command():
click.echo("late_result")
app.register_blueprint(custom)
app.register_blueprint(nested)
app.register_blueprint(merged)
app.register_blueprint(late, cli_group="late_registration")
app_runner = app.test_cli_runner()
result = app_runner.invoke(args=["customized", "custom"])
assert "custom_result" in result.output
result = app_runner.invoke(args=["nested", "nested"])
assert "nested_result" in result.output
result = app_runner.invoke(args=["merged"])
assert "merged_result" in result.output
result = app_runner.invoke(args=["late_registration", "late"])
assert "late_result" in result.output
def test_cli_empty(app):
bp = blueprint("blue", __name__, cli_group="blue")
app.register_blueprint(bp)
result = app.test_cli_runner().invoke(args=["blue", "--help"])
assert result.exit_code == 2, f"unexpected success:\n\n{result.output}"
def test_run_exclude_patterns():
ctx = run_command.make_context("run", ["--exclude-patterns", __file__])
assert ctx.params["exclude_patterns"] == [__file__]