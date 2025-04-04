from flask import flask
def create_app():
return flask("app")
def create_app2(foo, bar):
return flask("_".join(["app2", foo, bar]))
def no_app():
pass