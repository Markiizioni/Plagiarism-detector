from __future__ import annotations
import logging
import os
import sys
import typing as t
from datetime import timedelta
from itertools import chain
from werkzeug.exceptions import aborter
from werkzeug.exceptions import badrequest
from werkzeug.exceptions import badrequestkeyerror
from werkzeug.routing import builderror
from werkzeug.routing import map
from werkzeug.routing import rule
from werkzeug.sansio.response import response
from werkzeug.utils import cached_property
from werkzeug.utils import redirect as _wz_redirect
from .. import typing as ft
from ..config import config
from ..config import configattribute
from ..ctx import _appctxglobals
from ..helpers import _split_blueprint_path
from ..helpers import get_debug_flag
from ..json.provider import defaultjsonprovider
from ..json.provider import jsonprovider
from ..logging import create_logger
from ..templating import dispatchingjinjaloader
from ..templating import environment
from .scaffold import _endpoint_from_view_func
from .scaffold import find_package
from .scaffold import scaffold
from .scaffold import setupmethod
if t.type_checking:
from werkzeug.wrappers import response as baseresponse
from ..testing import flaskclient
from ..testing import flaskclirunner
from .blueprints import blueprint
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
class app(scaffold):
aborter_class = aborter
jinja_environment = environment
app_ctx_globals_class = _appctxglobals
config_class = config
testing = configattribute[bool]("testing")
secret_key = configattribute[t.union[str, bytes, none]]("secret_key")
permanent_session_lifetime = configattribute[timedelta](
"permanent_session_lifetime",
get_converter=_make_timedelta,
)
json_provider_class: type[jsonprovider] = defaultjsonprovider
jinja_options: dict[str, t.any] = {}
url_rule_class = rule
url_map_class = map
test_client_class: type[flaskclient] | none = none
test_cli_runner_class: type[flaskclirunner] | none = none
default_config: dict[str, t.any]
response_class: type[response]
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
) -> none:
super().__init__(
import_name=import_name,
static_folder=static_folder,
static_url_path=static_url_path,
template_folder=template_folder,
root_path=root_path,
)
if instance_path is none:
instance_path = self.auto_find_instance_path()
elif not os.path.isabs(instance_path):
raise valueerror(
"if an instance path is provided it must be absolute."
" a relative path was given instead."
)
self.instance_path = instance_path
self.config = self.make_config(instance_relative_config)
self.aborter = self.make_aborter()
self.json: jsonprovider = self.json_provider_class(self)
self.url_build_error_handlers: list[
t.callable[[exception, str, dict[str, t.any]], str]
] = []
self.teardown_appcontext_funcs: list[ft.teardowncallable] = []
self.shell_context_processors: list[ft.shellcontextprocessorcallable] = []
self.blueprints: dict[str, blueprint] = {}
self.extensions: dict[str, t.any] = {}
self.url_map = self.url_map_class(host_matching=host_matching)
self.subdomain_matching = subdomain_matching
self._got_first_request = false
def _check_setup_finished(self, f_name: str) -> none:
if self._got_first_request:
raise assertionerror(
f"the setup method '{f_name}' can no longer be called"
" on the application. it has already handled its first"
" request, any changes will not be applied"
" consistently.\n"
"make sure all imports, decorators, functions, etc."
" needed to set up the application are done before"
" running it."
)
@cached_property
def name(self) -> str:
if self.import_name == "__main__":
fn: str | none = getattr(sys.modules["__main__"], "__file__", none)
if fn is none:
return "__main__"
return os.path.splitext(os.path.basename(fn))[0]
return self.import_name
@cached_property
def logger(self) -> logging.logger:
return create_logger(self)
@cached_property
def jinja_env(self) -> environment:
return self.create_jinja_environment()
def create_jinja_environment(self) -> environment:
raise notimplementederror()
def make_config(self, instance_relative: bool = false) -> config:
root_path = self.root_path
if instance_relative:
root_path = self.instance_path
defaults = dict(self.default_config)
defaults["debug"] = get_debug_flag()
return self.config_class(root_path, defaults)
def make_aborter(self) -> aborter:
return self.aborter_class()
def auto_find_instance_path(self) -> str:
prefix, package_path = find_package(self.import_name)
if prefix is none:
return os.path.join(package_path, "instance")
return os.path.join(prefix, "var", f"{self.name}-instance")
def create_global_jinja_loader(self) -> dispatchingjinjaloader:
return dispatchingjinjaloader(self)
def select_jinja_autoescape(self, filename: str) -> bool:
if filename is none:
return true
return filename.endswith((".html", ".htm", ".xml", ".xhtml", ".svg"))
@property
def debug(self) -> bool:
return self.config["debug"]
@debug.setter
def debug(self, value: bool) -> none:
self.config["debug"] = value
if self.config["templates_auto_reload"] is none:
self.jinja_env.auto_reload = value
@setupmethod
def register_blueprint(self, blueprint: blueprint, **options: t.any) -> none:
blueprint.register(self, options)
def iter_blueprints(self) -> t.valuesview[blueprint]:
return self.blueprints.values()
@setupmethod
def add_url_rule(
self,
rule: str,
endpoint: str | none = none,
view_func: ft.routecallable | none = none,
provide_automatic_options: bool | none = none,
**options: t.any,
) -> none:
if endpoint is none:
endpoint = _endpoint_from_view_func(view_func)
options["endpoint"] = endpoint
methods = options.pop("methods", none)
if methods is none:
methods = getattr(view_func, "methods", none) or ("get",)
if isinstance(methods, str):
raise typeerror(
"allowed methods must be a list of strings, for"
' example: @app.route(..., methods=["post"])'
)
methods = {item.upper() for item in methods}
required_methods: set[str] = set(getattr(view_func, "required_methods", ()))
if provide_automatic_options is none:
provide_automatic_options = getattr(
view_func, "provide_automatic_options", none
)
if provide_automatic_options is none:
if "options" not in methods and self.config["provide_automatic_options"]:
provide_automatic_options = true
required_methods.add("options")
else:
provide_automatic_options = false
methods |= required_methods
rule_obj = self.url_rule_class(rule, methods=methods, **options)
rule_obj.provide_automatic_options = provide_automatic_options
self.url_map.add(rule_obj)
if view_func is not none:
old_func = self.view_functions.get(endpoint)
if old_func is not none and old_func != view_func:
raise assertionerror(
"view function mapping is overwriting an existing"
f" endpoint function: {endpoint}"
)
self.view_functions[endpoint] = view_func
@setupmethod
def template_filter(
self, name: str | none = none
) -> t.callable[[t_template_filter], t_template_filter]:
def decorator(f: t_template_filter) -> t_template_filter:
self.add_template_filter(f, name=name)
return f
return decorator
@setupmethod
def add_template_filter(
self, f: ft.templatefiltercallable, name: str | none = none
) -> none:
self.jinja_env.filters[name or f.__name__] = f
@setupmethod
def template_test(
self, name: str | none = none
) -> t.callable[[t_template_test], t_template_test]:
def decorator(f: t_template_test) -> t_template_test:
self.add_template_test(f, name=name)
return f
return decorator
@setupmethod
def add_template_test(
self, f: ft.templatetestcallable, name: str | none = none
) -> none:
self.jinja_env.tests[name or f.__name__] = f
@setupmethod
def template_global(
self, name: str | none = none
) -> t.callable[[t_template_global], t_template_global]:
def decorator(f: t_template_global) -> t_template_global:
self.add_template_global(f, name=name)
return f
return decorator
@setupmethod
def add_template_global(
self, f: ft.templateglobalcallable, name: str | none = none
) -> none:
self.jinja_env.globals[name or f.__name__] = f
@setupmethod
def teardown_appcontext(self, f: t_teardown) -> t_teardown:
self.teardown_appcontext_funcs.append(f)
return f
@setupmethod
def shell_context_processor(
self, f: t_shell_context_processor
) -> t_shell_context_processor:
self.shell_context_processors.append(f)
return f
def _find_error_handler(
self, e: exception, blueprints: list[str]
) -> ft.errorhandlercallable | none:
exc_class, code = self._get_exc_class_and_code(type(e))
names = (*blueprints, none)
for c in (code, none) if code is not none else (none,):
for name in names:
handler_map = self.error_handler_spec[name][c]
if not handler_map:
continue
for cls in exc_class.__mro__:
handler = handler_map.get(cls)
if handler is not none:
return handler
return none
def trap_http_exception(self, e: exception) -> bool:
if self.config["trap_http_exceptions"]:
return true
trap_bad_request = self.config["trap_bad_request_errors"]
if (
trap_bad_request is none
and self.debug
and isinstance(e, badrequestkeyerror)
):
return true
if trap_bad_request:
return isinstance(e, badrequest)
return false
def should_ignore_error(self, error: baseexception | none) -> bool:
return false
def redirect(self, location: str, code: int = 302) -> baseresponse:
return _wz_redirect(
location,
code=code,
response=self.response_class,
)
def inject_url_defaults(self, endpoint: str, values: dict[str, t.any]) -> none:
names: t.iterable[str | none] = (none,)
if "." in endpoint:
names = chain(
names, reversed(_split_blueprint_path(endpoint.rpartition(".")[0]))
)
for name in names:
if name in self.url_default_functions:
for func in self.url_default_functions[name]:
func(endpoint, values)
def handle_url_build_error(
self, error: builderror, endpoint: str, values: dict[str, t.any]
) -> str:
for handler in self.url_build_error_handlers:
try:
rv = handler(error, endpoint, values)
except builderror as e:
error = e
else:
if rv is not none:
return rv
if error is sys.exc_info()[1]:
raise
raise error