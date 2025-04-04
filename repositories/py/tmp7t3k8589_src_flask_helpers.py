from __future__ import annotations
import importlib.util
import os
import sys
import typing as t
from datetime import datetime
from functools import cache
from functools import update_wrapper
import werkzeug.utils
from werkzeug.exceptions import abort as _wz_abort
from werkzeug.utils import redirect as _wz_redirect
from werkzeug.wrappers import response as baseresponse
from .globals import _cv_request
from .globals import current_app
from .globals import request
from .globals import request_ctx
from .globals import session
from .signals import message_flashed
if t.type_checking:
from .wrappers import response
def get_debug_flag() -> bool:
val = os.environ.get("flask_debug")
return bool(val and val.lower() not in {"0", "false", "no"})
def get_load_dotenv(default: bool = true) -> bool:
val = os.environ.get("flask_skip_dotenv")
if not val:
return default
return val.lower() in ("0", "false", "no")
@t.overload
def stream_with_context(
generator_or_function: t.iterator[t.anystr],
) -> t.iterator[t.anystr]: ...
@t.overload
def stream_with_context(
generator_or_function: t.callable[..., t.iterator[t.anystr]],
) -> t.callable[[t.iterator[t.anystr]], t.iterator[t.anystr]]: ...
def stream_with_context(
generator_or_function: t.iterator[t.anystr] | t.callable[..., t.iterator[t.anystr]],
) -> t.iterator[t.anystr] | t.callable[[t.iterator[t.anystr]], t.iterator[t.anystr]]:
try:
gen = iter(generator_or_function)
except typeerror:
def decorator(*args: t.any, **kwargs: t.any) -> t.any:
gen = generator_or_function(*args, **kwargs)
return stream_with_context(gen)
return update_wrapper(decorator, generator_or_function)
def generator() -> t.iterator[t.anystr | none]:
ctx = _cv_request.get(none)
if ctx is none:
raise runtimeerror(
"'stream_with_context' can only be used when a request"
" context is active, such as in a view function."
)
with ctx:
yield none
try:
yield from gen
finally:
if hasattr(gen, "close"):
gen.close()
wrapped_g = generator()
next(wrapped_g)
return wrapped_g
def make_response(*args: t.any) -> response:
if not args:
return current_app.response_class()
if len(args) == 1:
args = args[0]
return current_app.make_response(args)
def url_for(
endpoint: str,
*,
_anchor: str | none = none,
_method: str | none = none,
_scheme: str | none = none,
_external: bool | none = none,
**values: t.any,
) -> str:
return current_app.url_for(
endpoint,
_anchor=_anchor,
_method=_method,
_scheme=_scheme,
_external=_external,
**values,
)
def redirect(
location: str, code: int = 302, response: type[baseresponse] | none = none
) -> baseresponse:
if current_app:
return current_app.redirect(location, code=code)
return _wz_redirect(location, code=code, response=response)
def abort(code: int | baseresponse, *args: t.any, **kwargs: t.any) -> t.noreturn:
if current_app:
current_app.aborter(code, *args, **kwargs)
_wz_abort(code, *args, **kwargs)
def get_template_attribute(template_name: str, attribute: str) -> t.any:
return getattr(current_app.jinja_env.get_template(template_name).module, attribute)
def flash(message: str, category: str = "message") -> none:
flashes = session.get("_flashes", [])
flashes.append((category, message))
session["_flashes"] = flashes
app = current_app._get_current_object()
message_flashed.send(
app,
_async_wrapper=app.ensure_sync,
message=message,
category=category,
)
def get_flashed_messages(
with_categories: bool = false, category_filter: t.iterable[str] = ()
) -> list[str] | list[tuple[str, str]]:
flashes = request_ctx.flashes
if flashes is none:
flashes = session.pop("_flashes") if "_flashes" in session else []
request_ctx.flashes = flashes
if category_filter:
flashes = list(filter(lambda f: f[0] in category_filter, flashes))
if not with_categories:
return [x[1] for x in flashes]
return flashes
def _prepare_send_file_kwargs(**kwargs: t.any) -> dict[str, t.any]:
if kwargs.get("max_age") is none:
kwargs["max_age"] = current_app.get_send_file_max_age
kwargs.update(
environ=request.environ,
use_x_sendfile=current_app.config["use_x_sendfile"],
response_class=current_app.response_class,
_root_path=current_app.root_path,
)
return kwargs
def send_file(
path_or_file: os.pathlike[t.anystr] | str | t.binaryio,
mimetype: str | none = none,
as_attachment: bool = false,
download_name: str | none = none,
conditional: bool = true,
etag: bool | str = true,
last_modified: datetime | int | float | none = none,
max_age: none | (int | t.callable[[str | none], int | none]) = none,
) -> response:
return werkzeug.utils.send_file(
**_prepare_send_file_kwargs(
path_or_file=path_or_file,
environ=request.environ,
mimetype=mimetype,
as_attachment=as_attachment,
download_name=download_name,
conditional=conditional,
etag=etag,
last_modified=last_modified,
max_age=max_age,
)
)
def send_from_directory(
directory: os.pathlike[str] | str,
path: os.pathlike[str] | str,
**kwargs: t.any,
) -> response:
return werkzeug.utils.send_from_directory(
directory, path, **_prepare_send_file_kwargs(**kwargs)
)
def get_root_path(import_name: str) -> str:
mod = sys.modules.get(import_name)
if mod is not none and hasattr(mod, "__file__") and mod.__file__ is not none:
return os.path.dirname(os.path.abspath(mod.__file__))
try:
spec = importlib.util.find_spec(import_name)
if spec is none:
raise valueerror
except (importerror, valueerror):
loader = none
else:
loader = spec.loader
if loader is none:
return os.getcwd()
if hasattr(loader, "get_filename"):
filepath = loader.get_filename(import_name)
else:
__import__(import_name)
mod = sys.modules[import_name]
filepath = getattr(mod, "__file__", none)
if filepath is none:
raise runtimeerror(
"no root path can be found for the provided module"
f" {import_name!r}. this can happen because the module"
" came from an import hook that does not provide file"
" name information or because it's a namespace package."
" in this case the root path needs to be explicitly"
" provided."
)
return os.path.dirname(os.path.abspath(filepath))
@cache
def _split_blueprint_path(name: str) -> list[str]:
out: list[str] = [name]
if "." in name:
out.extend(_split_blueprint_path(name.rpartition(".")[0]))
return out