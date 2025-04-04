from __future__ import annotations
import ast
import collections.abc as cabc
import importlib.metadata
import inspect
import os
import platform
import re
import sys
import traceback
import typing as t
from functools import update_wrapper
from operator import itemgetter
from types import moduletype
import click
from click.core import parametersource
from werkzeug import run_simple
from werkzeug.serving import is_running_from_reloader
from werkzeug.utils import import_string
from .globals import current_app
from .helpers import get_debug_flag
from .helpers import get_load_dotenv
if t.type_checking:
import ssl
from _typeshed.wsgi import startresponse
from _typeshed.wsgi import wsgiapplication
from _typeshed.wsgi import wsgienvironment
from .app import flask
class noappexception(click.usageerror):
def find_best_app(module: moduletype) -> flask:
from . import flask
for attr_name in ("app", "application"):
app = getattr(module, attr_name, none)
if isinstance(app, flask):
return app
matches = [v for v in module.__dict__.values() if isinstance(v, flask)]
if len(matches) == 1:
return matches[0]
elif len(matches) > 1:
raise noappexception(
"detected multiple flask applications in module"
f" '{module.__name__}'. use '{module.__name__}:name'"
" to specify the correct one."
)
for attr_name in ("create_app", "make_app"):
app_factory = getattr(module, attr_name, none)
if inspect.isfunction(app_factory):
try:
app = app_factory()
if isinstance(app, flask):
return app
except typeerror as e:
if not _called_with_wrong_args(app_factory):
raise
raise noappexception(
f"detected factory '{attr_name}' in module '{module.__name__}',"
" but could not call it without arguments. use"
f" '{module.__name__}:{attr_name}(args)'"
" to specify arguments."
) from e
raise noappexception(
"failed to find flask application or factory in module"
f" '{module.__name__}'. use '{module.__name__}:name'"
" to specify one."
)
def _called_with_wrong_args(f: t.callable[..., flask]) -> bool:
tb = sys.exc_info()[2]
try:
while tb is not none:
if tb.tb_frame.f_code is f.__code__:
return false
tb = tb.tb_next
return true
finally:
del tb
def find_app_by_string(module: moduletype, app_name: str) -> flask:
from . import flask
try:
expr = ast.parse(app_name.strip(), mode="eval").body
except syntaxerror:
raise noappexception(
f"failed to parse {app_name!r} as an attribute name or function call."
) from none
if isinstance(expr, ast.name):
name = expr.id
args = []
kwargs = {}
elif isinstance(expr, ast.call):
if not isinstance(expr.func, ast.name):
raise noappexception(
f"function reference must be a simple name: {app_name!r}."
)
name = expr.func.id
try:
args = [ast.literal_eval(arg) for arg in expr.args]
kwargs = {
kw.arg: ast.literal_eval(kw.value)
for kw in expr.keywords
if kw.arg is not none
}
except valueerror:
raise noappexception(
f"failed to parse arguments as literal values: {app_name!r}."
) from none
else:
raise noappexception(
f"failed to parse {app_name!r} as an attribute name or function call."
)
try:
attr = getattr(module, name)
except attributeerror as e:
raise noappexception(
f"failed to find attribute {name!r} in {module.__name__!r}."
) from e
if inspect.isfunction(attr):
try:
app = attr(*args, **kwargs)
except typeerror as e:
if not _called_with_wrong_args(attr):
raise
raise noappexception(
f"the factory {app_name!r} in module"
f" {module.__name__!r} could not be called with the"
" specified arguments."
) from e
else:
app = attr
if isinstance(app, flask):
return app
raise noappexception(
"a valid flask application was not obtained from"
f" '{module.__name__}:{app_name}'."
)
def prepare_import(path: str) -> str:
path = os.path.realpath(path)
fname, ext = os.path.splitext(path)
if ext == ".py":
path = fname
if os.path.basename(path) == "__init__":
path = os.path.dirname(path)
module_name = []
while true:
path, name = os.path.split(path)
module_name.append(name)
if not os.path.exists(os.path.join(path, "__init__.py")):
break
if sys.path[0] != path:
sys.path.insert(0, path)
return ".".join(module_name[::-1])
@t.overload
def locate_app(
module_name: str, app_name: str | none, raise_if_not_found: t.literal[true] = true
) -> flask: ...
@t.overload
def locate_app(
module_name: str, app_name: str | none, raise_if_not_found: t.literal[false] = ...
) -> flask | none: ...
def locate_app(
module_name: str, app_name: str | none, raise_if_not_found: bool = true
) -> flask | none:
try:
__import__(module_name)
except importerror:
if sys.exc_info()[2].tb_next:
raise noappexception(
f"while importing {module_name!r}, an importerror was"
f" raised:\n\n{traceback.format_exc()}"
) from none
elif raise_if_not_found:
raise noappexception(f"could not import {module_name!r}.") from none
else:
return none
module = sys.modules[module_name]
if app_name is none:
return find_best_app(module)
else:
return find_app_by_string(module, app_name)
def get_version(ctx: click.context, param: click.parameter, value: t.any) -> none:
if not value or ctx.resilient_parsing:
return
flask_version = importlib.metadata.version("flask")
werkzeug_version = importlib.metadata.version("werkzeug")
click.echo(
f"python {platform.python_version()}\n"
f"flask {flask_version}\n"
f"werkzeug {werkzeug_version}",
color=ctx.color,
)
ctx.exit()
version_option = click.option(
["--version"],
help="show the flask version.",
expose_value=false,
callback=get_version,
is_flag=true,
is_eager=true,
)
class scriptinfo:
def __init__(
self,
app_import_path: str | none = none,
create_app: t.callable[..., flask] | none = none,
set_debug_flag: bool = true,
load_dotenv_defaults: bool = true,
) -> none:
self.app_import_path = app_import_path
self.create_app = create_app
self.data: dict[t.any, t.any] = {}
self.set_debug_flag = set_debug_flag
self.load_dotenv_defaults = get_load_dotenv(load_dotenv_defaults)
self._loaded_app: flask | none = none
def load_app(self) -> flask:
if self._loaded_app is not none:
return self._loaded_app
app: flask | none = none
if self.create_app is not none:
app = self.create_app()
else:
if self.app_import_path:
path, name = (
re.split(r":(?![\\/])", self.app_import_path, maxsplit=1) + [none]
)[:2]
import_name = prepare_import(path)
app = locate_app(import_name, name)
else:
for path in ("wsgi.py", "app.py"):
import_name = prepare_import(path)
app = locate_app(import_name, none, raise_if_not_found=false)
if app is not none:
break
if app is none:
raise noappexception(
"could not locate a flask application. use the"
" 'flask --app' option, 'flask_app' environment"
" variable, or a 'wsgi.py' or 'app.py' file in the"
" current directory."
)
if self.set_debug_flag:
app.debug = get_debug_flag()
self._loaded_app = app
return app
pass_script_info = click.make_pass_decorator(scriptinfo, ensure=true)
f = t.typevar("f", bound=t.callable[..., t.any])
def with_appcontext(f: f) -> f:
@click.pass_context
def decorator(ctx: click.context, /, *args: t.any, **kwargs: t.any) -> t.any:
if not current_app:
app = ctx.ensure_object(scriptinfo).load_app()
ctx.with_resource(app.app_context())
return ctx.invoke(f, *args, **kwargs)
return update_wrapper(decorator, f)
class appgroup(click.group):
def command(
self, *args: t.any, **kwargs: t.any
) -> t.callable[[t.callable[..., t.any]], click.command]:
wrap_for_ctx = kwargs.pop("with_appcontext", true)
def decorator(f: t.callable[..., t.any]) -> click.command:
if wrap_for_ctx:
f = with_appcontext(f)
return super(appgroup, self).command(*args, **kwargs)(f)
return decorator
def group(
self, *args: t.any, **kwargs: t.any
) -> t.callable[[t.callable[..., t.any]], click.group]:
kwargs.setdefault("cls", appgroup)
return super().group(*args, **kwargs)
def _set_app(ctx: click.context, param: click.option, value: str | none) -> str | none:
if value is none:
return none
info = ctx.ensure_object(scriptinfo)
info.app_import_path = value
return value
_app_option = click.option(
["-a", "--app"],
metavar="import",
help=(
"the flask application or factory function to load, in the form 'module:name'."
" module can be a dotted import or file path. name is not required if it is"
" 'app', 'application', 'create_app', or 'make_app', and can be 'name(args)' to"
" pass arguments."
),
is_eager=true,
expose_value=false,
callback=_set_app,
)
def _set_debug(ctx: click.context, param: click.option, value: bool) -> bool | none:
source = ctx.get_parameter_source(param.name)
if source is not none and source in (
parametersource.default,
parametersource.default_map,
):
return none
os.environ["flask_debug"] = "1" if value else "0"
return value
_debug_option = click.option(
["--debug/--no-debug"],
help="set debug mode.",
expose_value=false,
callback=_set_debug,
)
def _env_file_callback(
ctx: click.context, param: click.option, value: str | none
) -> str | none:
try:
import dotenv
except importerror:
if value is not none:
raise click.badparameter(
"python-dotenv must be installed to load an env file.",
ctx=ctx,
param=param,
) from none
if value is not none or ctx.obj.load_dotenv_defaults:
load_dotenv(value, load_defaults=ctx.obj.load_dotenv_defaults)
return value
_env_file_option = click.option(
["-e", "--env-file"],
type=click.path(exists=true, dir_okay=false),
help=(
"load environment variables from this file, taking precedence over"
" those set by '.env' and '.flaskenv'. variables set directly in the"
" environment take highest precedence. python-dotenv must be installed."
),
is_eager=true,
expose_value=false,
callback=_env_file_callback,
)
class flaskgroup(appgroup):
def __init__(
self,
add_default_commands: bool = true,
create_app: t.callable[..., flask] | none = none,
add_version_option: bool = true,
load_dotenv: bool = true,
set_debug_flag: bool = true,
**extra: t.any,
) -> none:
params: list[click.parameter] = list(extra.pop("params", none) or ())
params.extend((_env_file_option, _app_option, _debug_option))
if add_version_option:
params.append(version_option)
if "context_settings" not in extra:
extra["context_settings"] = {}
extra["context_settings"].setdefault("auto_envvar_prefix", "flask")
super().__init__(params=params, **extra)
self.create_app = create_app
self.load_dotenv = load_dotenv
self.set_debug_flag = set_debug_flag
if add_default_commands:
self.add_command(run_command)
self.add_command(shell_command)
self.add_command(routes_command)
self._loaded_plugin_commands = false
def _load_plugin_commands(self) -> none:
if self._loaded_plugin_commands:
return
if sys.version_info >= (3, 10):
from importlib import metadata
else:
import importlib_metadata as metadata
for ep in metadata.entry_points(group="flask.commands"):
self.add_command(ep.load(), ep.name)
self._loaded_plugin_commands = true
def get_command(self, ctx: click.context, name: str) -> click.command | none:
self._load_plugin_commands()
rv = super().get_command(ctx, name)
if rv is not none:
return rv
info = ctx.ensure_object(scriptinfo)
try:
app = info.load_app()
except noappexception as e:
click.secho(f"error: {e.format_message()}\n", err=true, fg="red")
return none
if not current_app or current_app._get_current_object() is not app:
ctx.with_resource(app.app_context())
return app.cli.get_command(ctx, name)
def list_commands(self, ctx: click.context) -> list[str]:
self._load_plugin_commands()
rv = set(super().list_commands(ctx))
info = ctx.ensure_object(scriptinfo)
try:
rv.update(info.load_app().cli.list_commands(ctx))
except noappexception as e:
click.secho(f"error: {e.format_message()}\n", err=true, fg="red")
except exception:
click.secho(f"{traceback.format_exc()}\n", err=true, fg="red")
return sorted(rv)
def make_context(
self,
info_name: str | none,
args: list[str],
parent: click.context | none = none,
**extra: t.any,
) -> click.context:
os.environ["flask_run_from_cli"] = "true"
if "obj" not in extra and "obj" not in self.context_settings:
extra["obj"] = scriptinfo(
create_app=self.create_app,
set_debug_flag=self.set_debug_flag,
load_dotenv_defaults=self.load_dotenv,
)
return super().make_context(info_name, args, parent=parent, **extra)
def parse_args(self, ctx: click.context, args: list[str]) -> list[str]:
if (not args and self.no_args_is_help) or (
len(args) == 1 and args[0] in self.get_help_option_names(ctx)
):
_env_file_option.handle_parse_result(ctx, {}, [])
_app_option.handle_parse_result(ctx, {}, [])
return super().parse_args(ctx, args)
def _path_is_ancestor(path: str, other: str) -> bool:
return os.path.join(path, other[len(path) :].lstrip(os.sep)) == other
def load_dotenv(
path: str | os.pathlike[str] | none = none, load_defaults: bool = true
) -> bool:
try:
import dotenv
except importerror:
if path or os.path.isfile(".env") or os.path.isfile(".flaskenv"):
click.secho(
" * tip: there are .env files present. install python-dotenv"
" to use them.",
fg="yellow",
err=true,
)
return false
data: dict[str, str | none] = {}
if load_defaults:
for default_name in (".flaskenv", ".env"):
if not (default_path := dotenv.find_dotenv(default_name, usecwd=true)):
continue
data |= dotenv.dotenv_values(default_path, encoding="utf-8")
if path is not none and os.path.isfile(path):
data |= dotenv.dotenv_values(path, encoding="utf-8")
for key, value in data.items():
if key in os.environ or value is none:
continue
os.environ[key] = value
return bool(data)
def show_server_banner(debug: bool, app_import_path: str | none) -> none:
if is_running_from_reloader():
return
if app_import_path is not none:
click.echo(f" * serving flask app '{app_import_path}'")
if debug is not none:
click.echo(f" * debug mode: {'on' if debug else 'off'}")
class certparamtype(click.paramtype):
name = "path"
def __init__(self) -> none:
self.path_type = click.path(exists=true, dir_okay=false, resolve_path=true)
def convert(
self, value: t.any, param: click.parameter | none, ctx: click.context | none
) -> t.any:
try:
import ssl
except importerror:
raise click.badparameter(
'using "--cert" requires python to be compiled with ssl support.',
ctx,
param,
) from none
try:
return self.path_type(value, param, ctx)
except click.badparameter:
value = click.string(value, param, ctx).lower()
if value == "adhoc":
try:
import cryptography
except importerror:
raise click.badparameter(
"using ad-hoc certificates requires the cryptography library.",
ctx,
param,
) from none
return value
obj = import_string(value, silent=true)
if isinstance(obj, ssl.sslcontext):
return obj
raise
def _validate_key(ctx: click.context, param: click.parameter, value: t.any) -> t.any:
cert = ctx.params.get("cert")
is_adhoc = cert == "adhoc"
try:
import ssl
except importerror:
is_context = false
else:
is_context = isinstance(cert, ssl.sslcontext)
if value is not none:
if is_adhoc:
raise click.badparameter(
'when "--cert" is "adhoc", "--key" is not used.', ctx, param
)
if is_context:
raise click.badparameter(
'when "--cert" is an sslcontext object, "--key" is not used.',
ctx,
param,
)
if not cert:
raise click.badparameter('"--cert" must also be specified.', ctx, param)
ctx.params["cert"] = cert, value
else:
if cert and not (is_adhoc or is_context):
raise click.badparameter('required when using "--cert".', ctx, param)
return value
class separatedpathtype(click.path):
def convert(
self, value: t.any, param: click.parameter | none, ctx: click.context | none
) -> t.any:
items = self.split_envvar_value(value)
super_convert = super().convert
return [super_convert(item, param, ctx) for item in items]
@click.command("run", short_help="run a development server.")
@click.option("--host", "-h", default="127.0.0.1", help="the interface to bind to.")
@click.option("--port", "-p", default=5000, help="the port to bind to.")
@click.option(
"--cert",
type=certparamtype(),
help="specify a certificate file to use https.",
is_eager=true,
)
@click.option(
"--key",
type=click.path(exists=true, dir_okay=false, resolve_path=true),
callback=_validate_key,
expose_value=false,
help="the key file to use when specifying a certificate.",
)
@click.option(
"--reload/--no-reload",
default=none,
help="enable or disable the reloader. by default the reloader "
"is active if debug is enabled.",
)
@click.option(
"--debugger/--no-debugger",
default=none,
help="enable or disable the debugger. by default the debugger "
"is active if debug is enabled.",
)
@click.option(
"--with-threads/--without-threads",
default=true,
help="enable or disable multithreading.",
)
@click.option(
"--extra-files",
default=none,
type=separatedpathtype(),
help=(
"extra files that trigger a reload on change. multiple paths"
f" are separated by {os.path.pathsep!r}."
),
)
@click.option(
"--exclude-patterns",
default=none,
type=separatedpathtype(),
help=(
"files matching these fnmatch patterns will not trigger a reload"
" on change. multiple patterns are separated by"
f" {os.path.pathsep!r}."
),
)
@pass_script_info
def run_command(
info: scriptinfo,
host: str,
port: int,
reload: bool,
debugger: bool,
with_threads: bool,
cert: ssl.sslcontext | tuple[str, str | none] | t.literal["adhoc"] | none,
extra_files: list[str] | none,
exclude_patterns: list[str] | none,
) -> none:
try:
app: wsgiapplication = info.load_app()
except exception as e:
if is_running_from_reloader():
traceback.print_exc()
err = e
def app(
environ: wsgienvironment, start_response: startresponse
) -> cabc.iterable[bytes]:
raise err from none
else:
raise e from none
debug = get_debug_flag()
if reload is none:
reload = debug
if debugger is none:
debugger = debug
show_server_banner(debug, info.app_import_path)
run_simple(
host,
port,
app,
use_reloader=reload,
use_debugger=debugger,
threaded=with_threads,
ssl_context=cert,
extra_files=extra_files,
exclude_patterns=exclude_patterns,
)
run_command.params.insert(0, _debug_option)
@click.command("shell", short_help="run a shell in the app context.")
@with_appcontext
def shell_command() -> none:
import code
banner = (
f"python {sys.version} on {sys.platform}\n"
f"app: {current_app.import_name}\n"
f"instance: {current_app.instance_path}"
)
ctx: dict[str, t.any] = {}
startup = os.environ.get("pythonstartup")
if startup and os.path.isfile(startup):
with open(startup) as f:
eval(compile(f.read(), startup, "exec"), ctx)
ctx.update(current_app.make_shell_context())
interactive_hook = getattr(sys, "__interactivehook__", none)
if interactive_hook is not none:
try:
import readline
from rlcompleter import completer
except importerror:
pass
else:
readline.set_completer(completer(ctx).complete)
interactive_hook()
code.interact(banner=banner, local=ctx)
@click.command("routes", short_help="show the routes for the app.")
@click.option(
"--sort",
"-s",
type=click.choice(("endpoint", "methods", "domain", "rule", "match")),
default="endpoint",
help=(
"method to sort routes by. 'match' is the order that flask will match routes"
" when dispatching a request."
),
)
@click.option("--all-methods", is_flag=true, help="show head and options methods.")
@with_appcontext
def routes_command(sort: str, all_methods: bool) -> none:
rules = list(current_app.url_map.iter_rules())
if not rules:
click.echo("no routes were registered.")
return
ignored_methods = set() if all_methods else {"head", "options"}
host_matching = current_app.url_map.host_matching
has_domain = any(rule.host if host_matching else rule.subdomain for rule in rules)
rows = []
for rule in rules:
row = [
rule.endpoint,
", ".join(sorted((rule.methods or set()) - ignored_methods)),
]
if has_domain:
row.append((rule.host if host_matching else rule.subdomain) or "")
row.append(rule.rule)
rows.append(row)
headers = ["endpoint", "methods"]
sorts = ["endpoint", "methods"]
if has_domain:
headers.append("host" if host_matching else "subdomain")
sorts.append("domain")
headers.append("rule")
sorts.append("rule")
try:
rows.sort(key=itemgetter(sorts.index(sort)))
except valueerror:
pass
rows.insert(0, headers)
widths = [max(len(row[i]) for row in rows) for i in range(len(headers))]
rows.insert(1, ["-" * w for w in widths])
template = "  ".join(f"{{{i}:<{w}}}" for i, w in enumerate(widths))
for row in rows:
click.echo(template.format(*row))
cli = flaskgroup(
name="flask",
help=,
)
def main() -> none:
cli.main()
if __name__ == "__main__":
main()