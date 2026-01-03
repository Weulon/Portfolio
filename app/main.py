
import os
import sys
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

APP_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR_PATH)
app = FastAPI()
TEMPLATES_DIR = os.path.join(APP_DIR_PATH, "templates")
STATIC_DIR = os.path.join(os.path.dirname(APP_DIR_PATH), "static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Импортируем ВСЕ нужные данные из data.py
try:
    from data import collections, figures
    from data import about_text
except ImportError as e:
    print(f"Ошибка импорта из data.py: {e}")
    collections = []
    figures = []
    about_text = "# О проекте\n\nИнформация о проекте появится здесь в ближайшее время."







@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/debug/static-dir")
def debug_static_dir():
    import os
    return {
        "STATIC_DIR": STATIC_DIR,
        "exists": os.path.exists(STATIC_DIR),
        "images_path": os.path.join(STATIC_DIR, "images"),
        "images_exist": os.path.exists(os.path.join(STATIC_DIR, "images")),
        "files": os.listdir(os.path.join(STATIC_DIR, "images")) if os.path.exists(os.path.join(STATIC_DIR, "images")) else []
    }


@app.get("/debug/collections")
def debug_collections():
    return {
        "collections_count": len(collections),
        "collections": collections[:2] if collections else "empty"
    }


app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)




# ======================================================
# ROUTES

# Каталог без выбора коллекции — показать все коллекции и все фигурки
@app.get("/collection", response_class=HTMLResponse)
def all_collections_page(request: Request):
    return templates.TemplateResponse(
        "collection.html",
        {
            "request": request,
            "collection": {"title": "Все коллекции", "subtitle": "Все фигурки из всех коллекций", "description": "Здесь собраны все фигурки из всех коллекций."},
            "figures": figures,
        },
    )
# ======================================================

# Страница курса «Подготовка 3D-модели к печати»
@app.get("/courses/printing", response_class=HTMLResponse)
def course_printing_page(request: Request):
    return templates.TemplateResponse(
        "course_printing.html",
        {"request": request},
    )

# Страница «Обучение»
@app.get("/courses", response_class=HTMLResponse)
def courses_page(request: Request):
    return templates.TemplateResponse(
        "courses.html",
        {"request": request},
    )

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "collections": collections,
        },
    )


@app.get("/collection/{collection_id}", response_class=HTMLResponse)
def collection_page(request: Request, collection_id: str):
    collection = next(
        (c for c in collections if c["id"] == collection_id),
        None
    )

    if not collection:
        return HTMLResponse("Коллекция не найдена", status_code=404)

    items = [
        f for f in figures if f["collection_id"] == collection_id
    ]

    return templates.TemplateResponse(
        "collection.html",
        {
            "request": request,
            "collection": collection,
            "figures": items,
        },
    )


@app.get("/figure/{figure_id}", response_class=HTMLResponse)
def figure_page(request: Request, figure_id: str):
    figure = next(
        (f for f in figures if f["id"] == figure_id),
        None
    )

    if not figure:
        return HTMLResponse("Фигурка не найдена", status_code=404)

    return templates.TemplateResponse(
        "figure.html",
        {
            "request": request,
            "figure": figure,
        },
    )


# В main.py обновите about_page:
@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {
            "request": request,
            "profile": about_text,  # Передаем данные профиля
        },
    )

# ======================================================
# LOCAL RUN
# ======================================================

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)