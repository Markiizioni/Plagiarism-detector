import packaging.version
from pallets_sphinx_themes import get_version
from pallets_sphinx_themes import projectlink
project = "flask"
copyright = "2010 pallets"
author = "pallets"
release, version = get_version("flask")
default_role = "code"
extensions = [
"sphinx.ext.autodoc",
"sphinx.ext.extlinks",
"sphinx.ext.intersphinx",
"sphinxcontrib.log_cabinet",
"sphinx_tabs.tabs",
"pallets_sphinx_themes",
]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = true
extlinks = {
"issue": ("https:
"pr": ("https:
"ghsa": ("https:
}
intersphinx_mapping = {
"python": ("https:
"werkzeug": ("https:
"click": ("https:
"jinja": ("https:
"itsdangerous": ("https:
"sqlalchemy": ("https:
"wtforms": ("https:
"blinker": ("https:
}
html_theme = "flask"
html_theme_options = {"index_sidebar_logo": false}
html_context = {
"project_links": [
projectlink("donate", "https:
projectlink("pypi releases", "https:
projectlink("source code", "https:
projectlink("issue tracker", "https:
projectlink("chat", "https:
]
}
html_sidebars = {
"index": ["project.html", "localtoc.html", "searchbox.html", "ethicalads.html"],
"**": ["localtoc.html", "relations.html", "searchbox.html", "ethicalads.html"],
}
singlehtml_sidebars = {"index": ["project.html", "localtoc.html", "ethicalads.html"]}
html_static_path = ["_static"]
html_favicon = "_static/shortcut-icon.png"
html_logo = "_static/flask-vertical.png"
html_title = f"flask documentation ({version})"
html_show_sourcelink = false
gettext_uuid = true
gettext_compact = false
def github_link(name, rawtext, text, lineno, inliner, options=none, content=none):
app = inliner.document.settings.env.app
release = app.config.release
base_url = "https:
if text.endswith(">"):
words, text = text[:-1].rsplit("<", 1)
words = words.strip()
else:
words = none
if packaging.version.parse(release).is_devrelease:
url = f"{base_url}main/{text}"
else:
url = f"{base_url}{release}/{text}"
if words is none:
words = url
from docutils.nodes import reference
from docutils.parsers.rst.roles import set_classes
options = options or {}
set_classes(options)
node = reference(rawtext, words, refuri=url, **options)
return [node], []
def setup(app):
app.add_role("gh", github_link)