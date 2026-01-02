import os
import shutil
from jinja2 import Environment, FileSystemLoader

# Пути
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "templates")
REPO_ROOT = os.path.dirname(CURRENT_DIR)
STATIC_SRC = os.path.join(REPO_ROOT, "static")
OUT_DIR = os.path.join(REPO_ROOT, "docs")  # GitHub Pages по умолчанию может брать /docs

# Импорт данных
try:
    from data import collections, figures, about_text
except Exception:
    collections, figures, about_text = [], [], ""

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

os.makedirs(OUT_DIR, exist_ok=True)

# Скопировать статические файлы
if os.path.exists(STATIC_SRC):
    dst_static = os.path.join(OUT_DIR, "static")
    if os.path.exists(dst_static):
        shutil.rmtree(dst_static)
    shutil.copytree(STATIC_SRC, dst_static)


class _URL:
    def __init__(self, path):
        self.path = path


class _Request:
    def __init__(self, path):
        self.url = _URL(path)


def render_template(template_name, target_path, **ctx):
    tpl = env.get_template(template_name)

    # Подставляем request с url.path, чтобы шаблоны, ожидающие request, работали корректно
    if 'request' not in ctx:
        # Определяем путь по имени шаблона
        if template_name == 'index.html':
            path = '/'
        elif template_name == 'about.html':
            path = '/about'
        elif template_name == 'collection.html' or '/collection/' in target_path:
            path = '/collection'
        elif template_name == 'figure.html' or '/figure/' in target_path:
            path = '/figure'
        else:
            path = '/'
        ctx['request'] = _Request(path)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(tpl.render(**ctx))


# index
render_template(
    "index.html",
    os.path.join(OUT_DIR, "index.html"),
    collections=collections,
)

# about
render_template(
    "about.html",
    os.path.join(OUT_DIR, "about.html"),
    profile=about_text,
)

# collection pages
collections_dir = os.path.join(OUT_DIR, "collection")
os.makedirs(collections_dir, exist_ok=True)
for c in collections:
    items = [f for f in figures if f.get("collection_id") == c.get("id")]
    render_template(
        "collection.html",
        os.path.join(collections_dir, f"{c.get('id')}.html"),
        collection=c,
        figures=items,
    )

# figure pages
figures_dir = os.path.join(OUT_DIR, "figure")
os.makedirs(figures_dir, exist_ok=True)
for f in figures:
    render_template(
        "figure.html",
        os.path.join(figures_dir, f"{f.get('id')}.html"),
        figure=f,
    )

print("Static site built into docs/")

