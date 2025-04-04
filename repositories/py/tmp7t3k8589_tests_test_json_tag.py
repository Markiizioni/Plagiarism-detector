from datetime import datetime
from datetime import timezone
from uuid import uuid4
import pytest
from markupsafe import markup
from flask.json.tag import jsontag
from flask.json.tag import taggedjsonserializer
@pytest.mark.parametrize(
"data",
(
{" t": (1, 2, 3)},
{" t__": b"a"},
{" di": " di"},
{"x": (1, 2, 3), "y": 4},
(1, 2, 3),
[(1, 2, 3)],
b"\xff",
markup("<html>"),
uuid4(),
datetime.now(tz=timezone.utc).replace(microsecond=0),
),
)
def test_dump_load_unchanged(data):
s = taggedjsonserializer()
assert s.loads(s.dumps(data)) == data
def test_duplicate_tag():
class tagdict(jsontag):
key = " d"
s = taggedjsonserializer()
pytest.raises(keyerror, s.register, tagdict)
s.register(tagdict, force=true, index=0)
assert isinstance(s.tags[" d"], tagdict)
assert isinstance(s.order[0], tagdict)
def test_custom_tag():
class foo:
def __init__(self, data):
self.data = data
class tagfoo(jsontag):
__slots__ = ()
key = " f"
def check(self, value):
return isinstance(value, foo)
def to_json(self, value):
return self.serializer.tag(value.data)
def to_python(self, value):
return foo(value)
s = taggedjsonserializer()
s.register(tagfoo)
assert s.loads(s.dumps(foo("bar"))).data == "bar"
def test_tag_interface():
t = jsontag(none)
pytest.raises(notimplementederror, t.check, none)
pytest.raises(notimplementederror, t.to_json, none)
pytest.raises(notimplementederror, t.to_python, none)
def test_tag_order():
class tag1(jsontag):
key = " 1"
class tag2(jsontag):
key = " 2"
s = taggedjsonserializer()
s.register(tag1, index=-1)
assert isinstance(s.order[-2], tag1)
s.register(tag2, index=none)
assert isinstance(s.order[-1], tag2)