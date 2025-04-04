import datetime
import decimal
import io
import uuid
import pytest
from werkzeug.http import http_date
import flask
from flask import json
from flask.json.provider import defaultjsonprovider
@pytest.mark.parametrize("debug", (true, false))
def test_bad_request_debug_message(app, client, debug):
app.config["debug"] = debug
app.config["trap_bad_request_errors"] = false
@app.route("/json", methods=["post"])
def post_json():
flask.request.get_json()
return none
rv = client.post("/json", data=none, content_type="application/json")
assert rv.status_code == 400
contains = b"failed to decode json object" in rv.data
assert contains == debug
def test_json_bad_requests(app, client):
@app.route("/json", methods=["post"])
def return_json():
return flask.jsonify(foo=str(flask.request.get_json()))
rv = client.post("/json", data="malformed", content_type="application/json")
assert rv.status_code == 400
def test_json_custom_mimetypes(app, client):
@app.route("/json", methods=["post"])
def return_json():
return flask.request.get_json()
rv = client.post("/json", data='"foo"', content_type="application/x+json")
assert rv.data == b"foo"
@pytest.mark.parametrize(
"test_value,expected", [(true, '"\\u2603"'), (false, '"\u2603"')]
)
def test_json_as_unicode(test_value, expected, app, app_ctx):
app.json.ensure_ascii = test_value
rv = app.json.dumps("\n{snowman}")
assert rv == expected
def test_json_dump_to_file(app, app_ctx):
test_data = {"name": "flask"}
out = io.stringio()
flask.json.dump(test_data, out)
out.seek(0)
rv = flask.json.load(out)
assert rv == test_data
@pytest.mark.parametrize(
"test_value", [0, -1, 1, 23, 3.14, "s", "longer string", true, false, none]
)
def test_jsonify_basic_types(test_value, app, client):
url = "/jsonify_basic_types"
app.add_url_rule(url, url, lambda x=test_value: flask.jsonify(x))
rv = client.get(url)
assert rv.mimetype == "application/json"
assert flask.json.loads(rv.data) == test_value
def test_jsonify_dicts(app, client):
d = {
"a": 0,
"b": 23,
"c": 3.14,
"d": "t",
"e": "hi",
"f": true,
"g": false,
"h": ["test list", 10, false],
"i": {"test": "dict"},
}
@app.route("/kw")
def return_kwargs():
return flask.jsonify(**d)
@app.route("/dict")
def return_dict():
return flask.jsonify(d)
for url in "/kw", "/dict":
rv = client.get(url)
assert rv.mimetype == "application/json"
assert flask.json.loads(rv.data) == d
def test_jsonify_arrays(app, client):
a_list = [
0,
42,
3.14,
"t",
"hello",
true,
false,
["test list", 2, false],
{"test": "dict"},
]
@app.route("/args_unpack")
def return_args_unpack():
return flask.jsonify(*a_list)
@app.route("/array")
def return_array():
return flask.jsonify(a_list)
for url in "/args_unpack", "/array":
rv = client.get(url)
assert rv.mimetype == "application/json"
assert flask.json.loads(rv.data) == a_list
@pytest.mark.parametrize(
"value", [datetime.datetime(1973, 3, 11, 6, 30, 45), datetime.date(1975, 1, 5)]
)
def test_jsonify_datetime(app, client, value):
@app.route("/")
def index():
return flask.jsonify(value=value)
r = client.get()
assert r.json["value"] == http_date(value)
class fixedoffset(datetime.tzinfo):
def __init__(self, hours, name):
self.__offset = datetime.timedelta(hours=hours)
self.__name = name
def utcoffset(self, dt):
return self.__offset
def tzname(self, dt):
return self.__name
def dst(self, dt):
return datetime.timedelta()
@pytest.mark.parametrize("tz", (("utc", 0), ("pst", -8), ("kst", 9)))
def test_jsonify_aware_datetimes(tz):
tzinfo = fixedoffset(hours=tz[1], name=tz[0])
dt = datetime.datetime(2017, 1, 1, 12, 34, 56, tzinfo=tzinfo)
gmt = fixedoffset(hours=0, name="gmt")
expected = dt.astimezone(gmt).strftime('"%a, %d %b %y %h:%m:%s %z"')
assert flask.json.dumps(dt) == expected
def test_jsonify_uuid_types(app, client):
test_uuid = uuid.uuid(bytes=b"\xde\xad\xbe\xef" * 4)
url = "/uuid_test"
app.add_url_rule(url, url, lambda: flask.jsonify(x=test_uuid))
rv = client.get(url)
rv_x = flask.json.loads(rv.data)["x"]
assert rv_x == str(test_uuid)
rv_uuid = uuid.uuid(rv_x)
assert rv_uuid == test_uuid
def test_json_decimal():
rv = flask.json.dumps(decimal.decimal("0.003"))
assert rv == '"0.003"'
def test_json_attr(app, client):
@app.route("/add", methods=["post"])
def add():
json = flask.request.get_json()
return str(json["a"] + json["b"])
rv = client.post(
"/add",
data=flask.json.dumps({"a": 1, "b": 2}),
content_type="application/json",
)
assert rv.data == b"3"
def test_tojson_filter(app, req_ctx):
rv = flask.render_template_string(
"const data = {{ data|tojson }};",
data={"name": "</script>", "time": datetime.datetime(2021, 2, 1, 7, 15)},
)
assert rv == (
'const data = {"name": "\\u003c/script\\u003e",'
' "time": "mon, 01 feb 2021 07:15:00 gmt"};'
)
def test_json_customization(app, client):
class x:
def __init__(self, val):
self.val = val
def default(o):
if isinstance(o, x):
return f"<{o.val}>"
return defaultjsonprovider.default(o)
class customprovider(defaultjsonprovider):
def object_hook(self, obj):
if len(obj) == 1 and "_foo" in obj:
return x(obj["_foo"])
return obj
def loads(self, s, **kwargs):
kwargs.setdefault("object_hook", self.object_hook)
return super().loads(s, **kwargs)
app.json = customprovider(app)
app.json.default = default
@app.route("/", methods=["post"])
def index():
return flask.json.dumps(flask.request.get_json()["x"])
rv = client.post(
"/",
data=flask.json.dumps({"x": {"_foo": 42}}),
content_type="application/json",
)
assert rv.data == b'"<42>"'
def _has_encoding(name):
try:
import codecs
codecs.lookup(name)
return true
except lookuperror:
return false
def test_json_key_sorting(app, client):
app.debug = true
assert app.json.sort_keys
d = dict.fromkeys(range(20), "foo")
@app.route("/")
def index():
return flask.jsonify(values=d)
rv = client.get("/")
lines = [x.strip() for x in rv.data.strip().decode("utf-8").splitlines()]
sorted_by_str = [
"{",
'"values": {',
'"0": "foo",',
'"1": "foo",',
'"10": "foo",',
'"11": "foo",',
'"12": "foo",',
'"13": "foo",',
'"14": "foo",',
'"15": "foo",',
'"16": "foo",',
'"17": "foo",',
'"18": "foo",',
'"19": "foo",',
'"2": "foo",',
'"3": "foo",',
'"4": "foo",',
'"5": "foo",',
'"6": "foo",',
'"7": "foo",',
'"8": "foo",',
'"9": "foo"',
"}",
"}",
]
sorted_by_int = [
"{",
'"values": {',
'"0": "foo",',
'"1": "foo",',
'"2": "foo",',
'"3": "foo",',
'"4": "foo",',
'"5": "foo",',
'"6": "foo",',
'"7": "foo",',
'"8": "foo",',
'"9": "foo",',
'"10": "foo",',
'"11": "foo",',
'"12": "foo",',
'"13": "foo",',
'"14": "foo",',
'"15": "foo",',
'"16": "foo",',
'"17": "foo",',
'"18": "foo",',
'"19": "foo"',
"}",
"}",
]
try:
assert lines == sorted_by_int
except assertionerror:
assert lines == sorted_by_str
def test_html_method():
class objectwithhtml:
def __html__(self):
return "<p>test</p>"
result = json.dumps(objectwithhtml())
assert result == '"<p>test</p>"'