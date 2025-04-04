from __future__ import annotations
import importlib.metadata
import typing as t
from contextlib import contextmanager
from contextlib import exitstack
from copy import copy
from types import tracebacktype
from urllib.parse import urlsplit
import werkzeug.test
from click.testing import clirunner
from click.testing import result
from werkzeug.test import client
from werkzeug.wrappers import request as baserequest
from .cli import scriptinfo
from .sessions import sessionmixin
if t.type_checking:
from _typeshed.wsgi import wsgienvironment
from werkzeug.test import testresponse
from .app import flask
class environbuilder(werkzeug.test.environbuilder):
def __init__(
self,
app: flask,
path: str = "/",
base_url: str | none = none,
subdomain: str | none = none,
url_scheme: str | none = none,
*args: t.any,
**kwargs: t.any,
) -> none:
assert not (base_url or subdomain or url_scheme) or (
base_url is not none
) != bool(subdomain or url_scheme), (
'cannot pass "subdomain" or "url_scheme" with "base_url".'
)
if base_url is none:
http_host = app.config.get("server_name") or "localhost"
app_root = app.config["application_root"]
if subdomain:
http_host = f"{subdomain}.{http_host}"
if url_scheme is none:
url_scheme = app.config["preferred_url_scheme"]
url = urlsplit(path)
base_url = (
f"{url.scheme or url_scheme}:
f"/{app_root.lstrip('/')}"
)
path = url.path
if url.query:
path = f"{path}?{url.query}"
self.app = app
super().__init__(path, base_url, *args, **kwargs)
def json_dumps(self, obj: t.any, **kwargs: t.any) -> str:
return self.app.json.dumps(obj, **kwargs)
_werkzeug_version = ""
def _get_werkzeug_version() -> str:
global _werkzeug_version
if not _werkzeug_version:
_werkzeug_version = importlib.metadata.version("werkzeug")
return _werkzeug_version
class flaskclient(client):
application: flask
def __init__(self, *args: t.any, **kwargs: t.any) -> none:
super().__init__(*args, **kwargs)
self.preserve_context = false
self._new_contexts: list[t.contextmanager[t.any]] = []
self._context_stack = exitstack()
self.environ_base = {
"remote_addr": "127.0.0.1",
"http_user_agent": f"werkzeug/{_get_werkzeug_version()}",
}
@contextmanager
def session_transaction(
self, *args: t.any, **kwargs: t.any
) -> t.iterator[sessionmixin]:
if self._cookies is none:
raise typeerror(
"cookies are disabled. create a client with 'use_cookies=true'."
)
app = self.application
ctx = app.test_request_context(*args, **kwargs)
self._add_cookies_to_wsgi(ctx.request.environ)
with ctx:
sess = app.session_interface.open_session(app, ctx.request)
if sess is none:
raise runtimeerror("session backend did not open a session.")
yield sess
resp = app.response_class()
if app.session_interface.is_null_session(sess):
return
with ctx:
app.session_interface.save_session(app, sess, resp)
self._update_cookies_from_response(
ctx.request.host.partition(":")[0],
ctx.request.path,
resp.headers.getlist("set-cookie"),
)
def _copy_environ(self, other: wsgienvironment) -> wsgienvironment:
out = {**self.environ_base, **other}
if self.preserve_context:
out["werkzeug.debug.preserve_context"] = self._new_contexts.append
return out
def _request_from_builder_args(
self, args: tuple[t.any, ...], kwargs: dict[str, t.any]
) -> baserequest:
kwargs["environ_base"] = self._copy_environ(kwargs.get("environ_base", {}))
builder = environbuilder(self.application, *args, **kwargs)
try:
return builder.get_request()
finally:
builder.close()
def open(
self,
*args: t.any,
buffered: bool = false,
follow_redirects: bool = false,
**kwargs: t.any,
) -> testresponse:
if args and isinstance(
args[0], (werkzeug.test.environbuilder, dict, baserequest)
):
if isinstance(args[0], werkzeug.test.environbuilder):
builder = copy(args[0])
builder.environ_base = self._copy_environ(builder.environ_base or {})
request = builder.get_request()
elif isinstance(args[0], dict):
request = environbuilder.from_environ(
args[0], app=self.application, environ_base=self._copy_environ({})
).get_request()
else:
request = copy(args[0])
request.environ = self._copy_environ(request.environ)
else:
request = self._request_from_builder_args(args, kwargs)
self._context_stack.close()
response = super().open(
request,
buffered=buffered,
follow_redirects=follow_redirects,
)
response.json_module = self.application.json
while self._new_contexts:
cm = self._new_contexts.pop()
self._context_stack.enter_context(cm)
return response
def __enter__(self) -> flaskclient:
if self.preserve_context:
raise runtimeerror("cannot nest client invocations")
self.preserve_context = true
return self
def __exit__(
self,
exc_type: type | none,
exc_value: baseexception | none,
tb: tracebacktype | none,
) -> none:
self.preserve_context = false
self._context_stack.close()
class flaskclirunner(clirunner):
def __init__(self, app: flask, **kwargs: t.any) -> none:
self.app = app
super().__init__(**kwargs)
def invoke(
self, cli: t.any = none, args: t.any = none, **kwargs: t.any
) -> result:
if cli is none:
cli = self.app.cli
if "obj" not in kwargs:
kwargs["obj"] = scriptinfo(create_app=lambda: self.app)
return super().invoke(cli, args, **kwargs)