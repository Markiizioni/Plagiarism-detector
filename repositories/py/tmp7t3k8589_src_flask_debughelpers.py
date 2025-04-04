from __future__ import annotations
import typing as t
from jinja2.loaders import baseloader
from werkzeug.routing import requestredirect
from .blueprints import blueprint
from .globals import request_ctx
from .sansio.app import app
if t.type_checking:
from .sansio.scaffold import scaffold
from .wrappers import request
class unexpectedunicodeerror(assertionerror, unicodeerror):
class debugfileskeyerror(keyerror, assertionerror):
def __init__(self, request: request, key: str) -> none:
form_matches = request.form.getlist(key)
buf = [
f"you tried to access the file {key!r} in the request.files"
" dictionary but it does not exist. the mimetype for the"
f" request is {request.mimetype!r} instead of"
" 'multipart/form-data' which means that no file contents"
" were transmitted. to fix this error you should provide"
' enctype="multipart/form-data" in your form.'
]
if form_matches:
names = ", ".join(repr(x) for x in form_matches)
buf.append(
"\n\nthe browser instead transmitted some file names. "
f"this was submitted: {names}"
)
self.msg = "".join(buf)
def __str__(self) -> str:
return self.msg
class formdataroutingredirect(assertionerror):
def __init__(self, request: request) -> none:
exc = request.routing_exception
assert isinstance(exc, requestredirect)
buf = [
f"a request was sent to '{request.url}', but routing issued"
f" a redirect to the canonical url '{exc.new_url}'."
]
if f"{request.base_url}/" == exc.new_url.partition("?")[0]:
buf.append(
" the url was defined with a trailing slash. flask"
" will redirect to the url with a trailing slash if it"
" was accessed without one."
)
buf.append(
" send requests to the canonical url, or use 307 or 308 for"
" routing redirects. otherwise, browsers will drop form"
" data.\n\n"
"this exception is only raised in debug mode."
)
super().__init__("".join(buf))
def attach_enctype_error_multidict(request: request) -> none:
oldcls = request.files.__class__
class newcls(oldcls):
def __getitem__(self, key: str) -> t.any:
try:
return super().__getitem__(key)
except keyerror as e:
if key not in request.form:
raise
raise debugfileskeyerror(request, key).with_traceback(
e.__traceback__
) from none
newcls.__name__ = oldcls.__name__
newcls.__module__ = oldcls.__module__
request.files.__class__ = newcls
def _dump_loader_info(loader: baseloader) -> t.iterator[str]:
yield f"class: {type(loader).__module__}.{type(loader).__name__}"
for key, value in sorted(loader.__dict__.items()):
if key.startswith("_"):
continue
if isinstance(value, (tuple, list)):
if not all(isinstance(x, str) for x in value):
continue
yield f"{key}:"
for item in value:
yield f"  - {item}"
continue
elif not isinstance(value, (str, int, float, bool)):
continue
yield f"{key}: {value!r}"
def explain_template_loading_attempts(
app: app,
template: str,
attempts: list[
tuple[
baseloader,
scaffold,
tuple[str, str | none, t.callable[[], bool] | none] | none,
]
],
) -> none:
info = [f"locating template {template!r}:"]
total_found = 0
blueprint = none
if request_ctx and request_ctx.request.blueprint is not none:
blueprint = request_ctx.request.blueprint
for idx, (loader, srcobj, triple) in enumerate(attempts):
if isinstance(srcobj, app):
src_info = f"application {srcobj.import_name!r}"
elif isinstance(srcobj, blueprint):
src_info = f"blueprint {srcobj.name!r} ({srcobj.import_name})"
else:
src_info = repr(srcobj)
info.append(f"{idx + 1:5}: trying loader of {src_info}")
for line in _dump_loader_info(loader):
info.append(f"       {line}")
if triple is none:
detail = "no match"
else:
detail = f"found ({triple[1] or '<string>'!r})"
total_found += 1
info.append(f"       -> {detail}")
seems_fishy = false
if total_found == 0:
info.append("error: the template could not be found.")
seems_fishy = true
elif total_found > 1:
info.append("warning: multiple loaders returned a match for the template.")
seems_fishy = true
if blueprint is not none and seems_fishy:
info.append(
"  the template was looked up from an endpoint that belongs"
f" to the blueprint {blueprint!r}."
)
info.append("  maybe you did not place a template in the right folder?")
info.append("  see https:
app.logger.info("\n".join(info))