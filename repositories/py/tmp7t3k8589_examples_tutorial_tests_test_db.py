import sqlite3
import pytest
from flaskr.db import get_db
def test_get_close_db(app):
with app.app_context():
db = get_db()
assert db is get_db()
with pytest.raises(sqlite3.programmingerror) as e:
db.execute("select 1")
assert "closed" in str(e.value)
def test_init_db_command(runner, monkeypatch):
class recorder:
called = false
def fake_init_db():
recorder.called = true
monkeypatch.setattr("flaskr.db.init_db", fake_init_db)
result = runner.invoke(args=["init-db"])
assert "initialized" in result.output
assert recorder.called