from __future__ import annotations
import importlib.util
import os
import pathlib
import sys
import typing as t
from collections import defaultdict
from functools import update_wrapper
from jinja2 import baseloader
from jinja2 import filesystemloader
from werkzeug.exceptions import default_exceptions
from werkzeug.exceptions import httpexception
from werkzeug.utils import cached_property
from .. import typing as ft
from ..helpers import get_root_path
from ..templating import _default_template_ctx_processor
if t.type_checking:
from click import group
_sentinel = object()
f = t.typevar("f", bound=t.callable[..., t.any])
t_after_request = t.typevar("t_after_request", bound=ft.afterrequestcallable[t.any])
t_before_request = t.typevar("t_before_request", bound=ft.beforerequestcallable)
t_error_handler = t.typevar("t_error_handler", bound=ft.errorhandlercallable)
t_teardown = t.typevar("t_teardown", bound=ft.teardowncallable)
t_template_context_processor = t.typevar(
"t_template_context_processor", bound=ft.templatecontextprocessorcallable
)
t_url_defaults = t.typevar("t_url_defaults", bound=ft.urldefaultcallable)
t_url_value_preprocessor = t.typevar(
"t_url_value_preprocessor", bound=ft.urlvaluepreprocessorcallable
)
t_route = t.typevar("t_route", bound=ft.routecallable)
def setupmethod(f: f) -> f:
f_name = f.__name__
def wrapper_func(self: scaffold, *args: t.any, **kwargs: t.any) -> t.any:
self._check_setup_finished(f_name)
return f(self, *args, **kwargs)
return t.cast(f, update_wrapper(wrapper_func, f))
class scaffold:
cli: group
name: str
_static_folder: str | none = none
_static_url_path: str | none = none
def __init__(
self,
import_name: str,
static_folder: str | os.pathlike[str] | none = none,
static_url_path: str | none = none,
template_folder: str | os.pathlike[str] | none = none,
root_path: str | none = none,
):
self.import_name = import_name
self.static_folder = static_folder
self.static_url_path = static_url_path
self.template_folder = template_folder
if root_path is none:
root_path = get_root_path(self.import_name)
self.root_path = root_path
self.view_functions: dict[str, ft.routecallable] = {}
self.error_handler_spec: dict[
ft.apporblueprintkey,
dict[int | none, dict[type[exception], ft.errorhandlercallable]],
] = defaultdict(lambda: defaultdict(dict))
self.before_request_funcs: dict[
ft.apporblueprintkey, list[ft.beforerequestcallable]
] = defaultdict(list)
self.after_request_funcs: dict[
ft.apporblueprintkey, list[ft.afterrequestcallable[t.any]]
] = defaultdict(list)
self.teardown_request_funcs: dict[
ft.apporblueprintkey, list[ft.teardowncallable]
] = defaultdict(list)
self.template_context_processors: dict[
ft.apporblueprintkey, list[ft.templatecontextprocessorcallable]
] = defaultdict(list, {none: [_default_template_ctx_processor]})
self.url_value_preprocessors: dict[
ft.apporblueprintkey,
list[ft.urlvaluepreprocessorcallable],
] = defaultdict(list)
self.url_default_functions: dict[
ft.apporblueprintkey, list[ft.urldefaultcallable]
] = defaultdict(list)
def __repr__(self) -> str:
return f"<{type(self).__name__} {self.name!r}>"
def _check_setup_finished(self, f_name: str) -> none:
raise notimplementederror
@property
def static_folder(self) -> str | none:
if self._static_folder is not none:
return os.path.join(self.root_path, self._static_folder)
else:
return none
@static_folder.setter
def static_folder(self, value: str | os.pathlike[str] | none) -> none:
if value is not none:
value = os.fspath(value).rstrip(r"\/")
self._static_folder = value
@property
def has_static_folder(self) -> bool:
return self.static_folder is not none
@property
def static_url_path(self) -> str | none:
if self._static_url_path is not none:
return self._static_url_path
if self.static_folder is not none:
basename = os.path.basename(self.static_folder)
return f"/{basename}".rstrip("/")
return none
@static_url_path.setter
def static_url_path(self, value: str | none) -> none:
if value is not none:
value = value.rstrip("/")
self._static_url_path = value
@cached_property
def jinja_loader(self) -> baseloader | none:
if self.template_folder is not none:
return filesystemloader(os.path.join(self.root_path, self.template_folder))
else:
return none
def _method_route(
self,
method: str,
rule: str,
options: dict[str, t.any],
) -> t.callable[[t_route], t_route]:
if "methods" in options:
raise typeerror("use the 'route' decorator to use the 'methods' argument.")
return self.route(rule, methods=[method], **options)
@setupmethod
def get(self, rule: str, **options: t.any) -> t.callable[[t_route], t_route]:
return self._method_route("get", rule, options)
@setupmethod
def post(self, rule: str, **options: t.any) -> t.callable[[t_route], t_route]:
return self._method_route("post", rule, options)
@setupmethod
def put(self, rule: str, **options: t.any) -> t.callable[[t_route], t_route]:
return self._method_route("put", rule, options)
@setupmethod
def delete(self, rule: str, **options: t.any) -> t.callable[[t_route], t_route]:
return self._method_route("delete", rule, options)
@setupmethod
def patch(self, rule: str, **options: t.any) -> t.callable[[t_route], t_route]:
return self._method_route("patch", rule, options)
@setupmethod
def route(self, rule: str, **options: t.any) -> t.callable[[t_route], t_route]:
def decorator(f: t_route) -> t_route:
endpoint = options.pop("endpoint", none)
self.add_url_rule(rule, endpoint, f, **options)
return f
return decorator
@setupmethod
def add_url_rule(
self,
rule: str,
endpoint: str | none = none,
view_func: ft.routecallable | none = none,
provide_automatic_options: bool | none = none,
**options: t.any,
) -> none:
raise notimplementederror
@setupmethod
def endpoint(self, endpoint: str) -> t.callable[[f], f]:
def decorator(f: f) -> f:
self.view_functions[endpoint] = f
return f
return decorator
@setupmethod
def before_request(self, f: t_before_request) -> t_before_request:
self.before_request_funcs.setdefault(none, []).append(f)
return f
@setupmethod
def after_request(self, f: t_after_request) -> t_after_request:
self.after_request_funcs.setdefault(none, []).append(f)
return f
@setupmethod
def teardown_request(self, f: t_teardown) -> t_teardown:
self.teardown_request_funcs.setdefault(none, []).append(f)
return f
@setupmethod
def context_processor(
self,
f: t_template_context_processor,
) -> t_template_context_processor:
self.template_context_processors[none].append(f)
return f
@setupmethod
def url_value_preprocessor(
self,
f: t_url_value_preprocessor,
) -> t_url_value_preprocessor:
self.url_value_preprocessors[none].append(f)
return f
@setupmethod
def url_defaults(self, f: t_url_defaults) -> t_url_defaults:
self.url_default_functions[none].append(f)
return f
@setupmethod
def errorhandler(
self, code_or_exception: type[exception] | int
) -> t.callable[[t_error_handler], t_error_handler]:
def decorator(f: t_error_handler) -> t_error_handler:
self.register_error_handler(code_or_exception, f)
return f
return decorator
@setupmethod
def register_error_handler(
self,
code_or_exception: type[exception] | int,
f: ft.errorhandlercallable,
) -> none:
exc_class, code = self._get_exc_class_and_code(code_or_exception)
self.error_handler_spec[none][code][exc_class] = f
@staticmethod
def _get_exc_class_and_code(
exc_class_or_code: type[exception] | int,
) -> tuple[type[exception], int | none]:
exc_class: type[exception]
if isinstance(exc_class_or_code, int):
try:
exc_class = default_exceptions[exc_class_or_code]
except keyerror:
raise valueerror(
f"'{exc_class_or_code}' is not a recognized http"
" error code. use a subclass of httpexception with"
" that code instead."
) from none
else:
exc_class = exc_class_or_code
if isinstance(exc_class, exception):
raise typeerror(
f"{exc_class!r} is an instance, not a class. handlers"
" can only be registered for exception classes or http"
" error codes."
)
if not issubclass(exc_class, exception):
raise valueerror(
f"'{exc_class.__name__}' is not a subclass of exception."
" handlers can only be registered for exception classes"
" or http error codes."
)
if issubclass(exc_class, httpexception):
return exc_class, exc_class.code
else:
return exc_class, none
def _endpoint_from_view_func(view_func: ft.routecallable) -> str:
assert view_func is not none, "expected view func if endpoint is not provided."
return view_func.__name__
def _find_package_path(import_name: str) -> str:
root_mod_name, _, _ = import_name.partition(".")
try:
root_spec = importlib.util.find_spec(root_mod_name)
if root_spec is none:
raise valueerror("not found")
except (importerror, valueerror):
return os.getcwd()
if root_spec.submodule_search_locations:
if root_spec.origin is none or root_spec.origin == "namespace":
package_spec = importlib.util.find_spec(import_name)
if package_spec is not none and package_spec.submodule_search_locations:
package_path = pathlib.path(
os.path.commonpath(package_spec.submodule_search_locations)
)
search_location = next(
location
for location in root_spec.submodule_search_locations
if package_path.is_relative_to(location)
)
else:
search_location = root_spec.submodule_search_locations[0]
return os.path.dirname(search_location)
else:
return os.path.dirname(os.path.dirname(root_spec.origin))
else:
return os.path.dirname(root_spec.origin)
def find_package(import_name: str) -> tuple[str | none, str]:
package_path = _find_package_path(import_name)
py_prefix = os.path.abspath(sys.prefix)
if pathlib.purepath(package_path).is_relative_to(py_prefix):
return py_prefix, package_path
site_parent, site_folder = os.path.split(package_path)
if site_folder.lower() == "site-packages":
parent, folder = os.path.split(site_parent)
if folder.lower() == "lib":
return parent, package_path
if os.path.basename(parent).lower() == "lib":
return os.path.dirname(parent), package_path
return site_parent, package_path
return none, package_path