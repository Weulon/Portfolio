#!/usr/bin/env python3
import re
import json
import os


def auto_add_collection():
    """АВТОМАТИЧЕСКИ добавляет новую коллекцию в data.py"""

    print("=== АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ КОЛЛЕКЦИИ ===\n")

    # 1. Запрашиваем данные
    print("📝 Введите данные новой коллекции:")
    print("-" * 40)

    collection_id = input("1. ID коллекции (англ. буквы, без пробелов, например: 'space-explorers'): ").strip()
    title = input("2. Название коллекции (например: 'Космические исследователи'): ").strip()
    subtitle = input("3. Подзаголовок (например: 'Открытие галактик'): ").strip()

    # Предлагаем варианты для изображения
    print("\n4. Изображение коллекции:")
    print("   a) Использовать placeholder (автоматически)")
    print("   b) Указать свой путь")
    image_choice = input("   Выберите вариант (a/b): ").strip().lower()

    if image_choice == 'a':
        # Создаём placeholder URL
        image_text = title.replace(' ', '+').replace('/', '')
        image = f"https://via.placeholder.com/600x400/1A1A1A/7C4DFF?text={image_text}"
    else:
        image = input("   Путь к изображению (например: /static/images/space.jpg): ").strip()

    description = input("5. Описание коллекции: ").strip()

    print("\n6. Бейдж (метка):")
    print("   a) NEW (новинка)")
    print("   b) SOLD OUT (распродано)")
    print("   c) HOT (популярное)")
    print("   d) LIMITED (ограниченный тираж)")
    print("   e) Без бейджа")
    badge_choice = input("   Выберите вариант (a/b/c/d/e): ").strip().lower()

    badge_map = {
        'a': 'NEW',
        'b': 'SOLD OUT',
        'c': 'HOT',
        'd': 'LIMITED',
        'e': None
    }
    badge = badge_map.get(badge_choice, None)

    # 2. Создаём объект коллекции
    new_collection = {
        "id": collection_id,
        "title": title,
        "subtitle": subtitle,
        "image": image,
        "description": description,
        "badge": badge
    }

    print(f"\n✅ Создана коллекция: {title}")

    # 3. Читаем текущий файл data.py
    data_file = "app/data.py"

    if not os.path.exists(data_file):
        print(f"❌ Файл {data_file} не найден!")
        return

    with open(data_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 4. Находим список collections и добавляем новую коллекцию
    # Ищем pattern: collections = [ {...}, {...} ]
    pattern = r'collections\s*=\s*\[(.*?)\]'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        print("❌ Не найден список collections в data.py")
        return

    collections_content = match.group(1)

    # Определяем, куда вставить новую коллекцию (перед закрывающей скобкой)
    # Находим последнюю коллекцию перед ]
    lines = collections_content.strip().split('\n')

    # Формируем текст новой коллекции
    new_collection_text = json.dumps(new_collection, ensure_ascii=False, indent=4)

    # Добавляем запятую если перед нами уже есть коллекции
    if collections_content.strip():
        new_collection_text = ',\n' + new_collection_text

    # Вставляем новую коллекцию перед закрывающей скобкой
    new_collections_content = collections_content + new_collection_text

    # Заменяем старый список на новый
    new_content = content.replace(
        f'collections = [{collections_content}]',
        f'collections = [{new_collections_content}]'
    )

    # 5. Спрашиваем про фигурки
    add_figures = input("\n📦 Добавить фигурки для этой коллекции? (y/n): ").strip().lower()

    if add_figures == 'y':
        figures = []
        figure_count = 1

        while True:
            print(f"\n--- Фигурка #{figure_count} ---")
            figure_id = input(f"  ID фигурки (например: {collection_id}-{figure_count:03d}): ").strip()
            if not figure_id:
                figure_id = f"{collection_id}-{figure_count:03d}"

            figure_title = input("  Название фигурки: ").strip()
            price = input("  Цена (например: $250): ").strip()

            print("  Статус:")
            print("    1) В наличии")
            print("    2) На заказ")
            print("    3) Продано")
            status_choice = input("  Выберите статус (1/2/3): ").strip()

            status_map = {
                '1': ('available', 'В наличии'),
                '2': ('order', 'На заказ'),
                '3': ('sold', 'Продано')
            }
            status, status_text = status_map.get(status_choice, ('available', 'В наличии'))

            description = input("  Описание: ").strip()
            size = input("  Размер (например: 25 см): ").strip() or "25 см"
            material = input("  Материал: ").strip() or "Смола, акриловые краски"

            # Создаём placeholder для изображения фигурки
            figure_image_text = figure_title.replace(' ', '+').replace('/', '')
            figure_image = f"https://via.placeholder.com/800x600/1A1A1A/7C4DFF?text={figure_image_text}"

            new_figure = {
                "id": figure_id,
                "collection_id": collection_id,
                "title": figure_title,
                "price": price,
                "status": status,
                "status_text": status_text,
                "description": description,
                "size": size,
                "material": material,
                "images": [figure_image],
                "is_available": status == 'available'
            }

            figures.append(new_figure)

            more = input("\n  Добавить ещё фигурку? (y/n): ").strip().lower()
            if more != 'y':
                break

            figure_count += 1

        # Добавляем фигурки в список figures
        figures_pattern = r'figures\s*=\s*\[(.*?)\]'
        figures_match = re.search(figures_pattern, new_content, re.DOTALL)

        if figures_match:
            figures_content = figures_match.group(1)

            # Формируем текст новых фигурок
            new_figures_text = ''
            for fig in figures:
                fig_text = json.dumps(fig, ensure_ascii=False, indent=4)
                if figures_content.strip():
                    fig_text = ',\n' + fig_text
                figures_content += fig_text

            # Заменяем старый список фигурок на новый
            new_content = new_content.replace(
                f'figures = [{figures_match.group(1)}]',
                f'figures = [{figures_content}]'
            )

    # 6. Записываем обновлённый файл
    with open(data_file, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"\n🎉 ГОТОВО! Коллекция '{title}' добавлена в {data_file}")
    print("\n📋 Что нужно сделать дальше:")
    print("   1. Перезапустить сервер: python -m app.main")
    print("   2. Открыть http://localhost:8000")
    print("   3. Новая коллекция появится на главной странице!")

    # 7. Показываем предварительный просмотр
    print(f"\n👁️  ПРЕДПРОСМОТР новой коллекции:")
    print(f"   Название: {title}")
    print(f"   Подзаголовок: {subtitle}")
    print(f"   ID: {collection_id}")
    print(f"   Бейдж: {badge if badge else 'нет'}")
    print(f"   Фигурок добавлено: {len(figures) if 'figures' in locals() else 0}")


if __name__ == "__main__":
    try:
        auto_add_collection()
    except KeyboardInterrupt:
        print("\n\n❌ Отменено пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")