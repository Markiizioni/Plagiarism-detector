import os
import sys
import pytest
from _pytest import monkeypatch
from flask import flask
from flask.globals import request_ctx
@pytest.fixture(scope="session", autouse=true)
def _standard_os_environ():
mp = monkeypatch.monkeypatch()
out = (
(os.environ, "flask_env_file", monkeypatch.notset),
(os.environ, "flask_app", monkeypatch.notset),
(os.environ, "flask_debug", monkeypatch.notset),
(os.environ, "flask_run_from_cli", monkeypatch.notset),
(os.environ, "werkzeug_run_main", monkeypatch.notset),
)
for _, key, value in out:
if value is monkeypatch.notset:
mp.delenv(key, false)
else:
mp.setenv(key, value)
yield out
mp.undo()
@pytest.fixture(autouse=true)
def _reset_os_environ(monkeypatch, _standard_os_environ):
monkeypatch._setitem.extend(_standard_os_environ)
@pytest.fixture
def app():
app = flask("flask_test", root_path=os.path.dirname(__file__))
app.config.update(
testing=true,
secret_key="test key",
)
return app
@pytest.fixture
def app_ctx(app):
with app.app_context() as ctx:
yield ctx
@pytest.fixture
def req_ctx(app):
with app.test_request_context() as ctx:
yield ctx
@pytest.fixture
def client(app):
return app.test_client()
@pytest.fixture
def test_apps(monkeypatch):
monkeypatch.syspath_prepend(os.path.join(os.path.dirname(__file__), "test_apps"))
original_modules = set(sys.modules.keys())
yield
for key in sys.modules.keys() - original_modules:
sys.modules.pop(key)
@pytest.fixture(autouse=true)
def leak_detector():
yield
leaks = []
while request_ctx:
leaks.append(request_ctx._get_current_object())
request_ctx.pop()
assert leaks == []
@pytest.fixture
def modules_tmp_path(tmp_path, monkeypatch):
rv = tmp_path / "modules_tmp"
rv.mkdir()
monkeypatch.syspath_prepend(os.fspath(rv))
return rv
@pytest.fixture
def modules_tmp_path_prefix(modules_tmp_path, monkeypatch):
monkeypatch.setattr(sys, "prefix", os.fspath(modules_tmp_path))
return modules_tmp_path
@pytest.fixture
def site_packages(modules_tmp_path, monkeypatch):
py_dir = f"python{sys.version_info.major}.{sys.version_info.minor}"
rv = modules_tmp_path / "lib" / py_dir / "site-packages"
rv.mkdir(parents=true)
monkeypatch.syspath_prepend(os.fspath(rv))
return rv
@pytest.fixture
def purge_module(request):
def inner(name):
request.addfinalizer(lambda: sys.modules.pop(name, none))
return inner