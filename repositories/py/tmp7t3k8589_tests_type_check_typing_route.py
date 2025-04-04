from __future__ import annotations
import typing as t
from http import httpstatus
from flask import flask
from flask import jsonify
from flask import stream_template
from flask.templating import render_template
from flask.views import view
from flask.wrappers import response
app = flask(__name__)
@app.route("/str")
def hello_str() -> str:
return "<p>hello, world!</p>"
@app.route("/bytes")
def hello_bytes() -> bytes:
return b"<p>hello, world!</p>"
@app.route("/json")
def hello_json() -> response:
return jsonify("hello, world!")
@app.route("/json/dict")
def hello_json_dict() -> dict[str, t.any]:
return {"response": "hello, world!"}
@app.route("/json/dict")
def hello_json_list() -> list[t.any]:
return [{"message": "hello"}, {"message": "world"}]
class statusjson(t.typeddict):
status: str
@app.route("/typed-dict")
def typed_dict() -> statusjson:
return {"status": "ok"}
@app.route("/generator")
def hello_generator() -> t.generator[str, none, none]:
def show() -> t.generator[str, none, none]:
for x in range(100):
yield f"data:{x}\n\n"
return show()
@app.route("/generator-expression")
def hello_generator_expression() -> t.iterator[bytes]:
return (f"data:{x}\n\n".encode() for x in range(100))
@app.route("/iterator")
def hello_iterator() -> t.iterator[str]:
return iter([f"data:{x}\n\n" for x in range(100)])
@app.route("/status")
@app.route("/status/<int:code>")
def tuple_status(code: int = 200) -> tuple[str, int]:
return "hello", code
@app.route("/status-enum")
def tuple_status_enum() -> tuple[str, int]:
return "hello", httpstatus.ok
@app.route("/headers")
def tuple_headers() -> tuple[str, dict[str, str]]:
return "hello, world!", {"content-type": "text/plain"}
@app.route("/template")
@app.route("/template/<name>")
def return_template(name: str | none = none) -> str:
return render_template("index.html", name=name)
@app.route("/template")
def return_template_stream() -> t.iterator[str]:
return stream_template("index.html", name="hello")
@app.route("/async")
async def async_route() -> str:
return "hello"
class rendertemplateview(view):
def __init__(self: rendertemplateview, template_name: str) -> none:
self.template_name = template_name
def dispatch_request(self: rendertemplateview) -> str:
return render_template(self.template_name)
app.add_url_rule(
"/about",
view_func=rendertemplateview.as_view("about_page", template_name="about.html"),
)