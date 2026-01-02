# app/data.py

collections = [
    {
        "id": "robot-ivan",
        "title": "Robot Ivan",
        "subtitle": "Limited figures",
        "image": "/static/images/robot-ivan.jpg",
        "description": "Коллекция уникальных роботизированных фигурок с ограниченным тиражом. Каждая фигурка — результат недель кропотливой работы.",
        "badge": "NEW"
    },
    {
        "id": "industrial",
        "title": "Industrial",
        "subtitle": "Handcrafted",
        "image": "/static/images/industrial.jpg",
        "description": "Фигурки в индустриальном стиле, созданные вручную с использованием металлических элементов и патины.",
        "badge": None
    },
    {
        "id": "time-portals",
        "title": "Time Portals",
        "subtitle": "3D printed",
        "image": "/static/images/time-portals.jpg",
        "description": "Футуристические порталы времени, созданные с использованием 3D-печати и светодиодной подсветки.",
        "badge": None
    },
    {
        "id": "seasonal",
        "title": "Seasonal",
        "subtitle": "Holiday themed",
        "image": "/static/images/seasonal.jpg",
        "description": "Тематические фигурки для праздников и особых событий. Ограниченные серии к каждому сезону.",
        "badge": "SOLD OUT"
    }
]

figures = [
    {
        "id": "ri-001",
        "collection_id": "robot-ivan",
        "title": "Ivan Protector",
        "price": "$240",
        "status": "available",
        "status_text": "В наличии",
        "description": "Робот-защитник с подвижными элементами и светящимися деталями. Ограниченная серия из 50 экземпляров.",
        "size": "25 см",
        "material": "Металл, пластик, светодиоды",
        "images": [
            "/static/images/ivan-1.jpg",
            "/static/images/ivan-2.jpg",
            "/static/images/ivan-3.jpg"
        ],
        "is_available": True
    },
    {
        "id": "ri-002",
        "collection_id": "robot-ivan",
        "title": "Ivan Explorer",
        "price": "$210",
        "status": "sold",
        "status_text": "Продано",
        "description": "Исследователь космоса с детализированным оборудованием и картой звёздного неба на спине.",
        "size": "22 см",
        "material": "Металл, смола, люминесцентная краска",
        "images": [
            "/static/images/explorer-1.jpg",
            "/static/images/explorer-2.jpg"
        ],
        "is_available": False
    },
    {
        "id": "ind-001",
        "collection_id": "industrial",
        "title": "Steam Mechanic",
        "price": "$180",
        "status": "available",
        "status_text": "В наличии",
        "description": "Механик парового века с работающими шестерёнками и паровыми трубками. Все элементы подвижны.",
        "size": "20 см",
        "material": "Латунь, медь, дерево",
        "images": [
            "/static/images/mechanic-1.jpg",
            "/static/images/mechanic-2.jpg"
        ],
        "is_available": True
    },
    {
        "id": "tp-001",
        "collection_id": "time-portals",
        "title": "Portal Keeper",
        "price": "$320",
        "status": "order",
        "status_text": "На заказ",
        "description": "Хранитель временного портала с программируемой RGB-подсветкой. Изменяет цвет в зависимости от настроения.",
        "size": "30 см",
        "material": "Смола, акрил, электроника",
        "images": [
            "/static/images/portal-1.jpg",
            "/static/images/portal-2.jpg",
            "/static/images/portal-3.jpg",
            "/static/images/portal-4.jpg"
        ],
        "is_available": True
    },
    {
        "id": "tp-002",
        "collection_id": "time-portals",
        "title": "Chrono Sphere",
        "price": "$280",
        "status": "available",
        "status_text": "В наличии",
        "description": "Сфера времени с плавающими элементами внутри. Создаёт гипнотический эффект при вращении.",
        "size": "18 см диаметр",
        "material": "Стекло, металл, магнитная жидкость",
        "images": [
            "/static/images/sphere-1.jpg",
            "/static/images/sphere-2.jpg"
        ],
        "is_available": True
    },
    {
        "id": "sea-001",
        "collection_id": "seasonal",
        "title": "Winter Guardian",
        "price": "$190",
        "status": "sold",
        "status_text": "Продано",
        "description": "Снежный страж с мерцающими кристаллами и инеевым покрытием. Создан к зимнему солнцестоянию.",
        "size": "21 см",
        "material": "Хрусталь, серебро, светодиоды",
        "images": [
            "/static/images/winter-1.jpg",
            "/static/images/winter-2.jpg"
        ],
        "is_available": False
    }
]

# В data.py обновите about_text:
about_text = {
    "title": "3D Дизайнер / Скульптор",
    "subtitle": "Автор коллекционных фигурок",
    "description": "Создаю уникальные фигурки и 3D-модели на заказ. Выполняю скульптинг, моделирование и анимацию для игр и коллекционных моделей.",
    "telegram": "@author_example",
    "email": "designer@example.com",
    "artstation": "https://www.artstation.com",
    "instagram": "https://www.instagram.com",
    "skills": [
        {"name": "3D Моделирование", "tools": "Blender, ZBrush, Maya", "icon": "cube"},
        {"name": "Текстурирование", "tools": "Substance Painter, Photoshop", "icon": "paint-brush"},
        {"name": "3D Печать", "tools": "SLA, FDM, постобработка", "icon": "print"},
        {"name": "Роспись", "tools": "Акрил, эмали, аэрография", "icon": "palette"},
        {"name": "Скульптинг", "tools": "Цифровая и традиционная", "icon": "robot"},
        {"name": "Концепт-арт", "tools": "Идеи и визуализация", "icon": "lightbulb"}
    ]
}

# Вспомогательные функции
def get_collection(collection_id):
    """Получить коллекцию по ID"""
    return next((c for c in collections if c["id"] == collection_id), None)

def get_figure(figure_id):
    """Получить фигурку по ID"""
    return next((f for f in figures if f["id"] == figure_id), None)

def get_figures_by_collection(collection_id):
    """Получить все фигурки в коллекции"""
    return [f for f in figures if f["collection_id"] == collection_id]

def get_all_figures():
    """Получить все фигурки"""
    return figures

# app/data.py - добавьте в конец файла

profile_data = {
    "name": "Александр Иванов",  # Ваше имя
    "role": "3D Дизайнер / Скульптор",
    "description": "Создаю уникальные фигурки и 3D-модели на заказ. Выполняю скульптинг, моделирование и анимацию для игр и коллекционных моделей.",
    "photo": "/static/images/profile-photo.jpg",  # Путь к вашему фото
    "contacts": {
        "telegram": "@testobotnub_bot",  # Ваш Telegram
        "email": "artist@example.com",    # Ваш Email
        "phone": "+7 (XXX) XXX-XX-XX",    # Ваш телефон
        "artstation": "https://www.artstation.com/yourprofile",
        "instagram": "https://www.instagram.com/yourprofile",
        "behance": "https://www.behance.net/yourprofile",
    },
    "skills": [
        "3D Моделирование", "Цифровой скульптинг", "Текстурирование",
        "3D Печать", "Ручная роспись", "Концепт-арт",
        "Blender", "ZBrush", "Substance Painter", "Маркетинг"
    ],
    "stats": {
        "experience": "5+",
        "figures": "100+",
        "clients": "50+",
        "support": "24/7"
    }
}