import logging
import sys
from io import stringio
import pytest
from flask.logging import default_handler
from flask.logging import has_level_handler
from flask.logging import wsgi_errors_stream
@pytest.fixture(autouse=true)
def reset_logging(pytestconfig):
root_handlers = logging.root.handlers[:]
logging.root.handlers = []
root_level = logging.root.level
logger = logging.getlogger("flask_test")
logger.handlers = []
logger.setlevel(logging.notset)
logging_plugin = pytestconfig.pluginmanager.unregister(name="logging-plugin")
yield
logging.root.handlers[:] = root_handlers
logging.root.setlevel(root_level)
logger.handlers = []
logger.setlevel(logging.notset)
if logging_plugin:
pytestconfig.pluginmanager.register(logging_plugin, "logging-plugin")
def test_logger(app):
assert app.logger.name == "flask_test"
assert app.logger.level == logging.notset
assert app.logger.handlers == [default_handler]
def test_logger_debug(app):
app.debug = true
assert app.logger.level == logging.debug
assert app.logger.handlers == [default_handler]
def test_existing_handler(app):
logging.root.addhandler(logging.streamhandler())
assert app.logger.level == logging.notset
assert not app.logger.handlers
def test_wsgi_errors_stream(app, client):
@app.route("/")
def index():
app.logger.error("test")
return ""
stream = stringio()
client.get("/", errors_stream=stream)
assert "error in test_logging: test" in stream.getvalue()
assert wsgi_errors_stream._get_current_object() is sys.stderr
with app.test_request_context(errors_stream=stream):
assert wsgi_errors_stream._get_current_object() is stream
def test_has_level_handler():
logger = logging.getlogger("flask.app")
assert not has_level_handler(logger)
handler = logging.streamhandler()
logging.root.addhandler(handler)
assert has_level_handler(logger)
logger.propagate = false
assert not has_level_handler(logger)
logger.propagate = true
handler.setlevel(logging.error)
assert not has_level_handler(logger)
def test_log_view_exception(app, client):
@app.route("/")
def index():
raise exception("test")
app.testing = false
stream = stringio()
rv = client.get("/", errors_stream=stream)
assert rv.status_code == 500
assert rv.data
err = stream.getvalue()
assert "exception on / [get]" in err
assert "exception: test" in err