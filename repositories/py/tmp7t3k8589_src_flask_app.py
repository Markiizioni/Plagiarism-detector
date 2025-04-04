from __future__ import annotations
import collections.abc as cabc
import os
import sys
import typing as t
import weakref
from datetime import timedelta
from inspect import iscoroutinefunction
from itertools import chain
from types import tracebacktype
from urllib.parse import quote as _url_quote
import click
from werkzeug.datastructures import headers
from werkzeug.datastructures import immutabledict
from werkzeug.exceptions import badrequestkeyerror
from werkzeug.exceptions import httpexception
from werkzeug.exceptions import internalservererror
from werkzeug.routing import builderror
from werkzeug.routing import mapadapter
from werkzeug.routing import requestredirect
from werkzeug.routing import routingexception
from werkzeug.routing import rule
from werkzeug.serving import is_running_from_reloader
from werkzeug.wrappers import response as baseresponse
from werkzeug.wsgi import get_host
from . import cli
from . import typing as ft
from .ctx import appcontext
from .ctx import requestcontext
from .globals import _cv_app
from .globals import _cv_request
from .globals import current_app
from .globals import g
from .globals import request
from .globals import request_ctx
from .globals import session
from .helpers import get_debug_flag
from .helpers import get_flashed_messages
from .helpers import get_load_dotenv
from .helpers import send_from_directory
from .sansio.app import app
from .sansio.scaffold import _sentinel
from .sessions import securecookiesessioninterface
from .sessions import sessioninterface
from .signals import appcontext_tearing_down
from .signals import got_request_exception
from .signals import request_finished
from .signals import request_started
from .signals import request_tearing_down
from .templating import environment
from .wrappers import request
from .wrappers import response
if t.type_checking:
from _typeshed.wsgi import startresponse
from _typeshed.wsgi import wsgienvironment
from .testing import flaskclient
from .testing import flaskclirunner
from .typing import headersvalue
t_shell_context_processor = t.typevar(
"t_shell_context_processor", bound=ft.shellcontextprocessorcallable
)
t_teardown = t.typevar("t_teardown", bound=ft.teardowncallable)
t_template_filter = t.typevar("t_template_filter", bound=ft.templatefiltercallable)
t_template_global = t.typevar("t_template_global", bound=ft.templateglobalcallable)
t_template_test = t.typevar("t_template_test", bound=ft.templatetestcallable)
def _make_timedelta(value: timedelta | int | none) -> timedelta | none:
if value is none or isinstance(value, timedelta):
return value
return timedelta(seconds=value)
class flask(app):
default_config = immutabledict(
{
"debug": none,
"testing": false,
"propagate_exceptions": none,
"secret_key": none,
"secret_key_fallbacks": none,
"permanent_session_lifetime": timedelta(days=31),
"use_x_sendfile": false,
"trusted_hosts": none,
"server_name": none,
"application_root": "/",
"session_cookie_name": "session",
"session_cookie_domain": none,
"session_cookie_path": none,
"session_cookie_httponly": true,
"session_cookie_secure": false,
"session_cookie_partitioned": false,
"session_cookie_samesite": none,
"session_refresh_each_request": true,
"max_content_length": none,
"max_form_memory_size": 500_000,
"max_form_parts": 1_000,
"send_file_max_age_default": none,
"trap_bad_request_errors": none,
"trap_http_exceptions": false,
"explain_template_loading": false,
"preferred_url_scheme": "http",
"templates_auto_reload": none,
"max_cookie_size": 4093,
"provide_automatic_options": true,
}
)
request_class: type[request] = request
response_class: type[response] = response
session_interface: sessioninterface = securecookiesessioninterface()
def __init__(
self,
import_name: str,
static_url_path: str | none = none,
static_folder: str | os.pathlike[str] | none = "static",
static_host: str | none = none,
host_matching: bool = false,
subdomain_matching: bool = false,
template_folder: str | os.pathlike[str] | none = "templates",
instance_path: str | none = none,
instance_relative_config: bool = false,
root_path: str | none = none,
):
super().__init__(
import_name=import_name,
static_url_path=static_url_path,
static_folder=static_folder,
static_host=static_host,
host_matching=host_matching,
subdomain_matching=subdomain_matching,
template_folder=template_folder,
instance_path=instance_path,
instance_relative_config=instance_relative_config,
root_path=root_path,
)
self.cli = cli.appgroup()
self.cli.name = self.name
if self.has_static_folder:
assert bool(static_host) == host_matching, (
"invalid static_host/host_matching combination"
)
self_ref = weakref.ref(self)
self.add_url_rule(
f"{self.static_url_path}/<path:filename>",
endpoint="static",
host=static_host,
view_func=lambda **kw: self_ref().send_static_file(**kw),
)
def get_send_file_max_age(self, filename: str | none) -> int | none:
value = current_app.config["send_file_max_age_default"]
if value is none:
return none
if isinstance(value, timedelta):
return int(value.total_seconds())
return value
def send_static_file(self, filename: str) -> response:
if not self.has_static_folder:
raise runtimeerror("'static_folder' must be set to serve static_files.")
max_age = self.get_send_file_max_age(filename)
return send_from_directory(
t.cast(str, self.static_folder), filename, max_age=max_age
)
def open_resource(
self, resource: str, mode: str = "rb", encoding: str | none = none
) -> t.io[t.anystr]:
if mode not in {"r", "rt", "rb"}:
raise valueerror("resources can only be opened for reading.")
path = os.path.join(self.root_path, resource)
if mode == "rb":
return open(path, mode)
return open(path, mode, encoding=encoding)
def open_instance_resource(
self, resource: str, mode: str = "rb", encoding: str | none = "utf-8"
) -> t.io[t.anystr]:
path = os.path.join(self.instance_path, resource)
if "b" in mode:
return open(path, mode)
return open(path, mode, encoding=encoding)
def create_jinja_environment(self) -> environment:
options = dict(self.jinja_options)
if "autoescape" not in options:
options["autoescape"] = self.select_jinja_autoescape
if "auto_reload" not in options:
auto_reload = self.config["templates_auto_reload"]
if auto_reload is none:
auto_reload = self.debug
options["auto_reload"] = auto_reload
rv = self.jinja_environment(self, **options)
rv.globals.update(
url_for=self.url_for,
get_flashed_messages=get_flashed_messages,
config=self.config,
request=request,
session=session,
g=g,
)
rv.policies["json.dumps_function"] = self.json.dumps
return rv
def create_url_adapter(self, request: request | none) -> mapadapter | none:
if request is not none:
if (trusted_hosts := self.config["trusted_hosts"]) is not none:
request.trusted_hosts = trusted_hosts
request.host = get_host(request.environ, request.trusted_hosts)
subdomain = none
server_name = self.config["server_name"]
if self.url_map.host_matching:
server_name = none
elif not self.subdomain_matching:
subdomain = self.url_map.default_subdomain or ""
return self.url_map.bind_to_environ(
request.environ, server_name=server_name, subdomain=subdomain
)
if self.config["server_name"] is not none:
return self.url_map.bind(
self.config["server_name"],
script_name=self.config["application_root"],
url_scheme=self.config["preferred_url_scheme"],
)
return none
def raise_routing_exception(self, request: request) -> t.noreturn:
if (
not self.debug
or not isinstance(request.routing_exception, requestredirect)
or request.routing_exception.code in {307, 308}
or request.method in {"get", "head", "options"}
):
raise request.routing_exception
from .debughelpers import formdataroutingredirect
raise formdataroutingredirect(request)
def update_template_context(self, context: dict[str, t.any]) -> none:
names: t.iterable[str | none] = (none,)
if request:
names = chain(names, reversed(request.blueprints))
orig_ctx = context.copy()
for name in names:
if name in self.template_context_processors:
for func in self.template_context_processors[name]:
context.update(self.ensure_sync(func)())
context.update(orig_ctx)
def make_shell_context(self) -> dict[str, t.any]:
rv = {"app": self, "g": g}
for processor in self.shell_context_processors:
rv.update(processor())
return rv
def run(
self,
host: str | none = none,
port: int | none = none,
debug: bool | none = none,
load_dotenv: bool = true,
**options: t.any,
) -> none:
if os.environ.get("flask_run_from_cli") == "true":
if not is_running_from_reloader():
click.secho(
" * ignoring a call to 'app.run()' that would block"
" the current 'flask' cli command.\n"
"   only call 'app.run()' in an 'if __name__ =="
' "__main__"\' guard.',
fg="red",
)
return
if get_load_dotenv(load_dotenv):
cli.load_dotenv()
if "flask_debug" in os.environ:
self.debug = get_debug_flag()
if debug is not none:
self.debug = bool(debug)
server_name = self.config.get("server_name")
sn_host = sn_port = none
if server_name:
sn_host, _, sn_port = server_name.partition(":")
if not host:
if sn_host:
host = sn_host
else:
host = "127.0.0.1"
if port or port == 0:
port = int(port)
elif sn_port:
port = int(sn_port)
else:
port = 5000
options.setdefault("use_reloader", self.debug)
options.setdefault("use_debugger", self.debug)
options.setdefault("threaded", true)
cli.show_server_banner(self.debug, self.name)
from werkzeug.serving import run_simple
try:
run_simple(t.cast(str, host), port, self, **options)
finally:
self._got_first_request = false
def test_client(self, use_cookies: bool = true, **kwargs: t.any) -> flaskclient:
cls = self.test_client_class
if cls is none:
from .testing import flaskclient as cls
return cls(
self, self.response_class, use_cookies=use_cookies, **kwargs
)
def test_cli_runner(self, **kwargs: t.any) -> flaskclirunner:
cls = self.test_cli_runner_class
if cls is none:
from .testing import flaskclirunner as cls
return cls(self, **kwargs)
def handle_http_exception(
self, e: httpexception
) -> httpexception | ft.responsereturnvalue:
if e.code is none:
return e
if isinstance(e, routingexception):
return e
handler = self._find_error_handler(e, request.blueprints)
if handler is none:
return e
return self.ensure_sync(handler)(e)
def handle_user_exception(
self, e: exception
) -> httpexception | ft.responsereturnvalue:
if isinstance(e, badrequestkeyerror) and (
self.debug or self.config["trap_bad_request_errors"]
):
e.show_exception = true
if isinstance(e, httpexception) and not self.trap_http_exception(e):
return self.handle_http_exception(e)
handler = self._find_error_handler(e, request.blueprints)
if handler is none:
raise
return self.ensure_sync(handler)(e)
def handle_exception(self, e: exception) -> response:
exc_info = sys.exc_info()
got_request_exception.send(self, _async_wrapper=self.ensure_sync, exception=e)
propagate = self.config["propagate_exceptions"]
if propagate is none:
propagate = self.testing or self.debug
if propagate:
if exc_info[1] is e:
raise
raise e
self.log_exception(exc_info)
server_error: internalservererror | ft.responsereturnvalue
server_error = internalservererror(original_exception=e)
handler = self._find_error_handler(server_error, request.blueprints)
if handler is not none:
server_error = self.ensure_sync(handler)(server_error)
return self.finalize_request(server_error, from_error_handler=true)
def log_exception(
self,
exc_info: (tuple[type, baseexception, tracebacktype] | tuple[none, none, none]),
) -> none:
self.logger.error(
f"exception on {request.path} [{request.method}]", exc_info=exc_info
)
def dispatch_request(self) -> ft.responsereturnvalue:
req = request_ctx.request
if req.routing_exception is not none:
self.raise_routing_exception(req)
rule: rule = req.url_rule
if (
getattr(rule, "provide_automatic_options", false)
and req.method == "options"
):
return self.make_default_options_response()
view_args: dict[str, t.any] = req.view_args
return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)
def full_dispatch_request(self) -> response:
self._got_first_request = true
try:
request_started.send(self, _async_wrapper=self.ensure_sync)
rv = self.preprocess_request()
if rv is none:
rv = self.dispatch_request()
except exception as e:
rv = self.handle_user_exception(e)
return self.finalize_request(rv)
def finalize_request(
self,
rv: ft.responsereturnvalue | httpexception,
from_error_handler: bool = false,
) -> response:
response = self.make_response(rv)
try:
response = self.process_response(response)
request_finished.send(
self, _async_wrapper=self.ensure_sync, response=response
)
except exception:
if not from_error_handler:
raise
self.logger.exception(
"request finalizing failed with an error while handling an error"
)
return response
def make_default_options_response(self) -> response:
adapter = request_ctx.url_adapter
methods = adapter.allowed_methods()
rv = self.response_class()
rv.allow.update(methods)
return rv
def ensure_sync(self, func: t.callable[..., t.any]) -> t.callable[..., t.any]:
if iscoroutinefunction(func):
return self.async_to_sync(func)
return func
def async_to_sync(
self, func: t.callable[..., t.coroutine[t.any, t.any, t.any]]
) -> t.callable[..., t.any]:
try:
from asgiref.sync import async_to_sync as asgiref_async_to_sync
except importerror:
raise runtimeerror(
"install flask with the 'async' extra in order to use async views."
) from none
return asgiref_async_to_sync(func)
def url_for(
self,
/,
endpoint: str,
*,
_anchor: str | none = none,
_method: str | none = none,
_scheme: str | none = none,
_external: bool | none = none,
**values: t.any,
) -> str:
req_ctx = _cv_request.get(none)
if req_ctx is not none:
url_adapter = req_ctx.url_adapter
blueprint_name = req_ctx.request.blueprint
if endpoint[:1] == ".":
if blueprint_name is not none:
endpoint = f"{blueprint_name}{endpoint}"
else:
endpoint = endpoint[1:]
if _external is none:
_external = _scheme is not none
else:
app_ctx = _cv_app.get(none)
if app_ctx is not none:
url_adapter = app_ctx.url_adapter
else:
url_adapter = self.create_url_adapter(none)
if url_adapter is none:
raise runtimeerror(
"unable to build urls outside an active request"
" without 'server_name' configured. also configure"
" 'application_root' and 'preferred_url_scheme' as"
" needed."
)
if _external is none:
_external = true
if _scheme is not none and not _external:
raise valueerror("when specifying '_scheme', '_external' must be true.")
self.inject_url_defaults(endpoint, values)
try:
rv = url_adapter.build(
endpoint,
values,
method=_method,
url_scheme=_scheme,
force_external=_external,
)
except builderror as error:
values.update(
_anchor=_anchor, _method=_method, _scheme=_scheme, _external=_external
)
return self.handle_url_build_error(error, endpoint, values)
if _anchor is not none:
_anchor = _url_quote(_anchor, safe="%!
rv = f"{rv}
return rv
def make_response(self, rv: ft.responsereturnvalue) -> response:
status: int | none = none
headers: headersvalue | none = none
if isinstance(rv, tuple):
len_rv = len(rv)
if len_rv == 3:
rv, status, headers = rv
elif len_rv == 2:
if isinstance(rv[1], (headers, dict, tuple, list)):
rv, headers = rv
else:
rv, status = rv
else:
raise typeerror(
"the view function did not return a valid response tuple."
" the tuple must have the form (body, status, headers),"
" (body, status), or (body, headers)."
)
if rv is none:
raise typeerror(
f"the view function for {request.endpoint!r} did not"
" return a valid response. the function either returned"
" none or ended without a return statement."
)
if not isinstance(rv, self.response_class):
if isinstance(rv, (str, bytes, bytearray)) or isinstance(rv, cabc.iterator):
rv = self.response_class(
rv,
status=status,
headers=headers,
)
status = headers = none
elif isinstance(rv, (dict, list)):
rv = self.json.response(rv)
elif isinstance(rv, baseresponse) or callable(rv):
try:
rv = self.response_class.force_type(
rv,
request.environ,
)
except typeerror as e:
raise typeerror(
f"{e}\nthe view function did not return a valid"
" response. the return type must be a string,"
" dict, list, tuple with headers or status,"
" response instance, or wsgi callable, but it"
f" was a {type(rv).__name__}."
).with_traceback(sys.exc_info()[2]) from none
else:
raise typeerror(
"the view function did not return a valid"
" response. the return type must be a string,"
" dict, list, tuple with headers or status,"
" response instance, or wsgi callable, but it was a"
f" {type(rv).__name__}."
)
rv = t.cast(response, rv)
if status is not none:
if isinstance(status, (str, bytes, bytearray)):
rv.status = status
else:
rv.status_code = status
if headers:
rv.headers.update(headers)
return rv
def preprocess_request(self) -> ft.responsereturnvalue | none:
names = (none, *reversed(request.blueprints))
for name in names:
if name in self.url_value_preprocessors:
for url_func in self.url_value_preprocessors[name]:
url_func(request.endpoint, request.view_args)
for name in names:
if name in self.before_request_funcs:
for before_func in self.before_request_funcs[name]:
rv = self.ensure_sync(before_func)()
if rv is not none:
return rv
return none
def process_response(self, response: response) -> response:
ctx = request_ctx._get_current_object()
for func in ctx._after_request_functions:
response = self.ensure_sync(func)(response)
for name in chain(request.blueprints, (none,)):
if name in self.after_request_funcs:
for func in reversed(self.after_request_funcs[name]):
response = self.ensure_sync(func)(response)
if not self.session_interface.is_null_session(ctx.session):
self.session_interface.save_session(self, ctx.session, response)
return response
def do_teardown_request(
self,
exc: baseexception | none = _sentinel,
) -> none:
if exc is _sentinel:
exc = sys.exc_info()[1]
for name in chain(request.blueprints, (none,)):
if name in self.teardown_request_funcs:
for func in reversed(self.teardown_request_funcs[name]):
self.ensure_sync(func)(exc)
request_tearing_down.send(self, _async_wrapper=self.ensure_sync, exc=exc)
def do_teardown_appcontext(
self,
exc: baseexception | none = _sentinel,
) -> none:
if exc is _sentinel:
exc = sys.exc_info()[1]
for func in reversed(self.teardown_appcontext_funcs):
self.ensure_sync(func)(exc)
appcontext_tearing_down.send(self, _async_wrapper=self.ensure_sync, exc=exc)
def app_context(self) -> appcontext:
return appcontext(self)
def request_context(self, environ: wsgienvironment) -> requestcontext:
return requestcontext(self, environ)
def test_request_context(self, *args: t.any, **kwargs: t.any) -> requestcontext:
from .testing import environbuilder
builder = environbuilder(self, *args, **kwargs)
try:
return self.request_context(builder.get_environ())
finally:
builder.close()
def wsgi_app(
self, environ: wsgienvironment, start_response: startresponse
) -> cabc.iterable[bytes]:
ctx = self.request_context(environ)
error: baseexception | none = none
try:
try:
ctx.push()
response = self.full_dispatch_request()
except exception as e:
error = e
response = self.handle_exception(e)
except:
error = sys.exc_info()[1]
raise
return response(environ, start_response)
finally:
if "werkzeug.debug.preserve_context" in environ:
environ["werkzeug.debug.preserve_context"](_cv_app.get())
environ["werkzeug.debug.preserve_context"](_cv_request.get())
if error is not none and self.should_ignore_error(error):
error = none
ctx.pop(error)
def __call__(
self, environ: wsgienvironment, start_response: startresponse
) -> cabc.iterable[bytes]:
return self.wsgi_app(environ, start_response)