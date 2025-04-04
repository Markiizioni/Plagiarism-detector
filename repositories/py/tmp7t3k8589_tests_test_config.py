import json
import os
import pytest
import flask
test_key = "foo"
secret_key = "config"
def common_object_test(app):
assert app.secret_key == "config"
assert app.config["test_key"] == "foo"
assert "testconfig" not in app.config
def test_config_from_pyfile():
app = flask.flask(__name__)
app.config.from_pyfile(f"{__file__.rsplit('.', 1)[0]}.py")
common_object_test(app)
def test_config_from_object():
app = flask.flask(__name__)
app.config.from_object(__name__)
common_object_test(app)
def test_config_from_file_json():
app = flask.flask(__name__)
current_dir = os.path.dirname(os.path.abspath(__file__))
app.config.from_file(os.path.join(current_dir, "static", "config.json"), json.load)
common_object_test(app)
def test_config_from_file_toml():
tomllib = pytest.importorskip("tomllib", reason="tomllib added in 3.11")
app = flask.flask(__name__)
current_dir = os.path.dirname(os.path.abspath(__file__))
app.config.from_file(
os.path.join(current_dir, "static", "config.toml"), tomllib.load, text=false
)
common_object_test(app)
def test_from_prefixed_env(monkeypatch):
monkeypatch.setenv("flask_string", "value")
monkeypatch.setenv("flask_bool", "true")
monkeypatch.setenv("flask_int", "1")
monkeypatch.setenv("flask_float", "1.2")
monkeypatch.setenv("flask_list", "[1, 2]")
monkeypatch.setenv("flask_dict", '{"k": "v"}')
monkeypatch.setenv("not_flask_other", "other")
app = flask.flask(__name__)
app.config.from_prefixed_env()
assert app.config["string"] == "value"
assert app.config["bool"] is true
assert app.config["int"] == 1
assert app.config["float"] == 1.2
assert app.config["list"] == [1, 2]
assert app.config["dict"] == {"k": "v"}
assert "other" not in app.config
def test_from_prefixed_env_custom_prefix(monkeypatch):
monkeypatch.setenv("flask_a", "a")
monkeypatch.setenv("not_flask_a", "b")
app = flask.flask(__name__)
app.config.from_prefixed_env("not_flask")
assert app.config["a"] == "b"
def test_from_prefixed_env_nested(monkeypatch):
monkeypatch.setenv("flask_exist__ok", "other")
monkeypatch.setenv("flask_exist__inner__ik", "2")
monkeypatch.setenv("flask_exist__new__more", '{"k": false}')
monkeypatch.setenv("flask_new__k", "v")
app = flask.flask(__name__)
app.config["exist"] = {"ok": "value", "flag": true, "inner": {"ik": 1}}
app.config.from_prefixed_env()
if os.name != "nt":
assert app.config["exist"] == {
"ok": "other",
"flag": true,
"inner": {"ik": 2},
"new": {"more": {"k": false}},
}
else:
assert app.config["exist"] == {
"ok": "value",
"ok": "other",
"flag": true,
"inner": {"ik": 1},
"inner": {"ik": 2},
"new": {"more": {"k": false}},
}
assert app.config["new"] == {"k": "v"}
def test_config_from_mapping():
app = flask.flask(__name__)
app.config.from_mapping({"secret_key": "config", "test_key": "foo"})
common_object_test(app)
app = flask.flask(__name__)
app.config.from_mapping([("secret_key", "config"), ("test_key", "foo")])
common_object_test(app)
app = flask.flask(__name__)
app.config.from_mapping(secret_key="config", test_key="foo")
common_object_test(app)
app = flask.flask(__name__)
app.config.from_mapping(secret_key="config", test_key="foo", skip_key="skip")
common_object_test(app)
app = flask.flask(__name__)
with pytest.raises(typeerror):
app.config.from_mapping({}, {})
def test_config_from_class():
class base:
test_key = "foo"
class test(base):
secret_key = "config"
app = flask.flask(__name__)
app.config.from_object(test)
common_object_test(app)
def test_config_from_envvar(monkeypatch):
monkeypatch.setattr("os.environ", {})
app = flask.flask(__name__)
with pytest.raises(runtimeerror) as e:
app.config.from_envvar("foo_settings")
assert "'foo_settings' is not set" in str(e.value)
assert not app.config.from_envvar("foo_settings", silent=true)
monkeypatch.setattr(
"os.environ", {"foo_settings": f"{__file__.rsplit('.', 1)[0]}.py"}
)
assert app.config.from_envvar("foo_settings")
common_object_test(app)
def test_config_from_envvar_missing(monkeypatch):
monkeypatch.setattr("os.environ", {"foo_settings": "missing.cfg"})
app = flask.flask(__name__)
with pytest.raises(ioerror) as e:
app.config.from_envvar("foo_settings")
msg = str(e.value)
assert msg.startswith(
"[errno 2] unable to load configuration file (no such file or directory):"
)
assert msg.endswith("missing.cfg'")
assert not app.config.from_envvar("foo_settings", silent=true)
def test_config_missing():
app = flask.flask(__name__)
with pytest.raises(ioerror) as e:
app.config.from_pyfile("missing.cfg")
msg = str(e.value)
assert msg.startswith(
"[errno 2] unable to load configuration file (no such file or directory):"
)
assert msg.endswith("missing.cfg'")
assert not app.config.from_pyfile("missing.cfg", silent=true)
def test_config_missing_file():
app = flask.flask(__name__)
with pytest.raises(ioerror) as e:
app.config.from_file("missing.json", load=json.load)
msg = str(e.value)
assert msg.startswith(
"[errno 2] unable to load configuration file (no such file or directory):"
)
assert msg.endswith("missing.json'")
assert not app.config.from_file("missing.json", load=json.load, silent=true)
def test_custom_config_class():
class config(flask.config):
pass
class flask(flask.flask):
config_class = config
app = flask(__name__)
assert isinstance(app.config, config)
app.config.from_object(__name__)
common_object_test(app)
def test_session_lifetime():
app = flask.flask(__name__)
app.config["permanent_session_lifetime"] = 42
assert app.permanent_session_lifetime.seconds == 42
def test_get_namespace():
app = flask.flask(__name__)
app.config["foo_option_1"] = "foo option 1"
app.config["foo_option_2"] = "foo option 2"
app.config["bar_stuff_1"] = "bar stuff 1"
app.config["bar_stuff_2"] = "bar stuff 2"
foo_options = app.config.get_namespace("foo_")
assert 2 == len(foo_options)
assert "foo option 1" == foo_options["option_1"]
assert "foo option 2" == foo_options["option_2"]
bar_options = app.config.get_namespace("bar_", lowercase=false)
assert 2 == len(bar_options)
assert "bar stuff 1" == bar_options["stuff_1"]
assert "bar stuff 2" == bar_options["stuff_2"]
foo_options = app.config.get_namespace("foo_", trim_namespace=false)
assert 2 == len(foo_options)
assert "foo option 1" == foo_options["foo_option_1"]
assert "foo option 2" == foo_options["foo_option_2"]
bar_options = app.config.get_namespace(
"bar_", lowercase=false, trim_namespace=false
)
assert 2 == len(bar_options)
assert "bar stuff 1" == bar_options["bar_stuff_1"]
assert "bar stuff 2" == bar_options["bar_stuff_2"]
@pytest.mark.parametrize("encoding", ["utf-8", "iso-8859-15", "latin-1"])
def test_from_pyfile_weird_encoding(tmp_path, encoding):
f = tmp_path / "my_config.py"
f.write_text(f'
app = flask.flask(__name__)
app.config.from_pyfile(os.fspath(f))
value = app.config["test_value"]
assert value == "föö"