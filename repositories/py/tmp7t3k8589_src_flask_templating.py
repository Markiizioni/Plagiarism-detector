from __future__ import annotations
import typing as t
from jinja2 import baseloader
from jinja2 import environment as baseenvironment
from jinja2 import template
from jinja2 import templatenotfound
from .globals import _cv_app
from .globals import _cv_request
from .globals import current_app
from .globals import request
from .helpers import stream_with_context
from .signals import before_render_template
from .signals import template_rendered
if t.type_checking:
from .app import flask
from .sansio.app import app
from .sansio.scaffold import scaffold
def _default_template_ctx_processor() -> dict[str, t.any]:
appctx = _cv_app.get(none)
reqctx = _cv_request.get(none)
rv: dict[str, t.any] = {}
if appctx is not none:
rv["g"] = appctx.g
if reqctx is not none:
rv["request"] = reqctx.request
rv["session"] = reqctx.session
return rv
class environment(baseenvironment):
def __init__(self, app: app, **options: t.any) -> none:
if "loader" not in options:
options["loader"] = app.create_global_jinja_loader()
baseenvironment.__init__(self, **options)
self.app = app
class dispatchingjinjaloader(baseloader):
def __init__(self, app: app) -> none:
self.app = app
def get_source(
self, environment: baseenvironment, template: str
) -> tuple[str, str | none, t.callable[[], bool] | none]:
if self.app.config["explain_template_loading"]:
return self._get_source_explained(environment, template)
return self._get_source_fast(environment, template)
def _get_source_explained(
self, environment: baseenvironment, template: str
) -> tuple[str, str | none, t.callable[[], bool] | none]:
attempts = []
rv: tuple[str, str | none, t.callable[[], bool] | none] | none
trv: none | (tuple[str, str | none, t.callable[[], bool] | none]) = none
for srcobj, loader in self._iter_loaders(template):
try:
rv = loader.get_source(environment, template)
if trv is none:
trv = rv
except templatenotfound:
rv = none
attempts.append((loader, srcobj, rv))
from .debughelpers import explain_template_loading_attempts
explain_template_loading_attempts(self.app, template, attempts)
if trv is not none:
return trv
raise templatenotfound(template)
def _get_source_fast(
self, environment: baseenvironment, template: str
) -> tuple[str, str | none, t.callable[[], bool] | none]:
for _srcobj, loader in self._iter_loaders(template):
try:
return loader.get_source(environment, template)
except templatenotfound:
continue
raise templatenotfound(template)
def _iter_loaders(self, template: str) -> t.iterator[tuple[scaffold, baseloader]]:
loader = self.app.jinja_loader
if loader is not none:
yield self.app, loader
for blueprint in self.app.iter_blueprints():
loader = blueprint.jinja_loader
if loader is not none:
yield blueprint, loader
def list_templates(self) -> list[str]:
result = set()
loader = self.app.jinja_loader
if loader is not none:
result.update(loader.list_templates())
for blueprint in self.app.iter_blueprints():
loader = blueprint.jinja_loader
if loader is not none:
for template in loader.list_templates():
result.add(template)
return list(result)
def _render(app: flask, template: template, context: dict[str, t.any]) -> str:
app.update_template_context(context)
before_render_template.send(
app, _async_wrapper=app.ensure_sync, template=template, context=context
)
rv = template.render(context)
template_rendered.send(
app, _async_wrapper=app.ensure_sync, template=template, context=context
)
return rv
def render_template(
template_name_or_list: str | template | list[str | template],
**context: t.any,
) -> str:
app = current_app._get_current_object()
template = app.jinja_env.get_or_select_template(template_name_or_list)
return _render(app, template, context)
def render_template_string(source: str, **context: t.any) -> str:
app = current_app._get_current_object()
template = app.jinja_env.from_string(source)
return _render(app, template, context)
def _stream(
app: flask, template: template, context: dict[str, t.any]
) -> t.iterator[str]:
app.update_template_context(context)
before_render_template.send(
app, _async_wrapper=app.ensure_sync, template=template, context=context
)
def generate() -> t.iterator[str]:
yield from template.generate(context)
template_rendered.send(
app, _async_wrapper=app.ensure_sync, template=template, context=context
)
rv = generate()
if request:
rv = stream_with_context(rv)
return rv
def stream_template(
template_name_or_list: str | template | list[str | template],
**context: t.any,
) -> t.iterator[str]:
app = current_app._get_current_object()
template = app.jinja_env.get_or_select_template(template_name_or_list)
return _stream(app, template, context)
def stream_template_string(source: str, **context: t.any) -> t.iterator[str]:
app = current_app._get_current_object()
template = app.jinja_env.from_string(source)
return _stream(app, template, context)