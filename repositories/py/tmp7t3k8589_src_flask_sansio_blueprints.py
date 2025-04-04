from __future__ import annotations
import os
import typing as t
from collections import defaultdict
from functools import update_wrapper
from .. import typing as ft
from .scaffold import _endpoint_from_view_func
from .scaffold import _sentinel
from .scaffold import scaffold
from .scaffold import setupmethod
if t.type_checking:
from .app import app
deferredsetupfunction = t.callable[["blueprintsetupstate"], none]
t_after_request = t.typevar("t_after_request", bound=ft.afterrequestcallable[t.any])
t_before_request = t.typevar("t_before_request", bound=ft.beforerequestcallable)
t_error_handler = t.typevar("t_error_handler", bound=ft.errorhandlercallable)
t_teardown = t.typevar("t_teardown", bound=ft.teardowncallable)
t_template_context_processor = t.typevar(
"t_template_context_processor", bound=ft.templatecontextprocessorcallable
)
t_template_filter = t.typevar("t_template_filter", bound=ft.templatefiltercallable)
t_template_global = t.typevar("t_template_global", bound=ft.templateglobalcallable)
t_template_test = t.typevar("t_template_test", bound=ft.templatetestcallable)
t_url_defaults = t.typevar("t_url_defaults", bound=ft.urldefaultcallable)
t_url_value_preprocessor = t.typevar(
"t_url_value_preprocessor", bound=ft.urlvaluepreprocessorcallable
)
class blueprintsetupstate:
def __init__(
self,
blueprint: blueprint,
app: app,
options: t.any,
first_registration: bool,
) -> none:
self.app = app
self.blueprint = blueprint
self.options = options
self.first_registration = first_registration
subdomain = self.options.get("subdomain")
if subdomain is none:
subdomain = self.blueprint.subdomain
self.subdomain = subdomain
url_prefix = self.options.get("url_prefix")
if url_prefix is none:
url_prefix = self.blueprint.url_prefix
self.url_prefix = url_prefix
self.name = self.options.get("name", blueprint.name)
self.name_prefix = self.options.get("name_prefix", "")
self.url_defaults = dict(self.blueprint.url_values_defaults)
self.url_defaults.update(self.options.get("url_defaults", ()))
def add_url_rule(
self,
rule: str,
endpoint: str | none = none,
view_func: ft.routecallable | none = none,
**options: t.any,
) -> none:
if self.url_prefix is not none:
if rule:
rule = "/".join((self.url_prefix.rstrip("/"), rule.lstrip("/")))
else:
rule = self.url_prefix
options.setdefault("subdomain", self.subdomain)
if endpoint is none:
endpoint = _endpoint_from_view_func(view_func)
defaults = self.url_defaults
if "defaults" in options:
defaults = dict(defaults, **options.pop("defaults"))
self.app.add_url_rule(
rule,
f"{self.name_prefix}.{self.name}.{endpoint}".lstrip("."),
view_func,
defaults=defaults,
**options,
)
class blueprint(scaffold):
_got_registered_once = false
def __init__(
self,
name: str,
import_name: str,
static_folder: str | os.pathlike[str] | none = none,
static_url_path: str | none = none,
template_folder: str | os.pathlike[str] | none = none,
url_prefix: str | none = none,
subdomain: str | none = none,
url_defaults: dict[str, t.any] | none = none,
root_path: str | none = none,
cli_group: str | none = _sentinel,
):
super().__init__(
import_name=import_name,
static_folder=static_folder,
static_url_path=static_url_path,
template_folder=template_folder,
root_path=root_path,
)
if not name:
raise valueerror("'name' may not be empty.")
if "." in name:
raise valueerror("'name' may not contain a dot '.' character.")
self.name = name
self.url_prefix = url_prefix
self.subdomain = subdomain
self.deferred_functions: list[deferredsetupfunction] = []
if url_defaults is none:
url_defaults = {}
self.url_values_defaults = url_defaults
self.cli_group = cli_group
self._blueprints: list[tuple[blueprint, dict[str, t.any]]] = []
def _check_setup_finished(self, f_name: str) -> none:
if self._got_registered_once:
raise assertionerror(
f"the setup method '{f_name}' can no longer be called on the blueprint"
f" '{self.name}'. it has already been registered at least once, any"
" changes will not be applied consistently.\n"
"make sure all imports, decorators, functions, etc. needed to set up"
" the blueprint are done before registering it."
)
@setupmethod
def record(self, func: deferredsetupfunction) -> none:
self.deferred_functions.append(func)
@setupmethod
def record_once(self, func: deferredsetupfunction) -> none:
def wrapper(state: blueprintsetupstate) -> none:
if state.first_registration:
func(state)
self.record(update_wrapper(wrapper, func))
def make_setup_state(
self, app: app, options: dict[str, t.any], first_registration: bool = false
) -> blueprintsetupstate:
return blueprintsetupstate(self, app, options, first_registration)
@setupmethod
def register_blueprint(self, blueprint: blueprint, **options: t.any) -> none:
if blueprint is self:
raise valueerror("cannot register a blueprint on itself")
self._blueprints.append((blueprint, options))
def register(self, app: app, options: dict[str, t.any]) -> none:
name_prefix = options.get("name_prefix", "")
self_name = options.get("name", self.name)
name = f"{name_prefix}.{self_name}".lstrip(".")
if name in app.blueprints:
bp_desc = "this" if app.blueprints[name] is self else "a different"
existing_at = f" '{name}'" if self_name != name else ""
raise valueerror(
f"the name '{self_name}' is already registered for"
f" {bp_desc} blueprint{existing_at}. use 'name=' to"
f" provide a unique name."
)
first_bp_registration = not any(bp is self for bp in app.blueprints.values())
first_name_registration = name not in app.blueprints
app.blueprints[name] = self
self._got_registered_once = true
state = self.make_setup_state(app, options, first_bp_registration)
if self.has_static_folder:
state.add_url_rule(
f"{self.static_url_path}/<path:filename>",
view_func=self.send_static_file,
endpoint="static",
)
if first_bp_registration or first_name_registration:
self._merge_blueprint_funcs(app, name)
for deferred in self.deferred_functions:
deferred(state)
cli_resolved_group = options.get("cli_group", self.cli_group)
if self.cli.commands:
if cli_resolved_group is none:
app.cli.commands.update(self.cli.commands)
elif cli_resolved_group is _sentinel:
self.cli.name = name
app.cli.add_command(self.cli)
else:
self.cli.name = cli_resolved_group
app.cli.add_command(self.cli)
for blueprint, bp_options in self._blueprints:
bp_options = bp_options.copy()
bp_url_prefix = bp_options.get("url_prefix")
bp_subdomain = bp_options.get("subdomain")
if bp_subdomain is none:
bp_subdomain = blueprint.subdomain
if state.subdomain is not none and bp_subdomain is not none:
bp_options["subdomain"] = bp_subdomain + "." + state.subdomain
elif bp_subdomain is not none:
bp_options["subdomain"] = bp_subdomain
elif state.subdomain is not none:
bp_options["subdomain"] = state.subdomain
if bp_url_prefix is none:
bp_url_prefix = blueprint.url_prefix
if state.url_prefix is not none and bp_url_prefix is not none:
bp_options["url_prefix"] = (
state.url_prefix.rstrip("/") + "/" + bp_url_prefix.lstrip("/")
)
elif bp_url_prefix is not none:
bp_options["url_prefix"] = bp_url_prefix
elif state.url_prefix is not none:
bp_options["url_prefix"] = state.url_prefix
bp_options["name_prefix"] = name
blueprint.register(app, bp_options)
def _merge_blueprint_funcs(self, app: app, name: str) -> none:
def extend(
bp_dict: dict[ft.apporblueprintkey, list[t.any]],
parent_dict: dict[ft.apporblueprintkey, list[t.any]],
) -> none:
for key, values in bp_dict.items():
key = name if key is none else f"{name}.{key}"
parent_dict[key].extend(values)
for key, value in self.error_handler_spec.items():
key = name if key is none else f"{name}.{key}"
value = defaultdict(
dict,
{
code: {exc_class: func for exc_class, func in code_values.items()}
for code, code_values in value.items()
},
)
app.error_handler_spec[key] = value
for endpoint, func in self.view_functions.items():
app.view_functions[endpoint] = func
extend(self.before_request_funcs, app.before_request_funcs)
extend(self.after_request_funcs, app.after_request_funcs)
extend(
self.teardown_request_funcs,
app.teardown_request_funcs,
)
extend(self.url_default_functions, app.url_default_functions)
extend(self.url_value_preprocessors, app.url_value_preprocessors)
extend(self.template_context_processors, app.template_context_processors)
@setupmethod
def add_url_rule(
self,
rule: str,
endpoint: str | none = none,
view_func: ft.routecallable | none = none,
provide_automatic_options: bool | none = none,
**options: t.any,
) -> none:
if endpoint and "." in endpoint:
raise valueerror("'endpoint' may not contain a dot '.' character.")
if view_func and hasattr(view_func, "__name__") and "." in view_func.__name__:
raise valueerror("'view_func' name may not contain a dot '.' character.")
self.record(
lambda s: s.add_url_rule(
rule,
endpoint,
view_func,
provide_automatic_options=provide_automatic_options,
**options,
)
)
@setupmethod
def app_template_filter(
self, name: str | none = none
) -> t.callable[[t_template_filter], t_template_filter]:
def decorator(f: t_template_filter) -> t_template_filter:
self.add_app_template_filter(f, name=name)
return f
return decorator
@setupmethod
def add_app_template_filter(
self, f: ft.templatefiltercallable, name: str | none = none
) -> none:
def register_template(state: blueprintsetupstate) -> none:
state.app.jinja_env.filters[name or f.__name__] = f
self.record_once(register_template)
@setupmethod
def app_template_test(
self, name: str | none = none
) -> t.callable[[t_template_test], t_template_test]:
def decorator(f: t_template_test) -> t_template_test:
self.add_app_template_test(f, name=name)
return f
return decorator
@setupmethod
def add_app_template_test(
self, f: ft.templatetestcallable, name: str | none = none
) -> none:
def register_template(state: blueprintsetupstate) -> none:
state.app.jinja_env.tests[name or f.__name__] = f
self.record_once(register_template)
@setupmethod
def app_template_global(
self, name: str | none = none
) -> t.callable[[t_template_global], t_template_global]:
def decorator(f: t_template_global) -> t_template_global:
self.add_app_template_global(f, name=name)
return f
return decorator
@setupmethod
def add_app_template_global(
self, f: ft.templateglobalcallable, name: str | none = none
) -> none:
def register_template(state: blueprintsetupstate) -> none:
state.app.jinja_env.globals[name or f.__name__] = f
self.record_once(register_template)
@setupmethod
def before_app_request(self, f: t_before_request) -> t_before_request:
self.record_once(
lambda s: s.app.before_request_funcs.setdefault(none, []).append(f)
)
return f
@setupmethod
def after_app_request(self, f: t_after_request) -> t_after_request:
self.record_once(
lambda s: s.app.after_request_funcs.setdefault(none, []).append(f)
)
return f
@setupmethod
def teardown_app_request(self, f: t_teardown) -> t_teardown:
self.record_once(
lambda s: s.app.teardown_request_funcs.setdefault(none, []).append(f)
)
return f
@setupmethod
def app_context_processor(
self, f: t_template_context_processor
) -> t_template_context_processor:
self.record_once(
lambda s: s.app.template_context_processors.setdefault(none, []).append(f)
)
return f
@setupmethod
def app_errorhandler(
self, code: type[exception] | int
) -> t.callable[[t_error_handler], t_error_handler]:
def decorator(f: t_error_handler) -> t_error_handler:
def from_blueprint(state: blueprintsetupstate) -> none:
state.app.errorhandler(code)(f)
self.record_once(from_blueprint)
return f
return decorator
@setupmethod
def app_url_value_preprocessor(
self, f: t_url_value_preprocessor
) -> t_url_value_preprocessor:
self.record_once(
lambda s: s.app.url_value_preprocessors.setdefault(none, []).append(f)
)
return f
@setupmethod
def app_url_defaults(self, f: t_url_defaults) -> t_url_defaults:
self.record_once(
lambda s: s.app.url_default_functions.setdefault(none, []).append(f)
)
return f