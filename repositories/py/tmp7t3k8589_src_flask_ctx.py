from __future__ import annotations
import contextvars
import sys
import typing as t
from functools import update_wrapper
from types import tracebacktype
from werkzeug.exceptions import httpexception
from . import typing as ft
from .globals import _cv_app
from .globals import _cv_request
from .signals import appcontext_popped
from .signals import appcontext_pushed
if t.type_checking:
from _typeshed.wsgi import wsgienvironment
from .app import flask
from .sessions import sessionmixin
from .wrappers import request
_sentinel = object()
class _appctxglobals:
def __getattr__(self, name: str) -> t.any:
try:
return self.__dict__[name]
except keyerror:
raise attributeerror(name) from none
def __setattr__(self, name: str, value: t.any) -> none:
self.__dict__[name] = value
def __delattr__(self, name: str) -> none:
try:
del self.__dict__[name]
except keyerror:
raise attributeerror(name) from none
def get(self, name: str, default: t.any | none = none) -> t.any:
return self.__dict__.get(name, default)
def pop(self, name: str, default: t.any = _sentinel) -> t.any:
if default is _sentinel:
return self.__dict__.pop(name)
else:
return self.__dict__.pop(name, default)
def setdefault(self, name: str, default: t.any = none) -> t.any:
return self.__dict__.setdefault(name, default)
def __contains__(self, item: str) -> bool:
return item in self.__dict__
def __iter__(self) -> t.iterator[str]:
return iter(self.__dict__)
def __repr__(self) -> str:
ctx = _cv_app.get(none)
if ctx is not none:
return f"<flask.g of '{ctx.app.name}'>"
return object.__repr__(self)
def after_this_request(
f: ft.afterrequestcallable[t.any],
) -> ft.afterrequestcallable[t.any]:
ctx = _cv_request.get(none)
if ctx is none:
raise runtimeerror(
"'after_this_request' can only be used when a request"
" context is active, such as in a view function."
)
ctx._after_request_functions.append(f)
return f
f = t.typevar("f", bound=t.callable[..., t.any])
def copy_current_request_context(f: f) -> f:
ctx = _cv_request.get(none)
if ctx is none:
raise runtimeerror(
"'copy_current_request_context' can only be used when a"
" request context is active, such as in a view function."
)
ctx = ctx.copy()
def wrapper(*args: t.any, **kwargs: t.any) -> t.any:
with ctx:
return ctx.app.ensure_sync(f)(*args, **kwargs)
return update_wrapper(wrapper, f)
def has_request_context() -> bool:
return _cv_request.get(none) is not none
def has_app_context() -> bool:
return _cv_app.get(none) is not none
class appcontext:
def __init__(self, app: flask) -> none:
self.app = app
self.url_adapter = app.create_url_adapter(none)
self.g: _appctxglobals = app.app_ctx_globals_class()
self._cv_tokens: list[contextvars.token[appcontext]] = []
def push(self) -> none:
self._cv_tokens.append(_cv_app.set(self))
appcontext_pushed.send(self.app, _async_wrapper=self.app.ensure_sync)
def pop(self, exc: baseexception | none = _sentinel) -> none:
try:
if len(self._cv_tokens) == 1:
if exc is _sentinel:
exc = sys.exc_info()[1]
self.app.do_teardown_appcontext(exc)
finally:
ctx = _cv_app.get()
_cv_app.reset(self._cv_tokens.pop())
if ctx is not self:
raise assertionerror(
f"popped wrong app context. ({ctx!r} instead of {self!r})"
)
appcontext_popped.send(self.app, _async_wrapper=self.app.ensure_sync)
def __enter__(self) -> appcontext:
self.push()
return self
def __exit__(
self,
exc_type: type | none,
exc_value: baseexception | none,
tb: tracebacktype | none,
) -> none:
self.pop(exc_value)
class requestcontext:
def __init__(
self,
app: flask,
environ: wsgienvironment,
request: request | none = none,
session: sessionmixin | none = none,
) -> none:
self.app = app
if request is none:
request = app.request_class(environ)
request.json_module = app.json
self.request: request = request
self.url_adapter = none
try:
self.url_adapter = app.create_url_adapter(self.request)
except httpexception as e:
self.request.routing_exception = e
self.flashes: list[tuple[str, str]] | none = none
self.session: sessionmixin | none = session
self._after_request_functions: list[ft.afterrequestcallable[t.any]] = []
self._cv_tokens: list[
tuple[contextvars.token[requestcontext], appcontext | none]
] = []
def copy(self) -> requestcontext:
return self.__class__(
self.app,
environ=self.request.environ,
request=self.request,
session=self.session,
)
def match_request(self) -> none:
try:
result = self.url_adapter.match(return_rule=true)
self.request.url_rule, self.request.view_args = result
except httpexception as e:
self.request.routing_exception = e
def push(self) -> none:
app_ctx = _cv_app.get(none)
if app_ctx is none or app_ctx.app is not self.app:
app_ctx = self.app.app_context()
app_ctx.push()
else:
app_ctx = none
self._cv_tokens.append((_cv_request.set(self), app_ctx))
if self.session is none:
session_interface = self.app.session_interface
self.session = session_interface.open_session(self.app, self.request)
if self.session is none:
self.session = session_interface.make_null_session(self.app)
if self.url_adapter is not none:
self.match_request()
def pop(self, exc: baseexception | none = _sentinel) -> none:
clear_request = len(self._cv_tokens) == 1
try:
if clear_request:
if exc is _sentinel:
exc = sys.exc_info()[1]
self.app.do_teardown_request(exc)
request_close = getattr(self.request, "close", none)
if request_close is not none:
request_close()
finally:
ctx = _cv_request.get()
token, app_ctx = self._cv_tokens.pop()
_cv_request.reset(token)
if clear_request:
ctx.request.environ["werkzeug.request"] = none
if app_ctx is not none:
app_ctx.pop(exc)
if ctx is not self:
raise assertionerror(
f"popped wrong request context. ({ctx!r} instead of {self!r})"
)
def __enter__(self) -> requestcontext:
self.push()
return self
def __exit__(
self,
exc_type: type | none,
exc_value: baseexception | none,
tb: tracebacktype | none,
) -> none:
self.pop(exc_value)
def __repr__(self) -> str:
return (
f"<{type(self).__name__} {self.request.url!r}"
f" [{self.request.method}] of {self.app.name}>"
)