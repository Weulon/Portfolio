import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Импортируем ВСЕ нужные данные из data.py
try:
    from data import collections, figures
    # Проверяем, есть ли about_text в data.py
    from data import about_text
except ImportError as e:
    print(f"Ошибка импорта из data.py: {e}")
    # Создаем пустые структуры для теста
    collections = []
    figures = []
    about_text = "# О проекте\n\nИнформация о проекте появится здесь в ближайшее время."

# ======================================================
# БАЗОВЫЕ ПУТИ (работает из любой точки запуска)
# ======================================================

CURRENT_FILE = os.path.abspath(__file__)
APP_DIR = os.path.dirname(CURRENT_FILE)
BASE_DIR = os.path.dirname(APP_DIR)

TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ======================================================
# APP
# ======================================================

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# ======================================================
# ROUTES
# ======================================================

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