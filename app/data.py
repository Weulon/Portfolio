# app/data.py

collections = [
    {
        "id": "ML_Collection",
        "title": "ML_Collection",
        "subtitle": "Лимитировання коллекция",
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
    ,
    {
        "id": "neo-automatons",
        "title": "Neo Automatons",
        "subtitle": "Prototype Series",
        "image": "/static/images/neo-automatons.jpg",
        "description": "Экспериментальная серия прототипов с модульными компонентами и нестандартными материалами.",
        "badge": "NEW"
    }
]

figures = [
    {
        "id": "ri-001",
        "collection_id": "ML_Collection",
        "title": "Fanny Aspirant",
        "price": "$180",
        "status": "available",
        "status_text": "В наличии",
        "description": "MLBB Collection",
        "size": "17 см",
        "material": "Металл, пластик, светодиоды",
        "images": [
            "/static/images/fanny-1.jpg",
            "/static/images/fanny-2.jpg",
            "/static/images/fanny-3.jpg"
        ],
        "is_available": True
    },
    {
        "id": "ri-002",
        "collection_id": "ML_Collection",
        "title": "Аргус",
        "price": "$160",
        "status": "order",
        "status_text": "На заказ",
        "description": "MLBB Collection",
        "size": "17 см",
        "material": "PLA",
        "images": [
            "/static/images/argus-1.jpg",
            "/static/images/argus-2.jpg",
            "/static/images/argus-3.jpg"
            
        ],
        "is_available": False
    },
    {
        "id": "ind-001",
        "collection_id": "ML_Collection",
        "title": "Ангела",
        "price": "$170",
        "status": "sold",
        "status_text": "Продано",
        "description": "MLBB Collection",
        "size": "18 см",
        "material": "PLA",
        "images": [
            "/static/images/angela-1.jpg"
        ],
        "is_available": True
    },
    {
        "id": "tp-001",
        "collection_id": "ML_Collection",
        "title": "Мия",
        "price": "$180",
        "status": "order",
        "status_text": "На заказ",
        "description": "MLBB Collection",
        "size": "18 см",
        "material": "PLA",
        "images": [
            "/static/images/mia-1.png"
        ],
        "is_available": True
    },
    {
        "id": "tp-002",
        "collection_id": "ML_Collection",
        "title": "Бартс",
        "price": "$80",
        "status": "Sold",
        "status_text": "Продано",
        "description": "MLBB Collection",
        "size": "17 см",
        "material": "PLA",
        "images": [
            "/static/images/barts-1.jpg"
        ],
        "is_available": True
    },
    {
        "id": "sea-001",
        "collection_id": "ML_Collection",
        "title": "X-Borg",
        "price": "$130",
        "status": "sold",
        "status_text": "Продано",
        "description": "MLBB Collection",
        "size": "18 см",
        "material": "PLA",
        "images": [
            "/static/images/xborg-1.jpg"
        ],
        "is_available": False
    },
    {
        "id": "ri-003",
        "collection_id": "ML_Collection",
        "title": "Diggie",
        "price": "$130",
        "status": "order",
        "status_text": "На заказ",
        "description": "MLBB Collection",
        "size": "19 см",
        "material": "PLA",
        "images": [
            "/static/images/diggie-1.jpg"
        ],
        "is_available": True
    }
    ,
    {
        "id": "ri-004",
        "collection_id": "ML_Collection",
        "title": "Лилия",
        "price": "$215",
        "status": "sold",
        "status_text": "Продано",
        "description": "MLBB Collection",
        "size": "23 см",
        "material": "PLA",
        "images": [
            "/static/images/lilia-1.jpg"
        ],
        "is_available": False
    },
    {
        "id": "ri-005",
        "collection_id": "ML_Collection",
        "title": "Грейнджер",
        "price": "$199",
        "status": "order",
        "status_text": "На заказ",
        "description": "MLBB Collection",
        "size": "21 см",
        "material": "PLA",
        "images": [
            "/static/images/grandger-1.jpg"
        ],
        "is_available": True
    },
    {
        "id": "ri-006",
        "collection_id": "robot-ivan",
        "title": "Ivan Medic",
        "price": "$225",
        "status": "available",
        "status_text": "В наличии",
        "description": "Медицинский робот с набором инструментов для экстренной помощи и светодиодной индикацией.",
        "size": "22 см",
        "material": "Металл, пластик, светодиоды",
        "images": [
            "/static/images/ivan-3.jpg",
            "/static/images/portal-1.jpg"
        ],
        "is_available": True
    }
    ,
    {
        "id": "ri-007",
        "collection_id": "robot-ivan",
        "title": "Ivan Mechanic",
        "price": "$230",
        "status": "available",
        "status_text": "В наличии",
        "description": "Механик Иван — мастер на все руки, с инструментами и подвижными деталями. Лимитированная серия.",
        "size": "23 см",
        "material": "Металл, пластик",
        "images": [
            "/static/images/ivan-mechanic-1.jpg"
        ],
        "is_available": True
    }
    ,
    {
        "id": "na-001",
        "collection_id": "neo-automatons",
        "title": "Prototype A1",
        "price": "$350",
        "status": "available",
        "status_text": "В наличии",
        "description": "Первый прототип из серии Neo Automatons с регенерирующей подсветкой и сменными панелями.",
        "size": "28 см",
        "material": "Алюминий, смола, RGB LED",
        "images": [
            "/static/images/neo-1.jpg",
            "/static/images/neo-2.jpg"
        ],
        "is_available": True
    },
    {
        "id": "na-002",
        "collection_id": "neo-automatons",
        "title": "Prototype B2",
        "price": "$370",
        "status": "order",
        "status_text": "На заказ",
        "description": "Улучшенная версия B2 с интегрированной электроникой и эффектом свечения в темноте.",
        "size": "30 см",
        "material": "Титан, смола, люминесцентная краска",
        "images": [
            "/static/images/neo-3.jpg",
            "/static/images/neo-4.jpg"
        ],
        "is_available": True
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