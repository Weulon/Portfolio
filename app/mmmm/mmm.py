# --- МАССОВАЯ РАССЫЛКА С ЛИМИТАМИ И БАТЧАМИ ---
import time

def send_mass_message(users, text, batch_size=20, pause_between_batches=5):
    """
    users: список user_id
    text: текст рассылки
    batch_size: сколько сообщений отправлять за раз
    pause_between_batches: пауза между батчами (сек)
    """
    for i in range(0, len(users), batch_size):
        batch = users[i:i+batch_size]
        for user_id in batch:
            try:
                bot.send_message(user_id, text)
            except Exception as e:
                print(f"Ошибка для {user_id}: {e}")
        if i + batch_size < len(users):
            time.sleep(pause_between_batches)

# Пример использования:
# users = db.get_users()  # Получить список user_id
# send_mass_message(users, "Ваша рассылка", batch_size=20, pause_between_batches=5)
import random
import time
import sched
import sqlite3
import os
import threading
import db
import telebot
from telebot import types
import requests

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- Константы для блока обучения ---
EDU_BTN_TEXT = '🎓 Сделать модель самому'
EDU_MESSAGE = (
    'Не хочешь покупать готовые модели — можешь научиться делать их сам.\n\n'
    'Я собрал полный рабочий процесс: от извлечения модели из игры до подготовки к 3D-печати.\n\n'
    'Без теории, только реальные шаги, типовые ошибки и рабочая логика.\n\n'
    'После покупки ты получаешь безлимитный доступ к закрытому каналу с обновлениями и новыми гайдами.'
)
EDU_MORE_BTN_TEXT = '▶ Подробнее об обучении'
EDU_LINK = 'https://portfolio-4t5k.onrender.com/courses/printing'  # В реальном проекте брать из env


# Установка статуса администратора
admin_user_id = 631107332  # Ваш пользовательский ID
db.update_admin_status(admin_user_id, 1)

# Создание словарей для хранения блокировок
user_locks = {}
user_locks_send = {}
user_locks_print = {}

sendall_stop = False  # Флаг для остановки рассылки

bot = telebot.TeleBot('6336246475:AAFDyyk6jUjdxgBTqhdPPnfo_-2REI9XqZE')


def insert_user_id(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()

    c.execute('''INSERT OR REPLACE INTO users (user_id) VALUES (?)''', (user_id,))

    conn.commit()
    conn.close()

# Изменение обработчика команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    """
    Приветствует пользователя, регистрирует его в базе, при необходимости
    инициализирует его данные и открывает главное меню.
    """
    # Отправляем приветственное сообщение пользователю
    bot.send_message(message.chat.id, 'Добро пожаловать в MLBB')
    # Сохраняем идентификатор пользователя в базе данных
    user_id = message.from_user.id
    insert_user_id(user_id)
    # Проверяем, существует ли запись о пользователе; если нет, инициализируем её
    user_data = db.get_user_data(user_id)
    if user_data is None:
        user_data = {
            # 'diamonds': 300,  # Удалено: алмазы
            # 'printers': [],   # Удалено: принтеры
            'models': [],
            'printed_models': []
        }
        # Добавляем несколько стартовых моделей
        user_data['models'].append({'name': 'Random file.stl', 'price': 10})
        user_data['models'].append({'name': 'Фигурка Гаррош', 'price': 10})
        user_data['models'].append({'name': 'Фигурка на заказ', 'price': 10})
        user_data['models'].append({'name': 'Фигурка из warcraft', 'price': 10})
        # Сохраняем данные пользователя в базу
        db.insert_user_data(
            user_id,
            # user_data['diamonds'],
            # str(user_data['printers']),
            str(user_data['models']),
            str(user_data['printed_models'])
        )
        # Сообщаем пользователю о начислении стартового баланса
        bot.send_message(
            user_id,
            "Добро пожаловать в Пиратскую Бухту, о, Моряк! 🏴‍☠\n\n"
            "У нас – сокровищница увлекательных 3D моделей из популярных игровых миров. "
            # "Как настоящий пират, ты можешь откопать сокровища в виде алмазов, "
            "которые смогут быть обменяны на разнообразные товары и онлайн услуги. "
            # "А для начала путешествия, тебе предоставляется щедрым жестом 300💎. "
            "Используй их с умом! ⚓🏴‍☠💰"
        )
    # Показываем пользователю меню
    onemenu(message)






scheduler = sched.scheduler(time.time, time.sleep)

# Dictionary to store user language preferences
user_languages = {}

# Путь к директории "main"
current_dir = os.path.dirname(os.path.abspath(__file__))
first_image_path = os.path.join(current_dir, 'juju.jpg')
second_image_path = os.path.join(current_dir, 'dikayl.jpg')

# Словарь для хранения ссылок
links = {}

# (Удалён лишний обработчик /start; логика перенесена в handle_start)

@bot.message_handler(commands=['create_button'])
def create_button(message):
    user_id = message.from_user.id
    args = message.text.split()[1:]

    if len(args) != 2:
        bot.send_message(user_id, "Используйте команду следующим образом: /create_button <название> <ссылка>")
        return

    button_name, button_url = args
    links[user_id] = button_url
    bot.send_message(user_id, f"Создана ссылка '{button_name}' с адресом: {button_url}")


# --- Обработчик рассылки только для администратора, без ссылок, с лимитами ---
@bot.message_handler(commands=['sendall'])
def handle_sendall(message):
    global sendall_stop
    sendall_stop = False
    user_id = message.from_user.id
    if user_id != admin_user_id:
        bot.send_message(message.chat.id, "Рассылка доступна только администратору.")
        return
    command_len = len('/sendall')
    command_text = message.text[command_len:].strip()
    if not command_text:
        bot.send_message(message.chat.id, "Укажите текст рассылки после /sendall.")
        return
    users = db.get_users()
    batch_size = 20
    pause_between_batches = 5
    sent = 0
    for i in range(0, len(users), batch_size):
        if sendall_stop:
            bot.send_message(message.chat.id, f"Рассылка остановлена. Отправлено сообщений: {sent}")
            return
        batch = users[i:i+batch_size]
        for user_id in batch:
            try:
                bot.send_message(user_id, command_text)
                sent += 1
            except Exception:
                pass
        if i + batch_size < len(users):
            time.sleep(pause_between_batches)
    bot.send_message(message.chat.id, f"Рассылка завершена. Отправлено сообщений: {sent}")

# Команда для остановки рассылки
@bot.message_handler(commands=['stop_sendall'])
def handle_stop_sendall(message):
    global sendall_stop
    user_id = message.from_user.id
    if user_id != admin_user_id:
        bot.send_message(message.chat.id, "Остановка рассылки доступна только администратору.")
        return
    sendall_stop = True
    bot.send_message(message.chat.id, "Остановка рассылки запрошена. Текущий процесс будет прерван.")
    user_id = message.from_user.id
    if user_id != admin_user_id:
        bot.send_message(message.chat.id, "У вас нет прав для рассылки.")
        return

    command_len = len('/sendall')
    command_text = message.text[command_len:].strip()
    if not command_text:
        bot.send_message(message.chat.id, "Введите текст для рассылки после команды.")
        return

    users = db.get_users()
    batch_size = 20
    pause_between_batches = 5
    sent = 0
    for i in range(0, len(users), batch_size):
        batch = users[i:i+batch_size]
        for uid in batch:
            try:
                bot.send_message(uid, command_text)
                sent += 1
            except Exception as e:
                print(f"Ошибка при отправке сообщения пользователю {uid}: {e}")
        if i + batch_size < len(users):
            time.sleep(pause_between_batches)
    bot.send_message(message.chat.id, f"Рассылка завершена. Отправлено сообщений: {sent}")

# Функция onemenu
@bot.message_handler(commands=['onemenu'])
def onemenu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    btn1 = types.KeyboardButton('Mobile Legends BB')
    markup.row(btn1)

    btn5 = types.KeyboardButton('Brawl Stars')  # Кнопка для Brawl Stars
    markup.row(btn5)

    btn6 = types.KeyboardButton('World of Warcraft')  # Кнопка для WoW
    markup.row(btn6)
    
 

    #btn4 = types.KeyboardButton('Заказать 3D фигурку')
    #markup.row(btn4)

    btn2 = types.KeyboardButton('Связь')
    btn3 = types.KeyboardButton('Инфо📄')
    markup.row(btn2, btn3)

    bot.send_message(message.chat.id, "Выберите игру или опцию:", reply_markup=markup)



    bot.send_message(message.chat.id, 'Меню', reply_markup=markup)

# Обработчик текстового сообщения "Заказать 3D фигурку"
@bot.message_handler(func=lambda message: message.text == 'Заказать 3D фигурку')
def order_3d_figure(message):
    bot.reply_to(message, 'Ссылка на заказ 3D модели: https://telegra.ph/3D-figurka-MLBB-04-11')





@bot.message_handler(func=lambda message: message.text == 'Инфо📄')
def show_sub_menu(message):
    markup = types.ReplyKeyboardMarkup(row_width=3,resize_keyboard=True)  # Указываем ширину строки (количество кнопок в одной строке)

    btn1 = types.KeyboardButton('Работы')
    btn2 = types.KeyboardButton('Бесплатные фигурки')  # Добавленная кнопка "Road map"
    btn3 = types.KeyboardButton('Назад')

    markup.row(btn1, btn2)
    markup.row(btn3)

    bot.send_message(message.chat.id, 'Дополнительные опции', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Работы')
def handle_works(message):
    markup = types.InlineKeyboardMarkup()
    channel_button = types.InlineKeyboardButton("Перейти в ТГК", url="https://t.me/myyawka")
    markup.add(channel_button)
    bot.send_message(message.chat.id, "Все наши работы и готовые модели вы можете посмотреть в нашем Telegram канале:", reply_markup=markup)




@bot.message_handler(func=lambda message: message.text == 'Назад')
def handle_back(message):
    onemenu(message)

@bot.message_handler(func=lambda message: message.text == 'Связь')
def handle_channels(message):
    bot.send_message(message.chat.id, 'Если есть предложения или вопросы\n1)3D печать фигурки - @dikayl\n2)Добавить что-то новое\n3)Имеется ли модель в цвете?\n4)Есть ли модели кроме MLBB?\nПиши мне по любому вопросу -> @dikayl')


@bot.message_handler(func=lambda message: message.text == 'Канал')
def handle_channels(message):
    bot.send_message(message.chat.id, 'Перейти в канал -> @Stlfre')

# -----------------------------------------------------------------------------
# Обработчики для отключённых функций
## Удалено: мини-игры, биржевые операции
# и неактивным разделам. При обращении к ним пользователю будет отправлено
# одно и то же уведомление. Это позволяет оставить остальной код нетронутым,
## Удалено: игровые и инвестиционные сценарии

def disabled_feature_message(message):
    """
    Отвечает на сообщения, связанные с отключёнными функциями. Вместо выполнения
    прежней логики пользователь получает уведомление о недоступности.
    """
    bot.send_message(message.chat.id, 'Эта функция временно недоступна.')


@bot.callback_query_handler(
    func=lambda call: (
        # Перехватываем игровые и инвестиционные callback-и,
        # а также операции с принтерами и печатью моделей
        any(call.data.startswith(prefix) for prefix in (
            'throw_', 'roll_', 'kick_', 'select_printer_', 'print_', 'sell_', 'Buy_printer_'
        ))
        or call.data in [
            'play', 'play_again', 'play_againb',
            'Buy_bitcoin', 'sell_bitcoin', 'sell_all_bitcoin',
            'check_balance', 'close_menu'
        ]
    )
)
def disabled_feature_callback(call):
    """
    Отвечает на callback‑запросы, связанные с отключёнными функциями. Вместо
    выполнения прежней логики пользователю выводится уведомление.
    """
    bot.send_message(call.message.chat.id, 'Эта функция временно недоступна.')

#bot.message_handler(func=lambda message: message.text == '-50%x🔥')
#ef Buy_diamonds(message):
    # Отправляем видео
    #video_path = r'C:\buhta\Marksman\nft_standard_card.mp4'
    #with open(video_path, 'rb') as video:
        #bot.send_video(message.chat.id, video)

    # Отправляем текстовое сообщение
    #bot.send_message(message.chat.id, 'Теперь у тебя есть возможность приобрести уникальные модели, используя свои алмазы.')
    #bot.send_message(message.chat.id, 'Самые интересные и креативные модели доступны по невероятно выгодному курсу:')
    #bot.send_message(message.chat.id, '1💵 = 60💎')
    #bot.send_message(message.chat.id, 'Откройте для себя мир бесконечных возможностей в 3D!')
    #bot.send_message(message.chat.id, 'Доступна любая форма оплаты без комиссии по выгодному курсу')
    #bot.send_message(message.chat.id, 'Пиши мне 24/7 --> @dikayl❤️ ')


@bot.message_handler(func=lambda message: message.text == 'Бесплатные фигурки')
def free_figures(message):
    markup = types.InlineKeyboardMarkup()
    channel_button = types.InlineKeyboardButton("Перейти в ТГК", url="https://t.me/myyawka")
    markup.add(channel_button)
    bot.send_message(message.chat.id, "Переходи в наш Telegram канал с бесплатными фигурками:", reply_markup=markup)



# Обработчик нажатия на кнопку "3D модели🧸"
#@bot.message_handler(func=lambda message: message.text == '3D модели🧸')
#def handle_3d_models(message):
    # Вызов функции для генерации меню 3D моделей
    #markup = generate_game_selection_menu()
    #bot.send_message(message.chat.id, 'Выберите 3D модель:', reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == '🏴‍☠Открыть сундук с сокровищами⚰️️')
def send_free_model(message):
    """
    Эта функция ранее использовалась для мини‑игры с сундуком сокровищ.
    Мини‑игры и механики с алмазами удалены, поэтому функция отключена.
    """
    bot.send_message(message.chat.id, "Функция сундука с сокровищами временно недоступна.")

@bot.message_handler(func=lambda message: message.text == 'Информация')
def handle_button_click(message):
    bot.send_message(message.chat.id, 'Я рад видеть тебя здесь ❤️ давай я тебе расскажу что тут происходит')
    bot.send_message(message.chat.id, 'Если ты пришел сюда, значит тебе интересны бесплатные 3D модели для печати')

    # Создаем инлайн-клавиатуру с одной кнопкой
    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text="Продолжить читать", callback_data="continue_reading")
    keyboard.add(button)

    bot.send_message(message.chat.id,
                     'Тут все просто, зарабатывай💎 Которые можно обменять на любые STL/OBJ доступные в каталоге',
                     reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "continue_reading")
def continue_reading(call):
    bot.send_message(call.message.chat.id, 'Так же...советую копить💎 эта инвестиция пригодится тебе в будущем')
    bot.send_message(call.message.chat.id, 'В будущем за алмазы ты сможешь приобрести услуги (но пока это останется секретом:)')
    bot.send_message(call.message.chat.id, 'А еще мы постоянно расширяем каталог 3D файлов интересными моделями')
    bot.send_message(call.message.chat.id, 'Ну ты это...')

    # Отправка изображения
    image_path = r"C:\buhta\Marksman\volk.jpg"
    with open(image_path, "rb") as img_file:
        bot.send_photo(call.message.chat.id, img_file)

@bot.message_handler(func=lambda message: message.text == 'Скоро...')
def printer_menu(message):
    # Перенаправляем пользователя в меню /printer
    bot.send_message(message.chat.id, 'def чёт будет):')

@bot.message_handler(commands=['8231'])
def handle_command_8231(message):
    bot.send_message(message.chat.id, "///")

tank_list = [
                  "/akai",
                  "/alice",
                  "/atlas",
                  "/barats",
                  "/baxia",
                  "/belerick",
                  "/carmilla",
                  "/edith",
                  "/franco",
                  "/fredrinn",
                  "/gatotkaca",
                  "/gloo",
                  "/grock",
                  "/hilda",
                  "/hylos",
                  "/johnson",
                  "/khufra",
                  "/lolita",
                  "/masha",
                  "/minotaur",
                  "/uranus"
                  ]
support_list = ["/nana",
                  "/diggie",
                  "/rafaela",
                  "/estes",
                  "/angela",
                  "/kaja",
                  "/faramis",
                  "/mathilda",
                  "/floryn",
                  "/carmilla"
                  ]
marksman_list = ["/beatrix",
                  "/brody",
                  "/bruno",
                  "/claude",
                  "/clint",
                  "/granger",
                  "/hanabi",
                  "/irihel",
                  "/karrie",
                  "/kimmy",
                  "/ixia",
                  "/layla",
                  "/popol",
                  "/melissa",
                  "/miya",
                  "/moskov",
                  "/natan",
                  "/wanwan",
                  "/lesley",
                  "/roger",
                  "/yisunshin",

                  ]
mage_list = ["/eudora",
                  "/esmeralda",
                  "/louyi",
                  "/valentina",
                  "/xavier",
                  "/aurora",
                  "/lunox",
                  "/alice",
                  "/gord",
                  "/kadita",
                  "/kagura",
                  "/cyclops",
                  "/vexana",
                  "/odette",
                  "/zhask",
                  "/pharsa",
                  "/valir",
                  "/change",
                  "/vale",
                  "/harith",
                  "/lylia",
                  "/cecilion",
                  "/yve",
                  "/julian",
                  "/novaria",
                  "/selena",
                  "/harley",
                  "/faramis",
                  "/nana"

                  ]

free_list = ["/eudora",
                  "/mathilda",
                  "/alucard",
                  "/balmond",
                  "/zhong",
                  "/guinevere",
                  "/fanny",
                  "/selena",
                  "/hayabusa",
                  "/lancelot",
                  "/gusion",
                  "/hanzo",
                  "/ling",
                  "/benedetta",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/alpha",
                  "/louyi"
                
                  ]

# Список доступных ассассинов
assassins_list = ["/saber",
                  "/karina",
                  "/fanny",
                  "/natalia",
                  "/selena",
                  "/hayabusa",
                  "/yisunshin",
                  "/lancelot",
                  "/gusion",
                  "/hanzo",
                  "/ling",
                  "/aamon",
                  "/joy",
                  "/nolan",
                  "/harley",
                  "/zilong",
                  "/alucard",
                  "/benedetta",
                  "/mathilda"
                  ]

# Функция для генерации списка меню команды '/assassin'
def generate_assassin_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого ассассина как отдельную кнопку в список
    for assassin in assassins_list:
        markup.add(types.KeyboardButton(assassin))
    # Добавляем кнопку "back"
    markup.add(types.KeyboardButton('back'))
    return markup

# Обработчик команды '/assassin'
@bot.message_handler(commands=['assassin'])
def show_assassin_menu(message):
    assassin_menu = generate_assassin_options_menu()
    bot.send_message(message.chat.id, "Choose a assassin:", reply_markup=assassin_menu)

# Обработчик для кнопки "back" в меню бойцов '/assassin'
@bot.message_handler(func=lambda message: message.text == 'back', content_types=['text'])
def back_to_model_options_menu_from_assassin(message):
    model_options_menu = generate_model_options_menu()
    bot.send_message(message.chat.id, "Main menu:", reply_markup=model_options_menu)


WorldBoss_list = [
    "/lich_king",
]

Alliance_list = [
    "/alliance_pack",
    "/alliance_leader",
    "/alliance_flot"

]

Ork_list = [
    "/horde_pack",
    "/horde_leader",
    "/horde_buldings"
]

# Список доступных бойцов
fighters_list = [
    "/alucard",
    "/balmond",
    "/bane",
    "/alpha",
    "/aldous",
    "/argus",
    "/arlott",
    "/aulus",
    "/freya",
    "/badang",
    "/barats",
    "/chou",
    "/dyrroth",
    "/guinevere",
    "/hilda",
    "/jawhead",
    "/khaleed",
    "/leomord",
    "/cici",
    "/lapuLapu",
    "/martis",
    "/masha",
    "/minsitthar",
    "/paquito",
    "/phoeveus",
    "/ruby",
    "/silvanna",
    "/sun",
    "/terizla",
    "/thamuz",
    "/xborg",
    "/yin",
    "/zhong"
]

@bot.message_handler(commands=['lich_king'])
def show_lich_king(message):
    lich_king_menu = "\n".join([f"{i+1}) {Lich_king_list[command]['name_ru']} - {command}" for i, command in enumerate(Lich_king_list)])
    bot.send_message(message.chat.id, lich_king_menu)

# Обновленный список Lich_king_list без цен
Lich_king_list = {
    '/lich_king_1': {
        'name_ru': 'Король-Лич',
        'photo_path': 'C:/pythonProject1/wow/lich_king.jpg'
        # Нет ссылки, значит модель платная
    },
    '/lich_king_2': {
        'name_ru': 'Пак-мобов (бесплатно)',
        'photo_path': 'C:/pythonProject1/wow/lich_mobspack.jpg',
        'link': 'https://disk.yandex.ru/d/6-5mp5ym5APzUA'  # Ссылка для бесплатной модели
    },
    '/clk': {
        'name_ru': 'Цлк (бесплатно)',
        'photo_path': 'C:/pythonProject1/wow/clk.jpg',
        'link': 'https://disk.yandex.ru/d/a2k6iunCgZ4XJA'  # Ссылка для бесплатной модели
    }
    # Добавьте остальные модели в формате '/lich_king_N': {...}
}

# Получаем список команд из Lich_king_list
lich_king_commands = list(Lich_king_list.keys())

# Обработчик для команд из Lich_king_list
@bot.message_handler(commands=[cmd.strip('/') for cmd in lich_king_commands])
def send_lich_king_model(message):
    command = '/' + message.text.split()[0].strip('/')
    if command in Lich_king_list:
        model_info = Lich_king_list[command]
        name_ru = model_info['name_ru']
        photo_path = model_info['photo_path']
        
        # Проверяем, есть ли ссылка в информации о модели
        if 'link' in model_info and model_info['link']:
            # Если ссылка есть, создаем кнопку "Скачать"
            link = model_info['link']
            markup = types.InlineKeyboardMarkup()
            button_download = types.InlineKeyboardButton('Скачать', url=link)
            markup.add(button_download)
        else:
            # Иначе создаем кнопку "Заказать модель"
            markup = types.InlineKeyboardMarkup()
            button_order = types.InlineKeyboardButton('Заказать модель', callback_data='order_model')
            markup.add(button_order)
        
        # Отправляем фотографию с подписью и соответствующей кнопкой
        try:
            with open(photo_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=name_ru, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"Не удалось отправить фотографию для {name_ru}.")
            print(f"Ошибка при отправке фото: {e}")



# Обработчик для команды '/horde'
@bot.message_handler(commands=['horde'])
def show_horde_menu(message):
    horde_menu = generate_horde_options_menu()
    bot.send_message(message.chat.id, "Выбрать каталог", reply_markup=horde_menu)

# Функция для генерации списка меню команды '/horde'
def generate_horde_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого члена Орды как отдельную кнопку в список
    for member in Ork_list:
        markup.add(types.KeyboardButton(member))
    # Добавляем кнопку "Назад в выбор фракции"
    markup.add(types.KeyboardButton('Назад в выбор фракции'))
    return markup

# Обработчик для кнопки "Назад в выбор фракции"
@bot.message_handler(func=lambda message: message.text == 'Назад в выбор фракции', content_types=['text'])
def back_to_faction_selection(message):
    bot.send_message(message.chat.id, "Выберите фракцию:", reply_markup=generate_wow_faction_menu())

# Обработчик для команды '/world_boss'
@bot.message_handler(commands=['world_boss'])
def show_world_boss_menu(message):
    world_boss_menu = generate_world_boss_options_menu()
    bot.send_message(message.chat.id, "Выбрать опцию мирового босса", reply_markup=world_boss_menu)

# Функция для генерации списка меню команды '/world_boss'
def generate_world_boss_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждую опцию мирового босса как отдельную кнопку в список
    for option in WorldBoss_list:
        markup.add(types.KeyboardButton(option))
    # Добавляем кнопку "Назад в выбор фракции"
    markup.add(types.KeyboardButton('Назад в выбор фракции'))
    return markup

# Обработчик для команды '/alliance'
@bot.message_handler(commands=['alliance'])
def show_alliance_menu(message):
    alliance_menu = generate_alliance_options_menu()
    bot.send_message(message.chat.id, "Выбрать каталог", reply_markup=alliance_menu)

# Функция для генерации списка меню команды '/alliance'
def generate_alliance_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого члена Альянса как отдельную кнопку в список
    for member in Alliance_list:
        markup.add(types.KeyboardButton(member))
    # Добавляем кнопку "Назад в выбор фракции"
    markup.add(types.KeyboardButton('Назад в выбор фракции'))
    return markup


# Обработчик для команды '/fighters'
@bot.message_handler(commands=['fighters'])
def show_fighters_menu(message):
    fighters_menu = generate_fighters_options_menu()
    bot.send_message(message.chat.id, "Choose a fighter:", reply_markup=fighters_menu)


# Функция для генерации списка меню команды '/fighters'
def generate_fighters_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого бойца как отдельную кнопку в список
    for fighter in fighters_list:
        markup.add(types.KeyboardButton(fighter))
    # Добавляем кнопку "back"
    markup.add(types.KeyboardButton('back'))
    return markup

# Функция для генерации списка меню команды '/Free'
def generate_free_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого бесплатного вариант как отдельную кнопку в список
    for free in free_list:
        markup.add(types.KeyboardButton(free))
    # Добавляем кнопку "back"
    markup.add(types.KeyboardButton('back'))
    return markup

# Обработчик для команды '/free'
@bot.message_handler(commands=['free'])
def show_free_menu(message):
    free_menu = generate_free_options_menu()
    bot.send_message(message.chat.id, "Выберите бесплатный вариант:", reply_markup=free_menu)

# Обработчик для кнопки "back" в меню бесплатных вариантов
@bot.message_handler(func=lambda message: message.text == 'back', content_types=['text'])
def back_to_model_options_menu_from_free(message):
    model_options_menu = generate_model_options_menu()
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=model_options_menu)


# Обработчик для команды '/mage'
# Функция для генерации списка меню команды '/Mage'
def generate_mage_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого ассассина как отдельную кнопку в список
    for mage in mage_list:
        markup.add(types.KeyboardButton(mage))
    # Добавляем кнопку "back"
    markup.add(types.KeyboardButton('back'))
    return markup

# Обработчик команды '/mage'
@bot.message_handler(commands=['mage'])
def show_mage_menu(message):
    mage_menu = generate_mage_options_menu()
    bot.send_message(message.chat.id, "Choose a mage:", reply_markup=mage_menu)

# Обработчик для кнопки "back" в меню бойцов '/Mage'
@bot.message_handler(func=lambda message: message.text == 'back', content_types=['text'])
def back_to_model_options_menu_from_mage(message):
    model_options_menu = generate_model_options_menu()
    bot.send_message(message.chat.id, "Main menu:", reply_markup=model_options_menu)


# Обработчик для команды '/marksman'
# Функция для генерации списка меню команды '/marksman'
def generate_marksman_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого ассассина как отдельную кнопку в список
    for marksman in marksman_list:
        markup.add(types.KeyboardButton(marksman))
    # Добавляем кнопку "back"
    markup.add(types.KeyboardButton('back'))
    return markup

# Обработчик команды '/marksman'
@bot.message_handler(commands=['marksman'])
def show_marksman_menu(message):
    marksman_menu = generate_marksman_options_menu()
    bot.send_message(message.chat.id, "Choose a marksman:", reply_markup=marksman_menu)

# Обработчик для кнопки "back" в меню бойцов '/marksman'
@bot.message_handler(func=lambda message: message.text == 'back', content_types=['text'])
def back_to_model_options_menu_from_marksman(message):
    model_options_menu = generate_model_options_menu()
    bot.send_message(message.chat.id, "Main menu:", reply_markup=model_options_menu)


# Обработчик для команды '/support'
# Функция для генерации списка меню команды '/support'
def generate_support_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого ассассина как отдельную кнопку в список
    for support in support_list:
        markup.add(types.KeyboardButton(support))
    # Добавляем кнопку "back"
    markup.add(types.KeyboardButton('back'))
    return markup

# Обработчик команды '/support'
@bot.message_handler(commands=['support'])
def show_support_menu(message):
    support_menu = generate_support_options_menu()
    bot.send_message(message.chat.id, "Choose a support:", reply_markup=support_menu)

# Обработчик для кнопки "back" в меню бойцов '/support'
@bot.message_handler(func=lambda message: message.text == 'back', content_types=['text'])
def back_to_model_options_menu_from_support(message):
    model_options_menu = generate_model_options_menu()
    bot.send_message(message.chat.id, "Main menu:", reply_markup=model_options_menu)


# Обработчик для команды '/tank'
# Функция для генерации списка меню команды '/tank'
def generate_tank_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    # Добавляем каждого ассассина как отдельную кнопку в список
    for tank in tank_list:
        markup.add(types.KeyboardButton(tank))
    # Добавляем кнопку "back"
    markup.add(types.KeyboardButton('back'))
    return markup

# Обработчик команды '/support'
@bot.message_handler(commands=['tank'])
def show_tank_menu(message):
    tank_menu = generate_tank_options_menu()
    bot.send_message(message.chat.id, "Choose a tank:", reply_markup=tank_menu)

# Обработчик для кнопки "back" в меню бойцов '/tank'
@bot.message_handler(func=lambda message: message.text == 'back', content_types=['text'])
def back_to_model_options_menu_from_tank(message):
    model_options_menu = generate_model_options_menu()
    bot.send_message(message.chat.id, "Main menu:", reply_markup=model_options_menu)
# Добавляем обработчики для остальных команд '/marksman', '/support', '/tank' аналогично

# Обработчик для кнопки "back" в меню бойцов '/fighters'
@bot.message_handler(func=lambda message: message.text == 'back', content_types=['text'])
def back_to_model_options_menu_from_fighters(message):
    model_options_menu = generate_model_options_menu()
    bot.send_message(message.chat.id, "Main menu:", reply_markup=model_options_menu)



# Обновленный список Human_list без цен
Human_list = {
    '/vorgen': {
        'name_ru': 'Пак_Ворген',
        'photo_path': 'C:/pythonProject1/wow/vorgen.jpg'
    },
    '/pandaren': {
        'name_ru': 'Пак_Пандарен',
        'photo_path': 'C:/pythonProject1/wow/pandaren.jpg'
    },
    '/night_elf': {
        'name_ru': 'Пак_Ночные Эльфы',
        'photo_path': 'C:/pythonProject1/wow/night_elf1.jpg'
    },
    '/night_elf2': {
        'name_ru': 'Пак_Ночные_Эльфы2',
        'photo_path': 'C:/pythonProject1/wow/night_elf2.jpg'
    },
    '/night_elf3': {
        'name_ru': 'Пак_Ночные_Эльфы3 (бесплатно)',
        'photo_path': 'C:/pythonProject1/wow/night_elf3.jpg',
        'link': 'https://disk.yandex.ru/d/jjw8cDbidC19Hg'  # Ссылка для бесплатной модели
    },
    '/dworf_gnom1': {
        'name_ru': 'Пак Дворф/Гном',
        'photo_path': 'C:/pythonProject1/wow/dworf_gnom1.jpg'
    },
    '/dworf_gnom2': {
        'name_ru': 'Пак Дворф/Гном2',
        'photo_path': 'C:/pythonProject1/wow/dworf_gnom2.jpg'
    },
    '/dworf_gnom3': {
        'name_ru': 'Пак Дворф/Гном3',
        'photo_path': 'C:/pythonProject1/wow/dworf_gnom3.jpg'
    },
    '/human': {
        'name_ru': 'Пак Человек',
        'photo_path': 'C:/pythonProject1/wow/human.jpg'
    },
    '/human2': {
        'name_ru': 'Пак Человек(2)',
        'photo_path': 'C:/pythonProject1/wow/human2.jpg'
    },
    '/human3': {
        'name_ru': 'Пак Человек(3)',
        'photo_path': 'C:/pythonProject1/wow/human3.jpg'
    }
}

# Получаем список команд из Human_list
human_commands = list(Human_list.keys())

# Обработчик для команд из Human_list
@bot.message_handler(commands=[cmd.strip('/') for cmd in human_commands])
def send_human_model(message):
    command = '/' + message.text.split()[0].strip('/')
    if command in Human_list:
        model_info = Human_list[command]
        name_ru = model_info['name_ru']
        photo_path = model_info['photo_path']
        
        # Проверяем, есть ли ссылка в информации о модели
        if 'link' in model_info and model_info['link']:
            # Если ссылка есть, создаем кнопку "Скачать"
            link = model_info['link']
            markup = types.InlineKeyboardMarkup()
            button_download = types.InlineKeyboardButton('Скачать', url=link)
            markup.add(button_download)
        else:
            # Иначе создаем кнопку "Заказать модель"
            markup = types.InlineKeyboardMarkup()
            button_order = types.InlineKeyboardButton('Заказать модель', callback_data='order_model')
            markup.add(button_order)
        
        # Отправляем фотографию с подписью и соответствующей кнопкой
        try:
            with open(photo_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=name_ru, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"Не удалось отправить фотографию для {name_ru}.")
            print(f"Ошибка при отправке фото: {e}")


# Обработчик команды /alliance_pack
@bot.message_handler(commands=['alliance_pack'])
def show_alliancepack(message):
    alliance_menu = "\n".join([f"{i+1}) {Human_list[command]['name_ru']} - {command}" for i, command in enumerate(Human_list)])
    bot.send_message(message.chat.id, alliance_menu)

# Обновленный список Alliance_flot без цен
Alliance_flot = {
    '/alliance_ship1': {
        'name_ru': 'Корабль 1',
        'video_path': 'C:/pythonProject1/wow/untitled.png0001-0220_1.mp4'
    },
    '/alliance_ship2': {
        'name_ru': 'Корабль 2',
        'video_path': 'C:/pythonProject1/wow/untitled.png0002-0220_1.mp4'
    },
    '/alliance_ship3': {
        'name_ru': 'Корабль 3 (бесплатно)',
        'video_path': 'C:/pythonProject1/wow/untitled.png0003-0220_1.mp4',
        'link': 'https://disk.yandex.ru/d/E4uNxAsw5nd1nA'  # Ссылка для бесплатной модели
    },
    '/alliance_ship4': {
        'name_ru': 'Корабль 4',
        'video_path': 'C:/pythonProject1/wow/untitled.png0004-0220_1.mp4'
    },
    '/alliance_ship5': {
        'name_ru': 'Корабль 5',
        'video_path': 'C:/pythonProject1/wow/untitled.png0005-0220_1.mp4'
    }
}

# Получаем список команд из Alliance_flot
alliance_flot_commands = list(Alliance_flot.keys())

# Обработчик для команд из Alliance_flot
@bot.message_handler(commands=[cmd.strip('/') for cmd in alliance_flot_commands])
def send_alliance_flot_video(message):
    command = '/' + message.text.split()[0].strip('/')
    if command in Alliance_flot:
        flot_info = Alliance_flot[command]
        name_ru = flot_info['name_ru']
        video_path = flot_info['video_path']
        
        # Проверяем, есть ли ссылка в информации о модели
        if 'link' in flot_info and flot_info['link']:
            # Если ссылка есть, создаем кнопку "Скачать"
            link = flot_info['link']
            markup = types.InlineKeyboardMarkup()
            button_download = types.InlineKeyboardButton('Скачать', url=link)
            markup.add(button_download)
        else:
            # Иначе создаем кнопку "Заказать модель"
            markup = types.InlineKeyboardMarkup()
            button_order = types.InlineKeyboardButton('Заказать модель', callback_data='order_model')
            markup.add(button_order)
        
        # Отправляем видео с подписью и соответствующей кнопкой
        try:
            with open(video_path, 'rb') as video:
                bot.send_video(message.chat.id, video, caption=name_ru, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"Не удалось отправить видео для {name_ru}.")
            print(f"Ошибка при отправке видео: {e}")

# Обработчик для команды /alliance_flot, который показывает список доступных кораблей
@bot.message_handler(commands=['alliance_flot'])
def show_alliance_flot(message):
    flot_menu = "\n".join([f"{i+1}) {Alliance_flot[command]['name_ru']} - {command}" for i, command in enumerate(Alliance_flot)])
    bot.send_message(message.chat.id, f"Список кораблей Альянса:\n{flot_menu}")






# Обновленный список лидеров Альянса без цен
Alliance_leader = {
    '/anduin': {
        'name_ru': 'Андуин (бесплатно)',
        'video_path': 'C:/pythonProject1/wow/anduin.mp4',
        'link': 'https://disk.yandex.ru/d/j0zFmKQ5taBgVQ'  # Ссылка для бесплатной модели
    },
    '/bronzoborod': {
        'name_ru': 'Магни Бронзобород',
        'video_path': 'C:/pythonProject1/wow/bronzoborod.mp4'
    },
    '/Djaina': {
        'name_ru': 'Джайна Праудмур',
        'video_path': 'C:/pythonProject1/wow/Djaina.mp4'
    },
    '/Tiranda': {
        'name_ru': 'Тиранда Шелест Ветра',
        'video_path': 'C:/pythonProject1/wow/Tiranda.mp4'
    },
    '/varian_rinn': {
        'name_ru': 'Вариан Ринн',
        'video_path': 'C:/pythonProject1/wow/varian_rinn.mp4'
    }
}

# Получаем список команд из Alliance_leader
alliance_commands = list(Alliance_leader.keys())

# Обработчик для команд из Alliance_leader
@bot.message_handler(commands=[cmd.strip('/') for cmd in alliance_commands])
def send_alliance_leader(message):
    command = '/' + message.text.split()[0].strip('/')
    if command in Alliance_leader:
        leader_info = Alliance_leader[command]
        name_ru = leader_info['name_ru']
        video_path = leader_info['video_path']
        
        # Проверяем, есть ли ссылка в информации о модели
        if 'link' in leader_info and leader_info['link']:
            # Если ссылка есть, создаем кнопку "Скачать"
            link = leader_info['link']
            markup = types.InlineKeyboardMarkup()
            button_download = types.InlineKeyboardButton('Скачать', url=link)
            markup.add(button_download)
        else:
            # Иначе создаем кнопку "Заказать модель"
            markup = types.InlineKeyboardMarkup()
            button_order = types.InlineKeyboardButton('Заказать модель', callback_data='order_model')
            markup.add(button_order)
        
        # Отправляем видео с подписью и соответствующей кнопкой
        try:
            with open(video_path, 'rb') as video:
                bot.send_video(message.chat.id, video, caption=name_ru, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"Не удалось отправить видео для {name_ru}.")
            print(f"Ошибка при отправке видео: {e}")

# Обработчик для команды /alliance_leader, который показывает список доступных лидеров
@bot.message_handler(commands=['alliance_leader'])
def show_alliance_leader(message):
    alliance_menu = "\n".join([f"{i+1}) {Alliance_leader[command]['name_ru']} - {command}" for i, command in enumerate(Alliance_leader)])
    bot.send_message(message.chat.id, f"Список лидеров Альянса:\n{alliance_menu}")



Horde_leader = {
    '/garrosh': {'name_ru': 'Гаррош (бесплатно)', 'video_path': 'C:/pythonProject1/wow/garrosh.mp4', 'price': 0, 'link': 'https://disk.yandex.ru/d/j0zFmKQ5taBgVQ'},
    '/saurfang': {'name_ru': 'Саурфанг', 'video_path': 'C:/pythonProject1/wow/saurfang.mp4', 'price': 290, 'link': 'https://disk.yandex.ru/d/7xvRGd2CGHjB1w'},
    '/silvana': {'name_ru': 'Сильванна', 'video_path': 'C:/pythonProject1/wow/silvanna.mp4', 'price': 290, 'link': 'https://disk.yandex.ru/d/j0rqyB60EQN0hw'},
    '/bain': {'name_ru': 'Бэйн Кровавое Копыто', 'video_path': 'C:/pythonProject1/wow/bain.mp4', 'price': 290, 'link': 'https://disk.yandex.ru/d/jU5kKw-Rr2-0Lg'},
    '/voldjin': {'name_ru': 'Волджин', 'video_path': 'C:/pythonProject1/wow/voldjin.mp4', 'price': 290, 'link': 'https://disk.yandex.ru/d/9NHjHXVWB9M0zQ'},
    '/garroshadskiy': {'name_ru': 'Гаррош Адский Крик', 'video_path': 'C:/pythonProject1/wow/garroshadskiy.mp4', 'price': 290, 'link': 'https://disk.yandex.ru/d/Q3zaWxXxpTYUWw'},
    '/ispolin': {'name_ru': 'Железный Исполин', 'video_path': 'C:/pythonProject1/wow/ispolin.mp4', 'price': 290, 'link': 'https://disk.yandex.ru/d/J37Qt31hGbzIIw'},
    '/chernoplass': {'name_ru': 'Черноплас', 'video_path': 'C:/pythonProject1/wow/chernoplass.mp4', 'price': 290, 'link': 'https://disk.yandex.ru/d/FNY3vzRWaU_bhg'}
}

@bot.message_handler(commands=['horde_leader'])
def show_horde_leader(message):
    horde_menu = "\n".join([f"{i+1}) {Horde_leader[command]['name_ru']} - {command}" for i, command in enumerate(Horde_leader)])
    bot.send_message(message.chat.id, horde_menu)

# Обновленный список лидеров Орды без цен
Horde_leader = {
    '/garrosh': {
        'name_ru': 'Гаррош (бесплатно)',
        'video_path': 'C:/pythonProject1/wow/garrosh.mp4',
        'link': 'https://disk.yandex.ru/d/j0zFmKQ5taBgVQ'  # Ссылка для бесплатной модели
    },
    '/saurfang': {
        'name_ru': 'Саурфанг',
        'video_path': 'C:/pythonProject1/wow/saurfang.mp4'
    },
    '/silvana': {
        'name_ru': 'Сильванна',
        'video_path': 'C:/pythonProject1/wow/silvanna.mp4'
    },
    '/bain': {
        'name_ru': 'Бэйн Кровавое Копыто',
        'video_path': 'C:/pythonProject1/wow/bain.mp4'
    },
    '/voldjin': {
        'name_ru': 'Волджин',
        'video_path': 'C:/pythonProject1/wow/voldjin.mp4'
    },
    '/garroshadskiy': {
        'name_ru': 'Гаррош Адский Крик',
        'video_path': 'C:/pythonProject1/wow/garroshadskiy.mp4'
    },
    '/ispolin': {
        'name_ru': 'Железный Исполин',
        'video_path': 'C:/pythonProject1/wow/ispolin.mp4'
    },
    '/chernoplass': {
        'name_ru': 'Черноплас',
        'video_path': 'C:/pythonProject1/wow/chernoplass.mp4'
    }
}

# Получаем список команд из Horde_leader
leader_commands = list(Horde_leader.keys())

# Обработчик для команд из Horde_leader
@bot.message_handler(commands=[cmd.strip('/') for cmd in leader_commands])
def send_horde_leader(message):
    command = '/' + message.text.split()[0].strip('/')
    if command in Horde_leader:
        leader_info = Horde_leader[command]
        name_ru = leader_info['name_ru']
        video_path = leader_info['video_path']
        
        # Проверяем, есть ли ссылка в информации о модели
        if 'link' in leader_info and leader_info['link']:
            # Если ссылка есть, создаем кнопку "Скачать"
            link = leader_info['link']
            markup = types.InlineKeyboardMarkup()
            button_download = types.InlineKeyboardButton('Скачать', url=link)
            markup.add(button_download)
        else:
            # Иначе создаем кнопку "Заказать модель"
            markup = types.InlineKeyboardMarkup()
            button_order = types.InlineKeyboardButton('Заказать модель', callback_data='order_model')
            markup.add(button_order)
        
        # Отправляем видео с подписью и соответствующей кнопкой
        try:
            with open(video_path, 'rb') as video:
                bot.send_video(message.chat.id, video, caption=name_ru, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"Не удалось отправить видео для {name_ru}.")
            print(f"Ошибка при отправке видео: {e}")


# Обновленный список моделей для Орды
Horde_list = {
    '/horde_tauren': {'name_ru': 'Пак_Таурен', 'photo_path': 'C:/pythonProject1/wow/tauren_horde1.jpg'},
    '/horde_troll': {'name_ru': 'Пак_Тролль', 'photo_path': 'C:/pythonProject1/wow/troll_horde1.jpg'},
    '/horde_troll2': {'name_ru': 'Пак_Тролль2', 'photo_path': 'C:/pythonProject1/wow/troll_horde2.jpg'},
    '/horde_undead': {'name_ru': 'Пак_Нежить', 'photo_path': 'C:/pythonProject1/wow/undead_horde1.jpg'},
    '/horde_undead2': {'name_ru': 'Пак2_Нежить', 'photo_path': 'C:/pythonProject1/wow/undead_horde2.jpg'},
    '/horde_sukub': {'name_ru': 'Пак_Суккуб', 'photo_path': 'C:/pythonProject1/wow/suk_horde.jpg'},
    '/horde_butcher': {'name_ru': 'Нежить-мясник', 'photo_path': 'C:/pythonProject1/wow/horde_butcher.jpg'},
    '/horde_elf': {
        'name_ru': 'Пак_Эльф (Бесплатно)',
        'photo_path': 'C:/pythonProject1/wow/elf_horde1.jpg',
        'link': 'https://disk.yandex.ru/d/f4mVKO9n5eKqyg'  # Добавляем ссылку для бесплатной модели
    },
    '/horde_goblin': {'name_ru': 'Пак_Гоблин', 'photo_path': 'C:/pythonProject1/wow/goblin_horde1.jpg'},
    '/horde_ork': {'name_ru': 'Пак_Орк', 'photo_path': 'C:/pythonProject1/wow/ork_horde1.jpg'},
    '/horde_ork2': {'name_ru': 'Пак2_Орк', 'photo_path': 'C:/pythonProject1/wow/horde_ork2.jpg'},
    '/horde_ork3': {'name_ru': 'Пак3_Орк', 'photo_path': 'C:/pythonProject1/wow/ork_horde3.jpg'},
    '/horde_ork4': {'name_ru': 'Пак4_Орк', 'photo_path': 'C:/pythonProject1/wow/ork_horde4.jpg'},
    '/horde_ork5': {'name_ru': 'Пак5_Орк', 'photo_path': 'C:/pythonProject1/wow/ork_horde5.jpg'},
    '/horde_ork6': {'name_ru': 'Пак6_Орк', 'photo_path': 'C:/pythonProject1/wow/ork_horde6.jpg'}
}

# Получаем список команд из Horde_list
horde_commands = list(Horde_list.keys())

# Обработчик для команд из Horde_list
@bot.message_handler(commands=[cmd.strip('/') for cmd in horde_commands])
def send_horde_model(message):
    command = '/' + message.text.split()[0].strip('/')
    if command in Horde_list:
        model_info = Horde_list[command]
        name_ru = model_info['name_ru']
        photo_path = model_info['photo_path']
        
        # Проверяем, есть ли ссылка в информации о модели
        if 'link' in model_info and model_info['link']:
            # Если ссылка есть, создаем кнопку "Скачать"
            link = model_info['link']
            markup = types.InlineKeyboardMarkup()
            button_download = types.InlineKeyboardButton('Скачать', url=link)
            markup.add(button_download)
        else:
            # Иначе создаем кнопку "Заказать модель"
            markup = types.InlineKeyboardMarkup()
            button_order = types.InlineKeyboardButton('Заказать модель', callback_data='order_model')
            markup.add(button_order)
        
        # Отправляем фотографию с подписью и соответствующей кнопкой
        try:
            with open(photo_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=name_ru, reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"Не удалось отправить фотографию для {name_ru}.")
            print(f"Ошибка при отправке фото: {e}")


@bot.message_handler(commands=['horde_pack'])
def show_hordepack(message):
    horde_menu = "\n".join([f"{i+1}) {Horde_list[command]['name_ru']} - {command}" for i, command in enumerate(Horde_list)])
    bot.send_message(message.chat.id, horde_menu)





Floryn_list = {
    '/floryn_basic': {'video_path': 'C:/pythonProject1/Marksman/Floryn_Basic.mp4', 'price': 230, 'link': 'Скачивание запрещено/307'},
    '/floryn_elite': {'video_path': 'C:/pythonProject1/Marksman/Floryn_Elite.mp4', 'price': 230, 'link': 'Скачивание запрещено/308'},
    '/floryn_characters': {'video_path': 'C:/pythonProject1/Marksman/Floryn_Characters.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['floryn'])
def show_floryn(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Floryn_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Floryn_list.keys())
def send_floryn_video(message):
    command = message.text.strip().lower()
    model_info = Floryn_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Kaja_list = {
    '/kaja_base': {'video_path': 'C:/pythonProject1/Marksman/Kaja_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/304'},
    '/kaja_elite': {'video_path': 'C:/pythonProject1/Marksman/Kaja_elite.mp4', 'price': 230, 'link': 'Скачивание запрещено/305'},
    '/kaja_epic': {'video_path': 'C:/pythonProject1/Marksman/Kaja_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/kaja_s20': {'video_path': 'C:/pythonProject1/Marksman/Kaja_s20.mp4', 'price': 200, 'link': 'Скачивание запрещено/306'},
    '/kaja_star': {'video_path': 'C:/pythonProject1/Marksman/Kaja_star.mp4', 'price': None, 'link': '@dikayl'},
    '/kaja_epic2': {'video_path': 'C:/pythonProject1/Marksman/kaja_epic2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['kaja'])
def show_kaja(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Kaja_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Kaja_list.keys())
def send_kaja_video(message):
    command = message.text.strip().lower()
    model_info = Kaja_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Estes_list = {
    '/estes_s8': {'video_path': 'C:/pythonProject1/Marksman/Estes_s8.mp4', 'price': 190, 'link': 'Скачивание запрещено/294'},
    '/estes_special': {'video_path': 'C:/pythonProject1/Marksman/Estes_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/295'},
    '/estes_basic': {'video_path': 'C:/pythonProject1/Marksman/Estes_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/296'},
    '/estes_dragon': {'video_path': 'C:/pythonProject1/Marksman/Estes_dragon.mp4', 'price': None, 'link': '@dikayl'},
    '/estes_epic': {'video_path': 'C:/pythonProject1/Marksman/Estes_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/297'},
    '/estes_epic2': {'video_path': 'C:/pythonProject1/Marksman/Estes_epic2.mp4', 'price': None, 'link': '@dikayl'},
    '/estes_champion': {'video_path': 'C:/pythonProject1/Marksman/estes_champion.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['estes'])
def show_estes(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Estes_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Estes_list.keys())
def send_estes_video(message):
    command = message.text.strip().lower()
    model_info = Estes_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Diggie_list = {
    '/diggie_basic': {'video_path': 'C:/pythonProject1/Marksman/Diggie_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/284'},
    '/diggie_elite': {'video_path': 'C:/pythonProject1/Marksman/Diggie_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/285'},
    '/diggie_epic': {'video_path': 'C:/pythonProject1/Marksman/Diggie_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/diggie_special': {'video_path': 'C:/pythonProject1/Marksman/Diggie_special.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['diggie'])
def show_diggie(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Diggie_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Diggie_list.keys())
def send_diggie_video(message):
    command = message.text.strip().lower()
    model_info = Diggie_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Angela_list = {
    '/angela_aspirants': {'video_path': 'C:/pythonProject1/Marksman/Angela_aspirants.mp4', 'price': 350, 'link': 'Скачивание запрещено/298'},
    '/angela_basic': {'video_path': 'C:/pythonProject1/Marksman/Angela_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/299'},
    '/angela_collector': {'video_path': 'C:/pythonProject1/Marksman/Angela_collector.mp4', 'price': 230, 'link': 'Скачивание запрещено/300'},
    '/angela_halloween': {'video_path': 'C:/pythonProject1/Marksman/Angela_halloween.mp4', 'price': None, 'link': '@dikayl'},
    '/angela_sand': {'video_path': 'C:/pythonProject1/Marksman/Angela_sand.mp4', 'price': None, 'link': '@dikayl'},
    '/angela_star': {'video_path': 'C:/pythonProject1/Marksman/Angela_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/301'},
    '/angela_summer': {'video_path': 'C:/pythonProject1/Marksman/Angela_summer.mp4', 'price': 210, 'link': 'Скачивание запрещено/302'},
    '/angela_venom': {'video_path': 'C:/pythonProject1/Marksman/Angela_venom.mp4', 'price': 210, 'link': 'Скачивание запрещено/303'},
    '/angela_star2': {'video_path': 'C:/pythonProject1/Marksman/angela_star2.mp4', 'price': 210, 'link': 'Скачивание запрещено/303'},
}


@bot.message_handler(commands=['angela'])
def show_angela(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Angela_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Angela_list.keys())
def send_angela_video(message):
    command = message.text.strip().lower()
    model_info = Angela_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Rafaela_list = {
    '/rafaela_saber': {'video_path': 'C:/pythonProject1/Marksman/Rafaela_saber.mp4', 'price': 190, 'link': 'Скачивание запрещено/292'},
    '/rafaela_christmas': {'video_path': 'C:/pythonProject1/Marksman/Rafaela_christmas.mp4', 'price': 210, 'link': 'Скачивание запрещено/287'},
    '/rafaela_elite': {'video_path': 'C:/pythonProject1/Marksman/Rafaela_elite.mp4', 'price': 180, 'link': 'Скачивание запрещено/288'},
    '/rafaela_elite2': {'video_path': 'C:/pythonProject1/Marksman/Rafaela_elite2.mp4', 'price': 190, 'link': 'Скачивание запрещено/289'},
    '/rafaela_epic': {'video_path': 'C:/pythonProject1/Marksman/Rafaela_epic.mp4', 'price': 190, 'link': 'Скачивание запрещено/290'},
    '/rafaela_s18': {'video_path': 'C:/pythonProject1/Marksman/Rafaela_s18.mp4', 'price': 230, 'link': 'Скачивание запрещено/291'},
    '/rafaela_as': {'video_path': 'C:/pythonProject1/Marksman/Rafaela_as.mp4', 'price': None, 'link': '@dikayl'},
    '/rafaela_basic': {'video_path': 'C:/pythonProject1/Marksman/Rafaela_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/286'},
}


@bot.message_handler(commands=['rafaela'])
def show_rafaela(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Rafaela_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Rafaela_list.keys())
def send_rafaela_video(message):
    command = message.text.strip().lower()
    model_info = Rafaela_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Minotaur_list = {
    '/minotaur_base': {'video_path': 'C:/pythonProject1/Marksman/Minotaur_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/346'},
    '/minotaur_elite': {'video_path': 'C:/pythonProject1/Marksman/Minotaur_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/minotaur_elite2': {'video_path': 'C:/pythonProject1/Marksman/Minotaur_elite2.mp4', 'price': None, 'link': '@dikayl'},
    '/minotaur_s4': {'video_path': 'C:/pythonProject1/Marksman/Minotaur_s4.mp4', 'price': 200, 'link': 'Скачивание запрещено/348'},
    '/minotaur_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Minotaur_zodiac.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['minotaur'])
def show_minotaur(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Minotaur_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Minotaur_list.keys())
def send_minotaur_video(message):
    command = message.text.strip().lower()
    model_info = Minotaur_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Lolita_list = {
    '/lolita_base': {'video_path': 'C:/pythonProject1/Marksman/Lolita_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/343'},
    '/lolita_elite': {'video_path': 'C:/pythonProject1/Marksman/Lolita_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/lolita_halloween': {'video_path': 'C:/pythonProject1/Marksman/Lolita_halloween.mp4', 'price': 190, 'link': 'Скачивание запрещено/344'},
    '/lolita_lunar': {'video_path': 'C:/pythonProject1/Marksman/Lolita_lunar.mp4', 'price': 250, 'link': 'Скачивание запрещено/345'},
    '/lolita_special': {'video_path': 'C:/pythonProject1/Marksman/lolita_special.mp4', 'price': 250, 'link': 'Скачивание запрещено/345'},
}


@bot.message_handler(commands=['lolita'])
def show_lolita(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Lolita_list)])
    bot.send_message(message.chat.id, fighters_menu)


@bot.message_handler(func=lambda message: message.text.lower() in Lolita_list.keys())
def send_lolita_video(message):
    command = message.text.strip().lower()
    model_info = Lolita_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


# Define the callback handler for the "Buy" button
@bot.callback_query_handler(func=lambda call: call.data.startswith("Buy_lolita"))
def Buy_lolita_callback(call):
    user_id = call.from_user.id
    user_data = db.get_user_data(user_id)
    if user_data is None:
        bot.send_message(user_id, "Write me bro -> @dikayl.")
        return

    model_name = call.data[11:]  # Remove the 'Buy_lolita' prefix from callback_data
    model_info = Lolita_list.get(f'/{model_name}')
    if model_info is None:
        bot.send_message(user_id, "Write me bro -> @dikayl")
        return

    #bot.send_message(user_id, "write me bro @dikayl")

Khufra_list = {
    '/khufra_basic': {'video_path': 'C:/pythonProject1/Marksman/Khufra_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/341'},
    '/khufra_elite': {'video_path': 'C:/pythonProject1/Marksman/Khufra_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/342'},
    '/khufra_collector': {'video_path': 'C:/pythonProject1/Marksman/Khufra_collector.mp4', 'price': None, 'link': '@dikayl'},
    '/khufra_star': {'video_path': 'C:/pythonProject1/Marksman/Khufra_star.mp4', 'price': None, 'link': '@dikayl'},
    '/khufra_valentine': {'video_path': 'C:/pythonProject1/Marksman/Khufra_valentine.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['khufra'])
def show_khufra(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Khufra_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Khufra_list.keys())
def send_khufra_video(message):
    command = message.text.strip().lower()
    model_info = Khufra_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Johnson_list = {
    '/johnson_base': {'video_path': 'C:/pythonProject1/Marksman/Johnson_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/338'},
    '/johnson_elite': {'video_path': 'C:/pythonProject1/Marksman/Johnson_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/johnson_epic': {'video_path': 'C:/pythonProject1/Marksman/Johnson_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/339'},
    '/johnson_saber': {'video_path': 'C:/pythonProject1/Marksman/Johnson_saber.mp4', 'price': 210, 'link': 'Скачивание запрещено/340'},
    '/johnson_transformer': {'video_path': 'C:/pythonProject1/Marksman/Johnson_transformer.mp4', 'price': None, 'link': '@dikayl'},
    '/johnson_special': {'video_path': 'C:/pythonProject1/Marksman/Johnson_special.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['johnson'])
def show_johnson(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Johnson_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Johnson_list.keys())
def send_johnson_video(message):
    command = message.text.strip().lower()
    model_info = Johnson_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Hylos_list = {
    '/hylos_base': {'video_path': 'C:/pythonProject1/Marksman/Hylos_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/334'},
    '/hylos_special': {'video_path': 'C:/pythonProject1/Marksman/Hylos_special.mp4', 'price': 200, 'link': 'Скачивание запрещено/335'},
    '/hylos_s13': {'video_path': 'C:/pythonProject1/Marksman/Hylos_s13.mp4', 'price': 180, 'link': 'Скачивание запрещено/336'},
    '/hylos_epic': {'video_path': 'C:/pythonProject1/Marksman/Hylos_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/hylos_elite': {'video_path': 'C:/pythonProject1/Marksman/Hylos_elite.mp4', 'price': 200, 'link': 'Скачивание запрещено/337'},
    '/hylos_epic2': {'video_path': 'C:/pythonProject1/Marksman/hylos_epic2.mp4', 'price': 200, 'link': 'Скачивание запрещено/337'},
}


@bot.message_handler(commands=['hylos'])
def show_hylos(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Hylos_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Hylos_list.keys())
def send_hylos_video(message):
    command = message.text.strip().lower()
    model_info = Hylos_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Grock_list = {
    '/grock_base': {'video_path': 'C:/pythonProject1/Marksman/Grock_base.mp4', 'price': None, 'link': '@dikayl'},
    '/grock_elite': {'video_path': 'C:/pythonProject1/Marksman/Grock_elite.mp4', 'price': 180, 'link': 'Скачивание запрещено/331'},
    '/grock_epic': {'video_path': 'C:/pythonProject1/Marksman/Grock_epic.mp4', 'price': 180, 'link': 'Скачивание запрещено/332'},
    '/grock_venom': {'video_path': 'C:/pythonProject1/Marksman/Grock_venom.mp4', 'price': 250, 'link': 'Скачивание запрещено/333'},
    '/grock_star': {'video_path': 'C:/pythonProject1/Marksman/Grock_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['grock'])
def show_grock(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Grock_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Grock_list.keys())
def send_grock_video(message):
    command = message.text.strip().lower()
    model_info = Grock_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Gloo_list = {
    '/gloo_base': {'video_path': 'C:/pythonProject1/Marksman/Gloo_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/330'},
    '/gloo_special': {'video_path': 'C:/pythonProject1/Marksman/Gloo_special.mp4', 'price': None, 'link': '@dikayl'},
}

@bot.message_handler(commands=['gloo'])
def show_gloo(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Gloo_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Gloo_list.keys())
def send_gloo_video(message):
    command = message.text.strip().lower()
    model_info = Gloo_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Uranus_list = {
    '/uranus_base': {'video_path': 'C:/pythonProject1/Marksman/Uranus_base.mp4', 'price': 200, 'link': 'Скачивание запрещено/349'},
    '/uranus_epic': {'video_path': 'C:/pythonProject1/Marksman/Uranus_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/350'},
    '/uranus_special2': {'video_path': 'C:/pythonProject1/Marksman/Uranus_special2.mp4', 'price': 210, 'link': 'Скачивание запрещено/351'},
    '/uranus_special': {'video_path': 'C:/pythonProject1/Marksman/Uranus_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/352'},
    '/uranus_s25': {'video_path': 'C:/pythonProject1/Marksman/Uranus_s25.mp4', 'price': 210, 'link': 'Скачивание запрещено/353'},
    '/uranus_epic2': {'video_path': 'C:/pythonProject1/Marksman/Uranus_epic2.mp4', 'price': 210, 'link': 'Скачивание запрещено/354'},
}


@bot.message_handler(commands=['uranus'])
def show_uranus(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Uranus_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Uranus_list.keys())
def send_uranus_video(message):
    command = message.text.strip().lower()
    model_info = Uranus_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Gatotkaca_list = {
    '/gatotkaca_base': {'video_path': 'C:/pythonProject1/Marksman/Gatotkaca_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/327'},
    '/gatotkaca_elite': {'video_path': 'C:/pythonProject1/Marksman/Gatotkaca_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/328'},
    '/gatotkaca_epic': {'video_path': 'C:/pythonProject1/Marksman/Gatotkaca_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/329'},
}

@bot.message_handler(commands=['gatotkaca'])
def show_gatotkaca(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Gatotkaca_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Gatotkaca_list.keys())
def send_gatotkaca_video(message):
    command = message.text.strip().lower()
    model_info = Gatotkaca_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Fredrinn_list = {
    '/fredrinn_base': {'video_path': 'C:/pythonProject1/Marksman/Fredrinn_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/324'},
    '/fredrinn_base2': {'video_path': 'C:/pythonProject1/Marksman/Fredrinn_base2.mp4', 'price': 210, 'link': 'Скачивание запрещено/325'},
    '/fredrinn_elite': {'video_path': 'C:/pythonProject1/Marksman/Fredrinn_elite.mp4', 'price': 200, 'link': 'Скачивание запрещено/326'},
    '/fredrinn_neobear': {'video_path': 'C:/pythonProject1/Marksman/fredrinn_neobear.mp4', 'price': 200, 'link': 'Скачивание запрещено/326'},
}

@bot.message_handler(commands=['fredrinn'])
def show_fredrinn(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Fredrinn_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Fredrinn_list.keys())
def send_fredrinn_video(message):
    command = message.text.strip().lower()
    model_info = Fredrinn_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Franco_list = {
    '/franco_base': {'video_path': 'C:/pythonProject1/Marksman/Franco_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/321'},
    '/franco_s9': {'video_path': 'C:/pythonProject1/Marksman/Franco_s9.mp4', 'price': 200, 'link': 'Скачивание запрещено/322'},
    '/franco_blazing': {'video_path': 'C:/pythonProject1/Marksman/Franco_blazing.mp4', 'price': None, 'link': '@dikayl'},
    '/franco_epic': {'video_path': 'C:/pythonProject1/Marksman/Franco_epic.mp4', 'price': 250, 'link': 'Скачивание запрещено/323'},
    '/franco_halloween': {'video_path': 'C:/pythonProject1/Marksman/Franco_halloween.mp4', 'price': None, 'link': '@dikayl'},
    '/franco_legend': {'video_path': 'C:/pythonProject1/Marksman/Franco_legend.mp4', 'price': None, 'link': '@dikayl'},
    '/franco_special': {'video_path': 'C:/pythonProject1/Marksman/Franco_special.mp4', 'price': None, 'link': '@dikayl'},
    '/franco_star': {'video_path': 'C:/pythonProject1/Marksman/Franco_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['franco'])
def show_franco(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Franco_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Franco_list.keys())
def send_franco_video(message):
    command = message.text.strip().lower()
    model_info = Franco_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Edith_list = {
    '/edith_base': {'video_path': 'C:/pythonProject1/Marksman/Edith_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/319'},
    '/edith_star': {'video_path': 'C:/pythonProject1/Marksman/Edith_star.mp4', 'price': 180, 'link': 'Скачивание запрещено/320'},
}


@bot.message_handler(commands=['edith'])
def show_edith(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Edith_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Edith_list.keys())
def send_edith_video(message):
    command = message.text.strip().lower()
    model_info = Edith_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Carmilla_list = {
    '/carmilla_basic': {'video_path': 'C:/pythonProject1/Marksman/Carmilla_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/308'},
    '/carmilla_elite': {'video_path': 'C:/pythonProject1/Marksman/Carmilla_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/309'},
    '/carmilla_valentine': {'video_path': 'C:/pythonProject1/Marksman/Carmilla_valentine.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['carmilla'])
def show_carmilla(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Carmilla_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Carmilla_list.keys())
def send_carmilla_video(message):
    command = message.text.strip().lower()
    model_info = Carmilla_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Belerick_list = {
    '/belerick_base': {'video_path': 'C:/pythonProject1/Marksman/Belerick_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/315'},
    '/belerick_elite': {'video_path': 'C:/pythonProject1/Marksman/Belerick_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/316'},
    '/belerick_special': {'video_path': 'C:/pythonProject1/Marksman/Belerick_special.mp4', 'price': 180, 'link': 'Скачивание запрещено/317'},
    '/belerick_special2': {'video_path': 'C:/pythonProject1/Marksman/Belerick_special2.mp4', 'price': 200, 'link': 'Скачивание запрещено/318'},
}


@bot.message_handler(commands=['belerick'])
def show_belerick(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Belerick_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Belerick_list.keys())
def send_belerick_video(message):
    command = message.text.strip().lower()
    model_info = Belerick_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Baxia_list = {
    '/baxia_basic': {'video_path': 'C:/pythonProject1/Marksman/Baxia_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/313'},
    '/baxia_elite': {'video_path': 'C:/pythonProject1/Marksman/Baxia_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/baxia_special': {'video_path': 'C:/pythonProject1/Marksman/Baxia_special.mp4', 'price': 200, 'link': 'Скачивание запрещено/314'},
}


@bot.message_handler(commands=['baxia'])
def show_baxia(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Baxia_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Baxia_list.keys())
def send_baxia_video(message):
    command = message.text.strip().lower()
    model_info = Baxia_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Barats_list = {
    '/barats_base': {'video_path': 'C:/pythonProject1/Marksman/Barats_base.mp4', 'price': None, 'link': '@dikayl'},
    '/barats_elite': {'video_path': 'C:/pythonProject1/Marksman/Barats_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/436'},
    '/barats_s26': {'video_path': 'C:/pythonProject1/Marksman/Barats_s26.mp4', 'price': None, 'link': '@dikayl'},
    '/barats_halloween': {'video_path': 'C:/pythonProject1/Marksman/Barats_halloween.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['barats'])
def show_barats(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Barats_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Barats_list.keys())
def send_barats_video(message):
    command = message.text.strip().lower()
    model_info = Barats_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Atlas_list = {
    '/atlas_base': {'video_path': 'C:/pythonProject1/Marksman/Atlas_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/310'},
    '/atlas_elite': {'video_path': 'C:/pythonProject1/Marksman/Atlas_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/311'},
    '/atlas_msc': {'video_path': 'C:/pythonProject1/Marksman/Atlas_msc.mp4', 'price': 210, 'link': 'Скачивание запрещено/312'},
    '/atlas_star': {'video_path': 'C:/pythonProject1/Marksman/Atlas_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['atlas'])
def show_atlas(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Atlas_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Atlas_list.keys())
def send_atlas_video(message):
    command = message.text.strip().lower()
    model_info = Atlas_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Roger_list = {
    '/roger_base': {'video_path': 'C:/pythonProject1/Marksman/Roger_base.mp4', 'price': None, 'link': '@dikayl'},
    '/roger_base2': {'video_path': 'C:/pythonProject1/Marksman/Roger_base2.mp4', 'price': None, 'link': '@dikayl'},
    '/roger_epic': {'video_path': 'C:/pythonProject1/Marksman/Roger_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/roger_epic2': {'video_path': 'C:/pythonProject1/Marksman/Roger_epic2.mp4', 'price': None, 'link': '@dikayl'},
    '/roger_epic3': {'video_path': 'C:/pythonProject1/Marksman/Roger_epic3.mp4', 'price': None, 'link': '@dikayl'},
    '/roger_m3': {'video_path': 'C:/pythonProject1/Marksman/Roger_m3.mp4', 'price': None, 'link': '@dikayl'},
    '/roger_transformer': {'video_path': 'C:/pythonProject1/Marksman/Roger_transformer.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['roger'])
def show_roger(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Roger_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Roger_list.keys())
def send_roger_video(message):
    command = message.text.strip().lower()
    model_info = Roger_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Lesley_list = {
    '/lesley_base': {'video_path': 'C:/pythonProject1/Marksman/Lesley_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/429'},
    '/lesley_base2': {'video_path': 'C:/pythonProject1/Marksman/Lesley_base2.mp4', 'price': 230, 'link': 'Скачивание запрещено/430'},
    '/lesley_collector': {'video_path': 'C:/pythonProject1/Marksman/Lesley_collector.mp4', 'price': None, 'link': '@dikayl'},
    '/lesley_elite': {'video_path': 'C:/pythonProject1/Marksman/Lesley_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/lesley_epic': {'video_path': 'C:/pythonProject1/Marksman/Lesley_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/431'},
    '/lesley_legend': {'video_path': 'C:/pythonProject1/Marksman/Lesley_legend.mp4', 'price': None, 'link': '@dikayl'},
    '/lesley_star': {'video_path': 'C:/pythonProject1/Marksman/Lesley_star.mp4', 'price': None, 'link': '@dikayl'},
    '/lesley_star2': {'video_path': 'C:/pythonProject1/Marksman/Lesley_star2.mp4', 'price': 230, 'link': 'Скачивание запрещено/432'},
    '/lesley_special_1': {'video_path': 'C:/pythonProject1/Marksman/lesley_special_1.mp4', 'price': None, 'link': '@dikayl'},
    '/lesley_special_2': {'video_path': 'C:/pythonProject1/Marksman/lesley_special_2', 'price': 290, 'link': 'Скачивание запрещено/433'},
    '/lesley_valentine_1': {'video_path': 'C:/pythonProject1/Marksman/lesley_valentine_1.mp4', 'price': None, 'link': '@dikayl'},
    '/lesley_valentine_2': {'video_path': 'C:/pythonProject1/Marksman/lesley_valentine_2', 'price': 290, 'link': 'Скачивание запрещено/434'},
}


@bot.message_handler(commands=['lesley'])
def show_lesley(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Lesley_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Lesley_list.keys())
def send_lesley_video(message):
    command = message.text.strip().lower()
    model_info = Lesley_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Wanwan_list = {
    '/wanwan_base': {'video_path': 'C:/pythonProject1/Marksman/Wanwan_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/424'},
    '/wanwan_collector': {'video_path': 'C:/pythonProject1/Marksman/Wanwan_collector.mp4', 'price': 230, 'link': 'Скачивание запрещено/425'},
    '/wanwan_elite': {'video_path': 'C:/pythonProject1/Marksman/Wanwan_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/wanwan_mdt': {'video_path': 'C:/pythonProject1/Marksman/Wanwan_mdt.mp4', 'price': 190, 'link': 'Скачивание запрещено/426'},
    '/wanwan_star': {'video_path': 'C:/pythonProject1/Marksman/Wanwan_star.mp4', 'price': None, 'link': '@dikayl'},
    '/wanwan_m_world_1': {'video_path': 'C:/pythonProject1/Marksman/wanwan_m-world_1.mp4', 'price': None, 'link': '@dikayl'},
    '/wanwan_m_world_2': {'video_path': 'C:/pythonProject1/Marksman/wanwan_m-world_2.mp4', 'price': 290, 'link': 'Скачивание запрещено/427'},
    '/wanwan_11_11': {'video_path': 'C:/pythonProject1/Marksman/wanwan_11_11.mp4', 'price': 290, 'link': 'Скачивание запрещено/427'},
}


@bot.message_handler(commands=['wanwan'])
def show_wanwan(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Wanwan_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Wanwan_list.keys())
def send_wanwan_video(message):
    command = message.text.strip().lower()
    model_info = Wanwan_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Popol_list = {
    '/popol_base_1': {'video_path': 'C:/pythonProject1/Marksman/popol_base_1.mp4', 'price': None, 'link': '@dikayl'},
    '/popol_base_2': {'video_path': 'C:/pythonProject1/Marksman/popol_base_2.mp4', 'price': 370, 'link': 'Скачивание запрещено/407'},
    '/popol_elite': {'video_path': 'C:/pythonProject1/Marksman/popol_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/popol_star': {'video_path': 'C:/pythonProject1/Marksman/popol_star.mp4', 'price': None, 'link': '@dikayl'},
    '/popol_transformer': {'video_path': 'C:/pythonProject1/Marksman/popol_transformer.mp4', 'price': None, 'link': '@dikayl'},
}

@bot.message_handler(commands=['popol'])
def show_popol(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Popol_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Popol_list.keys())
def send_popol_video(message):
    command = message.text.strip().lower()
    model_info = Popol_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Natan_list = {
    '/natan_base': {'video_path': 'C:/pythonProject1/Marksman/Natan_base.mp4', 'price': 210, 'link': 'Скачивание запрещено/422'},
    '/natan_collector': {'video_path': 'C:/pythonProject1/Marksman/Natan_collector.mp4', 'price': None, 'link': '@dikayl'},
    '/natan_elite': {'video_path': 'C:/pythonProject1/Marksman/Natan_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/423'},
    '/natan_star': {'video_path': 'C:/pythonProject1/Marksman/Natan_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['natan'])
def show_natan(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Natan_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Natan_list.keys())
def send_natan_video(message):
    command = message.text.strip().lower()
    model_info = Natan_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Moskov_list = {
    '/moskov_base': {'video_path': 'C:/pythonProject1/Marksman/Moskov_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/415'},
    '/moskov_elite': {'video_path': 'C:/pythonProject1/Marksman/Moskov_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/416'},
    '/moskov_epic': {'video_path': 'C:/pythonProject1/Marksman/Moskov_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/moskov_epic2': {'video_path': 'C:/pythonProject1/Marksman/Moskov_epic2.mp4', 'price': 230, 'link': 'Скачивание запрещено/417'},
    '/moskov_abbys': {'video_path': 'C:/pythonProject1/Marksman/Moskov_abbys.mp4', 'price': 210, 'link': 'Скачивание запрещено/418'},
    '/moskov_star2': {'video_path': 'C:/pythonProject1/Marksman/Moskov_star2.mp4', 'price': 210, 'link': 'Скачивание запрещено/419'},
    '/moskov_star': {'video_path': 'C:/pythonProject1/Marksman/Moskov_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/420'},
    '/moskov_special': {'video_path': 'C:/pythonProject1/Marksman/Moskov_special.mp4', 'price': None, 'link': '@dikayl'},
    '/moskov_s7': {'video_path': 'C:/pythonProject1/Marksman/Moskov_s7.mp4', 'price': 210, 'link': 'Скачивание запрещено/421'},
}


@bot.message_handler(commands=['moskov'])
def show_moskov(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Moskov_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Moskov_list.keys())
def send_moskov_video(message):
    command = message.text.strip().lower()
    model_info = Moskov_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Miya_list = {
    '/miya_base': {'video_path': 'C:/pythonProject1/Marksman/Miya_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/409'},
    '/miya_christmass': {'video_path': 'C:/pythonProject1/Marksman/Miya_christmass.mp4', 'price': None, 'link': '@dikayl'},
    '/miya_anniversary': {'video_path': 'C:/pythonProject1/Marksman/Miya_anniversary.mp4', 'price': 350, 'link': 'Скачивание запрещено/410'},
    '/miya_valentine': {'video_path': 'C:/pythonProject1/Marksman/Miya_valentine.mp4', 'price': 250, 'link': 'Скачивание запрещено/411'},
    '/miya_star': {'video_path': 'C:/pythonProject1/Marksman/Miya_star.mp4', 'price': None, 'link': '@dikayl'},
    '/miya_special': {'video_path': 'C:/pythonProject1/Marksman/Miya_special.mp4', 'price': None, 'link': '@dikayl'},
    '/miya_legend': {'video_path': 'C:/pythonProject1/Marksman/Miya_legend.mp4', 'price': 190, 'link': 'Скачивание запрещено/412'},
    '/miya_elite': {'video_path': 'C:/pythonProject1/Marksman/Miya_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/413'},
    '/miya_collector': {'video_path': 'C:/pythonProject1/Marksman/Miya_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/414'},
    '/miya_atomic': {'video_path': 'C:/pythonProject1/Marksman/atomic_1.mp4', 'price': None, 'link': '@dikayl'},
    '/miya_atomic2': {'video_path': 'C:/pythonProject1/Marksman/atomic_2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['miya'])
def show_miya(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Miya_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Miya_list.keys())
def send_miya_video(message):
    command = message.text.strip().lower()
    model_info = Miya_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Melissa_list = {
    '/melissa_base': {'video_path': 'C:/pythonProject1/Marksman/Melissa_base.mp4', 'price': 210, 'link': 'Скачивание запрещено/408'},
    '/melissa_jujutsu': {'video_path': 'C:/pythonProject1/Marksman/Melissa_jujutsu.mp4', 'price': None, 'link': '@dikayl'},
    '/melissa_star': {'video_path': 'C:/pythonProject1/Marksman/melissa_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['melissa'])
def show_melissa(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Melissa_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Melissa_list.keys())
def send_melissa_video(message):
    command = message.text.strip().lower()
    model_info = Melissa_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




@bot.callback_query_handler(func=lambda call: call.data == 'order_model')
def handle_order_model_callback(call):
    # Основное меню заказа
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton(text="Заказать 3D печать с покраской", url="https://telegra.ph/3D-figurka-MLBB-04-11"),
        InlineKeyboardButton(text="Купить модель: Цена 0р", callback_data="buy_model_free"),
        InlineKeyboardButton(text="Подробнее", callback_data="details"),
        InlineKeyboardButton(text="Закрыть", callback_data="close"),
        InlineKeyboardButton(text="Онлайн-курс по 3D-печати", url="https://portfolio-4t5k.onrender.com/courses/printing"),
    )
    info_message = (
        "Сегодня акция: любая модель — 0₽ вместо 350₽!\n\n"
        "Для получения модели нажмите кнопку \"Купить модель: Цена 0р\".\n\n"
        "Если хочешь не покупать модели, а научиться извлекать и подготавливать их самостоятельно, доступен онлайн-курс по полному пайплайну подготовки к 3D-печати:"
    )
    bot.send_message(call.message.chat.id, text=info_message, reply_markup=markup)

# Обработчик кнопки "Купить модель: Цена 0р"
@bot.callback_query_handler(func=lambda call: call.data == 'buy_model_free')
def handle_buy_model_free(call):
    import random
    random_id = random.randint(1000, 9999)
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, text="Покупка успешна!")
    reply_markup = InlineKeyboardMarkup()
    reply_markup.add(
        InlineKeyboardButton(text="Онлайн-курс по 3D-печати", url="https://portfolio-4t5k.onrender.com/courses/printing")
    )
    bot.send_message(
        call.message.chat.id,
        f"Вы успешно купили модель!\nВаш ID: {random_id}\n\nДля получения модели напишите ваш ID и нужный облик персонажа —\n📩 @dikayl\n\nЕсли хочешь не покупать модели, а научиться извлекать и подготавливать их самостоятельно, доступен онлайн-курс по полному пайплайну подготовки к 3D-печати:",
        reply_markup=reply_markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'details')
def handle_details_callback(call):
    # Отправляем сообщение "Тут скоро будет информация" с кнопкой "Назад"
    markup = InlineKeyboardMarkup().add(
        InlineKeyboardButton(text="Назад", callback_data="back")
    )
    bot.send_message(call.message.chat.id, text="Выберите опцию:\n\n- Базовый пакет за 250₽: Получите модель OBJ/STL для 3D печати фигурки в маленьком масштабе без дополнительной обработки.\n\n- Премиум пакет от 1000₽ от сложности: Полная обработка модели, включая детализацию, разрезы, персонализированная подставка с вашем именем и уникальные элементы.\n\nЗа консультацией -> @dikayl", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'close' or call.data == 'back')
def handle_close_callback(call):
    # Удаляем сообщение по нажатию "Закрыть" или "Назад"
    bot.delete_message(call.message.chat.id, call.message.message_id)




Nolan_list = {
    '/nolan_base2': {'video_path': 'C:/pythonProject1/Marksman/nolan_base2.mp4', 'price': 290, 'link': 'Скачивание запрещено/399'},
}

@bot.message_handler(commands=['nolan'])
def show_nolan(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Nolan_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Nolan_list.keys())
def send_nolan_video(message):
    command = message.text.strip().lower()
    model_info = Nolan_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)

Cici_list = {
    '/cici_base2': {'video_path': 'C:/pythonProject1/Marksman/cici_base2.mp4', 'price': 290, 'link': 'Скачивание запрещено/399'},
}

@bot.message_handler(commands=['cici'])
def show_cici(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Cici_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Cici_list.keys())
def send_cici_video(message):
    command = message.text.strip().lower()
    model_info = Cici_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)

Ixia_list = {
    '/ixia_base': {'video_path': 'C:/pythonProject1/Marksman/Ixia_base.mp4', 'price': 290, 'link': 'Скачивание запрещено/399'},
}

@bot.message_handler(commands=['ixia'])
def show_ixia(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Ixia_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Ixia_list.keys())
def send_ixia_video(message):
    command = message.text.strip().lower()
    model_info = Ixia_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Layla_list = {
    '/layla_base': {'video_path': 'C:/pythonProject1/Marksman/Layla_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/400'},
    '/layla_base2': {'video_path': 'C:/pythonProject1/Marksman/Layla_base2.mp4', 'price': 210, 'link': 'Скачивание запрещено/401'},
    '/layla_base3': {'video_path': 'C:/pythonProject1/Marksman/Layla_base3.mp4', 'price': 230, 'link': 'Скачивание запрещено/402'},
    '/layla_base4': {'video_path': 'C:/pythonProject1/Marksman/Layla_base4.mp4', 'price': None, 'link': '@dikayl'},
    '/layla_saber': {'video_path': 'C:/pythonProject1/Marksman/Layla_saber.mp4', 'price': 210, 'link': 'Скачивание запрещено/403'},
    '/layla_star1': {'video_path': 'C:/pythonProject1/Marksman/star_1.mp4', 'price': None, 'link': '@dikayl'},
    '/layla_star2': {'video_path': 'C:/pythonProject1/Marksman/star_2.mp4', 'price': 210, 'link': 'Скачивание запрещено/404'},
    '/layla_star3': {'video_path': 'C:/pythonProject1/Marksman/star_3.mp4', 'price': None, 'link': '@dikayl'},
    '/layla_valentine': {'video_path': 'C:/pythonProject1/Marksman/valentine_1.mp4', 'price': 370, 'link': 'Скачивание запрещено/405'},
    '/layla_valentine2': {'video_path': 'C:/pythonProject1/Marksman/valentine_2.mp4', 'price': None, 'link': '@dikayl'},
    '/layla_aspirants': {'video_path': 'C:/pythonProject1/Marksman/aspirants_1.mp4', 'price': 280, 'link': 'Скачивание запрещено/406'},
    '/layla_aspirants2': {'video_path': 'C:/pythonProject1/Marksman/aspirants_2.mp4', 'price': None, 'link': '@dikayl'},
    '/layla_star4': {'video_path': 'C:/pythonProject1/Marksman/layla_star4.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['layla'])
def show_layla(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Layla_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Layla_list.keys())
def send_layla_video(message):
    command = message.text.strip().lower()
    model_info = Layla_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Kimmy_list = {
    '/kimmy_base': {'video_path': 'C:/pythonProject1/Marksman/Kimmy_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/396'},
    '/kimmy_dragon': {'video_path': 'C:/pythonProject1/Marksman/Kimmy_dragon.mp4', 'price': 230, 'link': 'Скачивание запрещено/437'},
    '/kimmy_epic': {'video_path': 'C:/pythonProject1/Marksman/Kimmy_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/438'},
    '/kimmy_special': {'video_path': 'C:/pythonProject1/Marksman/Kimmy_special.mp4', 'price': None, 'link': '@dikayl'},
    '/kimmy_wars': {'video_path': 'C:/pythonProject1/Marksman/Kimmy_wars.mp4', 'price': None, 'link': '@dikayl'},
    '/kimmy_star': {'video_path': 'C:/pythonProject1/Marksman/Kimmy_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['kimmy'])
def show_kimmy(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Kimmy_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Kimmy_list.keys())
def send_kimmy_video(message):
    command = message.text.strip().lower()
    model_info = Kimmy_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Karrie_list = {
    '/karrie_base': {'video_path': 'C:/pythonProject1/Marksman/Karrie_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/390'},
    '/karrie_star': {'video_path': 'C:/pythonProject1/Marksman/Karrie_star.mp4', 'price': None, 'link': '@dikayl'},
    '/karrie_halloween': {'video_path': 'C:/pythonProject1/Marksman/Karrie_halloween.mp4', 'price': None, 'link': '@dikayl'},
    '/karrie_epic2': {'video_path': 'C:/pythonProject1/Marksman/Karrie_epic2.mp4', 'price': 210, 'link': 'Скачивание запрещено/391'},
    '/karrie_epic': {'video_path': 'C:/pythonProject1/Marksman/Karrie_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/392'},
    '/karrie_elite2': {'video_path': 'C:/pythonProject1/Marksman/Karrie_elite2.mp4', 'price': 210, 'link': 'Скачивание запрещено/393'},
    '/karrie_elite': {'video_path': 'C:/pythonProject1/Marksman/Karrie_elite.mp4', 'price': 180, 'link': 'Скачивание запрещено/394'},
    '/karrie_base2': {'video_path': 'C:/pythonProject1/Marksman/Karrie_base2.mp4', 'price': 180, 'link': 'Скачивание запрещено/395'},
    '/karrie_star2': {'video_path': 'C:/pythonProject1/Marksman/Karrie_star2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['karrie'])
def show_karrie(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Karrie_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Karrie_list.keys())
def send_karrie_video(message):
    command = message.text.strip().lower()
    model_info = Karrie_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Irihel_list = {
    '/irihel_star': {'video_path': 'C:/pythonProject1/Marksman/Irihel_star.mp4', 'price': None, 'link': '@dikayl'},
    '/irihel_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Irihel_zodiac.mp4', 'price': None, 'link': '@dikayl'},
    '/irihel_epic': {'video_path': 'C:/pythonProject1/Marksman/Irihel_epic.mp4', 'price': 220, 'link': 'Скачивание запрещено/386'},
    '/irihel_epic2': {'video_path': 'C:/pythonProject1/Marksman/Irihel_epic2.mp4', 'price': 210, 'link': 'Скачивание запрещено/387'},
    '/irihel_base_1': {'video_path': 'C:/pythonProject1/Marksman/irihel_base_1.mp4', 'price': 290, 'link': 'Скачивание запрещено/388'},
    '/irihel_base_2': {'video_path': 'C:/pythonProject1/Marksman/irihel_base_2.mp4', 'price': 290, 'link': 'Скачивание запрещено/389'},
    '/irihel_base_3': {'video_path': 'C:/pythonProject1/Marksman/irihel_base_3.mp4', 'price': None, 'link': '@dikayl'},
    '/irihel_ducati2': {'video_path': 'C:/pythonProject1/Marksman/irihel_ducati2.mp4', 'price': None, 'link': '@dikayl'},
    '/irihel_ducati1': {'video_path': 'C:/pythonProject1/Marksman/irihel_ducati1.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['irihel'])
def show_irihel(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Irihel_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Irihel_list.keys())
def send_irihel_video(message):
    command = message.text.strip().lower()
    model_info = Irihel_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Hanabi_list = {
    '/hanabi_base': {'video_path': 'C:/pythonProject1/Marksman/Hanabi_base.mp4', 'price': 210, 'link': 'Скачивание запрещено/380'},
    '/hanabi_base2': {'video_path': 'C:/pythonProject1/Marksman/Hanabi_base2.mp4', 'price': 210, 'link': 'Скачивание запрещено/381'},
    '/hanabi_elite': {'video_path': 'C:/pythonProject1/Marksman/Hanabi_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/382'},
    '/hanabi_collector': {'video_path': 'C:/pythonProject1/Marksman/Hanabi_collector.mp4', 'price': None, 'link': '@dikayl'},
    '/hanabi_venom': {'video_path': 'C:/pythonProject1/Marksman/Hanabi_venom.mp4', 'price': None, 'link': '@dikayl'},
    '/hanabi_star': {'video_path': 'C:/pythonProject1/Marksman/Hanabi_star.mp4', 'price': None, 'link': '@dikayl'},
    '/hanabi_special': {'video_path': 'C:/pythonProject1/Marksman/Hanabi_special.mp4', 'price': None, 'link': '@dikayl'},
    '/hanabi_epic': {'video_path': 'C:/pythonProject1/Marksman/Hanabi_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/383'},
    '/hanabi_all': {'video_path': 'C:/pythonProject1/Marksman/All_1.mp4', 'price': 210, 'link': 'Скачивание запрещено/384'},
    '/hanabi_all2': {'video_path': 'C:/pythonProject1/Marksman/All_2.mp4', 'price': 210, 'link': 'Скачивание запрещено/385'},
}


@bot.message_handler(commands=['hanabi'])
def show_hanabi(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Hanabi_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Hanabi_list.keys())
def send_hanabi_video(message):
    command = message.text.strip().lower()
    model_info = Hanabi_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Granger_list = {
    '/granger_special': {'video_path': 'C:/pythonProject1/Marksman/Granger_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/376'},
    '/granger_star': {'video_path': 'C:/pythonProject1/Marksman/Granger_star.mp4', 'price': None, 'link': '@dikayl'},
    '/granger_transformer': {'video_path': 'C:/pythonProject1/Marksman/Granger_transformer.mp4', 'price': 230, 'link': 'Скачивание запрещено/377'},
    '/granger_base': {'video_path': 'C:/pythonProject1/Marksman/Granger_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/378'},
    '/granger_collector': {'video_path': 'C:/pythonProject1/Marksman/Granger_collector.mp4', 'price': None, 'link': '@dikayl'},
    '/granger_elite': {'video_path': 'C:/pythonProject1/Marksman/Granger_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/granger_legend': {'video_path': 'C:/pythonProject1/Marksman/Granger_legend.mp4', 'price': 210, 'link': 'Скачивание запрещено/379'},
    '/granger_lightborn': {'video_path': 'C:/pythonProject1/Marksman/Granger_lightborn.mp4', 'price': None, 'link': '@dikayl'},
    '/granger_create': {'video_path': 'C:/pythonProject1/Marksman/granger_create.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['granger'])
def show_granger(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Granger_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Granger_list.keys())
def send_granger_video(message):
    command = message.text.strip().lower()
    model_info = Granger_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Clint_list = {
    '/clint_base': {'video_path': 'C:/pythonProject1/Marksman/Clint_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/370'},
    '/clint_star': {'video_path': 'C:/pythonProject1/Marksman/Clint_star.mp4', 'price': None, 'link': '@dikayl'},
    '/clint_special': {'video_path': 'C:/pythonProject1/Marksman/Clint_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/371'},
    '/clint_s15': {'video_path': 'C:/pythonProject1/Marksman/Clint_s15.mp4', 'price': 240, 'link': 'Скачивание запрещено/372'},
    '/clint_m2': {'video_path': 'C:/pythonProject1/Marksman/Clint_m2.mp4', 'price': None, 'link': '@dikayl'},
    '/clint_elite': {'video_path': 'C:/pythonProject1/Marksman/Clint_elite.mp4', 'price': 200, 'link': 'Скачивание запрещено/373'},
    '/clint_collector': {'video_path': 'C:/pythonProject1/Marksman/Clint_collector.mp4', 'price': 230, 'link': 'Скачивание запрещено/374'},
    '/clint_valentine_1': {'video_path': 'C:/pythonProject1/Marksman/clint_valentine_1.mp4', 'price': 260, 'link': 'Скачивание запрещено/375'},
    '/clint_valentine_2': {'video_path': 'C:/pythonProject1/Marksman/clint_valentine_2.mp4', 'price': None, 'link': '@dikayl'},
    '/clint_valentine_3': {'video_path': 'C:/pythonProject1/Marksman/clint_valentine_3.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['clint'])
def show_clint(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Clint_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Clint_list.keys())
def send_clint_video(message):
    command = message.text.strip().lower()
    model_info = Clint_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Claude_list = {
    '/claude_base': {'video_path': 'C:/pythonProject1/Marksman/Claude_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/365'},
    '/claude_blazing': {'video_path': 'C:/pythonProject1/Marksman/Claude_blazing.mp4', 'price': 230, 'link': 'Скачивание запрещено/366'},
    '/claude_valentine': {'video_path': 'C:/pythonProject1/Marksman/Claude_valentine.mp4', 'price': None, 'link': '@dikayl'},
    '/claude_summer': {'video_path': 'C:/pythonProject1/Marksman/Claude_summer.mp4', 'price': 250, 'link': 'Скачивание запрещено/367'},
    '/claude_star': {'video_path': 'C:/pythonProject1/Marksman/Claude_star.mp4', 'price': None, 'link': '@dikayl'},
    '/claude_special': {'video_path': 'C:/pythonProject1/Marksman/Claude_special.mp4', 'price': 230, 'link': 'Скачивание запрещено/368'},
    '/claude_sancharacters': {'video_path': 'C:/pythonProject1/Marksman/Claude_sancharacters.mp4', 'price': None, 'link': '@dikayl'},
    '/claude_epic': {'video_path': 'C:/pythonProject1/Marksman/Claude_epic.mp4', 'price': 240, 'link': 'Скачивание запрещено/369'},
    '/claude_christmass': {'video_path': 'C:/pythonProject1/Marksman/Claude_christmass.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['claude'])
def show_claude(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Claude_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Claude_list.keys())
def send_claude_video(message):
    command = message.text.strip().lower()
    model_info = Claude_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Bruno_list = {
    '/bruno_base_1': {'video_path': 'C:/pythonProject1/Marksman/bruno_base_1.mp4', 'price': 190, 'link': 'Скачивание запрещено/361'},
    '/bruno_base_2': {'video_path': 'C:/pythonProject1/Marksman/bruno_base_2.mp4', 'price': None, 'link': '@dikayl'},
    '/bruno_special2': {'video_path': 'C:/pythonProject1/Marksman/Bruno_special2.mp4', 'price': 190, 'link': 'Скачивание запрещено/362'},
    '/bruno_special': {'video_path': 'C:/pythonProject1/Marksman/Bruno_special.mp4', 'price': 200, 'link': 'Скачивание запрещено/363'},
    '/bruno_neymar': {'video_path': 'C:/pythonProject1/Marksman/Bruno_neymar.mp4', 'price': None, 'link': '@dikayl'},
    '/bruno_elite': {'video_path': 'C:/pythonProject1/Marksman/Bruno_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/bruno_dawning': {'video_path': 'C:/pythonProject1/Marksman/Bruno_dawning.mp4', 'price': 200, 'link': 'Скачивание запрещено/364'},
}


@bot.message_handler(commands=['bruno'])
def show_bruno(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Bruno_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Bruno_list.keys())
def send_bruno_video(message):
    command = message.text.strip().lower()
    model_info = Bruno_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Brody_list = {
    '/brody_base': {'video_path': 'C:/pythonProject1/Marksman/Brody_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/358'},
    '/brody_collector': {'video_path': 'C:/pythonProject1/Marksman/Brody_collector.mp4', 'price': 250, 'link': 'Скачивание запрещено/359'},
    '/brody_mdt': {'video_path': 'C:/pythonProject1/Marksman/Brody_mdt.mp4', 'price': None, 'link': '@dikayl'},
    '/brody_star': {'video_path': 'C:/pythonProject1/Marksman/Brody_star.mp4', 'price': None, 'link': '@dikayl'},
    '/brody_stun1': {'video_path': 'C:/pythonProject1/Marksman/stun_1.mp4', 'price': None, 'link': '@dikayl'},
    '/brody_stun2': {'video_path': 'C:/pythonProject1/Marksman/stun_2.mp4', 'price': 230, 'link': 'Скачивание запрещено/360'},
}

@bot.message_handler(commands=['brody'])
def show_brody(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Brody_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Brody_list.keys())
def send_brody_video(message):
    command = message.text.strip().lower()
    model_info = Brody_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Beatrix_list = {
    '/beatrix_base': {'video_path': 'C:/pythonProject1/Marksman/Beatrix_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/355'},
    '/beatrix_elite': {'video_path': 'C:/pythonProject1/Marksman/Beatrix_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/beatrix_star': {'video_path': 'C:/pythonProject1/Marksman/Beatrix_star.mp4', 'price': None, 'link': '@dikayl'},
    '/beatrix_prime': {'video_path': 'C:/pythonProject1/Marksman/Beatrix_prime.mp4', 'price': 210, 'link': 'Скачивание запрещено/356'},
    '/beatrix_m4': {'video_path': 'C:/pythonProject1/Marksman/Beatrix_m4.mp4', 'price': 210, 'link': 'Скачивание запрещено/357'},
    '/beatrix_special': {'video_path': 'C:/pythonProject1/Marksman/Beatrix_m4.mp4', 'price': 210, 'link': 'Скачивание запрещено/357'},
}


@bot.message_handler(commands=['beatrix'])
def show_beatrix(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Beatrix_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Beatrix_list.keys())
def send_beatrix_video(message):
    command = message.text.strip().lower()
    model_info = Beatrix_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Nana_list = {
    '/nana_basic': {'video_path': 'C:/pythonProject1/Marksman/Nana_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/278'},
    '/nana_summer': {'video_path': 'C:/pythonProject1/Marksman/Nana_summer.mp4', 'price': None, 'link': '@dikayl'},
    '/nana_star': {'video_path': 'C:/pythonProject1/Marksman/Nana_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/279'},
    '/nana_special': {'video_path': 'C:/pythonProject1/Marksman/Nana_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/280'},
    '/nana_s1': {'video_path': 'C:/pythonProject1/Marksman/Nana_s1.mp4', 'price': 210, 'link': 'Скачивание запрещено/281'},
    '/nana_epic': {'video_path': 'C:/pythonProject1/Marksman/Nana_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/282'},
    '/nana_elite': {'video_path': 'C:/pythonProject1/Marksman/Nana_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/283'},
    '/nana_collector': {'video_path': 'C:/pythonProject1/Marksman/Nana_collector.mp4', 'price': None, 'link': '@dikayl'},
    '/nana_mistbender': {'video_path': 'C:/pythonProject1/Marksman/Nana_mistbender.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['nana'])
def show_nana(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Nana_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Nana_list.keys())
def send_nana_video(message):
    command = message.text.strip().lower()
    model_info = Nana_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Faramis_list = {
    '/faramis_basic': {'video_path': 'C:/pythonProject1/Marksman/Faramis_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/276'},
    '/faramis_elite': {'video_path': 'C:/pythonProject1/Marksman/Faramis_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/277'},
}


@bot.message_handler(commands=['faramis'])
def show_faramis(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Faramis_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Faramis_list.keys())
def send_faramis_video(message):
    command = message.text.strip().lower()
    model_info = Faramis_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Novaria_list = {
    '/novaria_base': {'video_path': 'C:/pythonProject1/Marksman/Novaria_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/275'},
}


@bot.message_handler(commands=['novaria'])
def show_novaria(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Novaria_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Novaria_list.keys())
def send_novaria_video(message):
    command = message.text.strip().lower()
    model_info = Novaria_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Julian_list = {
    '/julian_base': {'video_path': 'C:/pythonProject1/Marksman/Julian_base.mp4', 'price': 230, 'link': 'Скачивание запрещено/274'},
    '/julian_jujutsu': {'video_path': 'C:/pythonProject1/Marksman/Julian_jujutsu.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['julian'])
def show_julian(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Julian_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Julian_list.keys())
def send_julian_video(message):
    command = message.text.strip().lower()
    model_info = Julian_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Yve_list = {
    '/yve_base': {'video_path': 'C:/pythonProject1/Marksman/Yve_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/272'},
    '/yve_elite': {'video_path': 'C:/pythonProject1/Marksman/Yve_elite.mp4', 'price': 22, 'link': 'Скачивание запрещено/273'},
}


@bot.message_handler(commands=['yve'])
def show_yve(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Yve_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Yve_list.keys())
def send_yve_video(message):
    command = message.text.strip().lower()
    model_info = Yve_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Cecilion_list = {
    '/cecion_base': {'video_path': 'C:/pythonProject1/Marksman/Cecilion_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/269'},
    '/cecion_collector': {'video_path': 'C:/pythonProject1/Marksman/Cecilion_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/270'},
    '/cecilion_valentine1': {'video_path': 'C:/pythonProject1/Marksman/cecilion_valentine_1.mp4', 'price': None, 'link': '@dikayl'},
    '/cecilion_valentine2': {'video_path': 'C:/pythonProject1/Marksman/cecilion_valentine_2', 'price': None, 'link': '@dikayl'},
    '/cecilion_valentine3': {'video_path': 'C:/pythonProject1/Marksman/cecilion_valentine_3.mp4', 'price': None, 'link': '@dikayl'},
    '/cecilion_valentine4': {'video_path': 'C:/pythonProject1/Marksman/cecilion_valentine_4.mp4', 'price': None, 'link': '@dikayl'},
    '/cecilion_star_1': {'video_path': 'C:/pythonProject1/Marksman/cecilion_star_1.mp4', 'price': None, 'link': '@dikayl'},
    '/cecilion_star_2': {'video_path': 'C:/pythonProject1/Marksman/cecilion_star_2.mp4', 'price': 290, 'link': 'Скачивание запрещено/271'},

}

@bot.message_handler(commands=['cecilion'])
def show_cecilion(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Cecilion_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Cecilion_list.keys())
def send_cecilion_video(message):
    command = message.text.strip().lower()
    model_info = Cecilion_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Lylia_list = {
    '/lylia_base': {'video_path': 'C:/pythonProject1/Marksman/Lylia_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/267'},
    '/lylia_elite': {'video_path': 'C:/pythonProject1/Marksman/Lylia_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/268'},
    '/lylia_halloween': {'video_path': 'C:/pythonProject1/Marksman/Lylia_halloween.mp4', 'price': None, 'link': '@dikayl'},
    '/lylia_special': {'video_path': 'C:/pythonProject1/Marksman/Lylia_special.mp4', 'price': None, 'link': '@dikayl'},
    '/lylia_neobear': {'video_path': 'C:/pythonProject1/Marksman/lylia_neobear.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['lylia'])
def show_lylia(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Lylia_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Lylia_list.keys())
def send_lylia_video(message):
    command = message.text.strip().lower()
    model_info = Lylia_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Kadita_list = {
    '/kadita_base': {'video_path': 'C:/pythonProject1/Marksman/Kadita_base.mp4', 'price': 200, 'link': 'Скачивание запрещено/439'},
    '/kadita_special': {'video_path': 'C:/pythonProject1/Marksman/Kadita_special.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['kadita'])
def show_kadita(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Kadita_list)])
    bot.send_message(message.chat.id, fighters_menu)


@bot.message_handler(func=lambda message: message.text.lower() in Kadita_list.keys())
def send_kadita_video(message):
    command = message.text.strip().lower()
    model_info = Kadita_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


# Define the callback handler for the "Buy" button
@bot.callback_query_handler(func=lambda call: call.data.startswith("Buy_kadita"))
def Buy_kadita_callback(call):
    user_id = call.from_user.id
    user_data = db.get_user_data(user_id)
    if user_data is None:
        bot.send_message(user_id, "Write me bro -> @dikayl.")
        return

    model_name = call.data[12:]  # Remove the 'Buy_kadita' prefix from callback_data
    model_info = Kadita_list.get(f'/{model_name}')
    if model_info is None:
        bot.send_message(user_id, "Write me bro -> @dikayl")
        return

    model_




Harith_list = {
    '/harith_base': {'video_path': 'C:/pythonProject1/Marksman/Harith_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/264'},
    '/harith_elite': {'video_path': 'C:/pythonProject1/Marksman/Harith_elite.mp4', 'price': 200, 'link': 'Скачивание запрещено/265'},
    '/harith_epic': {'video_path': 'C:/pythonProject1/Marksman/Harith_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/harith_lighborn': {'video_path': 'C:/pythonProject1/Marksman/Harith_lighborn.mp4', 'price': None, 'link': '@dikayl'},
    '/harith_515': {'video_path': 'C:/pythonProject1/Marksman/Harith_515.mp4', 'price': 250, 'link': 'Скачивание запрещено/266'},
    '/harith_christmass': {'video_path': 'C:/pythonProject1/Marksman/harith_christmass.mp4', 'price': 250, 'link': 'Скачивание запрещено/266'},
}


@bot.message_handler(commands=['harith'])
def show_harith(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Harith_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Harith_list.keys())
def send_harith_video(message):
    command = message.text.strip().lower()
    model_info = Harith_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Vale_list = {
    '/vale_base': {'video_path': 'C:/pythonProject1/Marksman/Vale_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/259'},
    '/vale_elite': {'video_path': 'C:/pythonProject1/Marksman/Vale_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/260'},
    '/vale_epic': {'video_path': 'C:/pythonProject1/Marksman/Vale_epic.mp4', 'price': 180, 'link': 'Скачивание запрещено/261'},
    '/vale_star': {'video_path': 'C:/pythonProject1/Marksman/Vale_star.mp4', 'price': 180, 'link': 'Скачивание запрещено/262'},
    '/vale_collector': {'video_path': 'C:/pythonProject1/Marksman/Vale_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/263'},
    '/vale_dawning': {'video_path': 'C:/pythonProject1/Marksman/Vale_dawning.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['vale'])
def show_vale(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Vale_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Vale_list.keys())
def send_vale_video(message):
    command = message.text.strip().lower()
    model_info = Vale_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Change_list = {
    '/change_base': {'video_path': 'C:/pythonProject1/Marksman/Change_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/255'},
    '/change_elite': {'video_path': 'C:/pythonProject1/Marksman/Change_elite.mp4', 'price': 200, 'link': 'Скачивание запрещено/256'},
    '/change_san': {'video_path': 'C:/pythonProject1/Marksman/Change_san.mp4', 'price': None, 'link': '@dikayl'},
    '/change_lunar': {'video_path': 'C:/pythonProject1/Marksman/Change_lunar.mp4', 'price': None, 'link': '@dikayl'},
    '/change_epic2': {'video_path': 'C:/pythonProject1/Marksman/Change_epic2.mp4', 'price': None, 'link': '@dikayl'},
    '/change_epic': {'video_path': 'C:/pythonProject1/Marksman/Change_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/change_star': {'video_path': 'C:/pythonProject1/Marksman/Change_star.mp4', 'price': 200, 'link': 'Скачивание запрещено/257'},
    '/change_special': {'video_path': 'C:/pythonProject1/Marksman/Change_special.mp4', 'price': 230, 'link': 'Скачивание запрещено/258'},
}


@bot.message_handler(commands=['change'])
def show_change(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Change_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Change_list.keys())
def send_change_video(message):
    command = message.text.strip().lower()
    model_info = Change_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Valir_list = {
    '/valir_base': {'video_path': 'C:/pythonProject1/Marksman/Valir_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/251'},
    '/valir_special': {'video_path': 'C:/pythonProject1/Marksman/Valir_special.mp4', 'price': 200, 'link': 'Скачивание запрещено/252'},
    '/valir_dragon': {'video_path': 'C:/pythonProject1/Marksman/Valir_dragon.mp4', 'price': 210, 'link': 'Скачивание запрещено/253'},
    '/valir_collector': {'video_path': 'C:/pythonProject1/Marksman/Valir_collector.mp4', 'price': 200, 'link': 'Скачивание запрещено/254'},
    '/valir_star': {'video_path': 'C:/pythonProject1/Marksman/Valir_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['valir'])
def show_valir(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Valir_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Valir_list.keys())
def send_valir_video(message):
    command = message.text.strip().lower()
    model_info = Valir_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Pharsa_list = {
    '/pharsa_base': {'video_path': 'C:/pythonProject1/Marksman/Pharsa_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/245'},
    '/pharsa_base2': {'video_path': 'C:/pythonProject1/Marksman/Pharsa_base2.mp4', 'price': 180, 'link': 'Скачивание запрещено/246'},
    '/pharsa_special': {'video_path': 'C:/pythonProject1/Marksman/Pharsa_special.mp4', 'price': 230, 'link': 'Скачивание запрещено/247'},
    '/pharsa_s14': {'video_path': 'C:/pythonProject1/Marksman/Pharsa_s14.mp4', 'price': None, 'link': '@dikayl'},
    '/pharsa_epic': {'video_path': 'C:/pythonProject1/Marksman/Pharsa_epic.mp4', 'price': 190, 'link': 'Скачивание запрещено/248'},
    '/pharsa_elite': {'video_path': 'C:/pythonProject1/Marksman/Pharsa_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/249'},
    '/pharsa_collector': {'video_path': 'C:/pythonProject1/Marksman/Pharsa_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/250'},
    '/pharsa_star': {'video_path': 'C:/pythonProject1/Marksman/Pharsa_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['pharsa'])
def show_pharsa(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Pharsa_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Pharsa_list.keys())
def send_pharsa_video(message):
    command = message.text.strip().lower()
    model_info = Pharsa_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Zhask_list = {
    '/zhask_base': {'video_path': 'C:/pythonProject1/Marksman/Zhask_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/241'},
    '/zhask_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Zhask_zodiac.mp4', 'price': 220, 'link': 'Скачивание запрещено/242'},
    '/zhask_special': {'video_path': 'C:/pythonProject1/Marksman/Zhask_special.mp4', 'price': 200, 'link': 'Скачивание запрещено/243'},
    '/zhask_epic': {'video_path': 'C:/pythonProject1/Marksman/Zhask_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/zhask_base2': {'video_path': 'C:/pythonProject1/Marksman/Zhask_base2.mp4', 'price': 180, 'link': 'Скачивание запрещено/244'},
}


@bot.message_handler(commands=['zhask'])
def show_zhask(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Zhask_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Zhask_list.keys())
def send_zhask_video(message):
    command = message.text.strip().lower()
    model_info = Zhask_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Odette_list = {
    '/odette_base': {'video_path': 'C:/pythonProject1/Marksman/Odette_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/235'},
    '/odette_create': {'video_path': 'C:/pythonProject1/Marksman/Odette_create.mp4', 'price': None, 'link': '@dikayl'},
    '/odette_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Odette_zodiac.mp4', 'price': None, 'link': '@dikayl'},
    '/odette_special': {'video_path': 'C:/pythonProject1/Marksman/Odette_special.mp4', 'price': 200, 'link': 'Скачивание запрещено/236'},
    '/odette_lunar': {'video_path': 'C:/pythonProject1/Marksman/Odette_lunar.mp4', 'price': 230, 'link': 'Скачивание запрещено/237'},
    '/odette_epic': {'video_path': 'C:/pythonProject1/Marksman/Odette_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/238'},
    '/odette_christmass_1': {'video_path': 'C:/pythonProject1/Marksman/odette_christmass_1.mp4', 'price': None, 'link': '@dikayl'},
    '/odette_christmass_2': {'video_path': 'C:/pythonProject1/Marksman/odette_christmass_2.mp4', 'price': 310, 'link': 'Скачивание запрещено/239'},
    '/odette_christmass_3': {'video_path': 'C:/pythonProject1/Marksman/odette_christmass_3.mp4', 'price': 310, 'link': 'Скачивание запрещено/240'},
}


@bot.message_handler(commands=['odette'])
def show_odette(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Odette_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Odette_list.keys())
def send_odette_video(message):
    command = message.text.strip().lower()
    model_info = Odette_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Vexana_list = {
    '/vexana_base': {'video_path': 'C:/pythonProject1/Marksman/Vexana_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/231'},
    '/vexana_epic': {'video_path': 'C:/pythonProject1/Marksman/Vexana_epic.mp4', 'price': 190, 'link': 'Скачивание запрещено/232'},
    '/vexana_s12': {'video_path': 'C:/pythonProject1/Marksman/Vexana_s12.mp4', 'price': 190, 'link': 'Скачивание запрещено/233'},
    '/vexana_star_1': {'video_path': 'C:/pythonProject1/Marksman/vexana_star_1.mp4', 'price': 290, 'link': 'Скачивание запрещено/234'},
    '/vexana_star_2': {'video_path': 'C:/pythonProject1/Marksman/vexana_star_2.mp4', 'price': None, 'link': '@dikayl'},
    '/vexana_star_3': {'video_path': 'C:/pythonProject1/Marksman/vexana_star_3.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['vexana'])
def show_vexana(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Vexana_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Vexana_list.keys())
def send_vexana_video(message):
    command = message.text.strip().lower()
    model_info = Vexana_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Cyclops_list = {
    '/cyclops_base': {'video_path': 'C:/pythonProject1/Marksman/Cyclops_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/227'},
    '/cyclops_collector': {'video_path': 'C:/pythonProject1/Marksman/Cyclops_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/228'},
    '/cyclops_elite': {'video_path': 'C:/pythonProject1/Marksman/Cyclops_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/229'},
    '/cyclops_star': {'video_path': 'C:/pythonProject1/Marksman/Cyclops_star.mp4', 'price': None, 'link': '@dikayl'},
    '/cyclops_saber': {'video_path': 'C:/pythonProject1/Marksman/Cyclops_saber.mp4', 'price': None, 'link': '@dikayl'},
    '/cyclops_halloween': {'video_path': 'C:/pythonProject1/Marksman/Cyclops_halloween.mp4', 'price': 230, 'link': 'Скачивание запрещено/230'},
}


@bot.message_handler(commands=['cyclops'])
def show_cyclops(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Cyclops_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Cyclops_list.keys())
def send_cyclops_video(message):
    command = message.text.strip().lower()
    model_info = Cyclops_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Kagura_list = {
    '/kagura_base': {'video_path': 'C:/pythonProject1/Marksman/Kagura_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/221'},
    '/kagura_base2': {'video_path': 'C:/pythonProject1/Marksman/Kagura_base2.mp4', 'price': 190, 'link': 'Скачивание запрещено/222'},
    '/kagura_epic': {'video_path': 'C:/pythonProject1/Marksman/Kagura_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/223'},
    '/kagura_exo': {'video_path': 'C:/pythonProject1/Marksman/Kagura_exo.mp4', 'price': None, 'link': '@dikayl'},
    '/kagura_exo2': {'video_path': 'C:/pythonProject1/Marksman/Kagura_exo2.mp4', 'price': None, 'link': '@dikayl'},
    '/kagura_special': {'video_path': 'C:/pythonProject1/Marksman/Kagura_special.mp4', 'price': 230, 'link': 'Скачивание запрещено/224'},
    '/kagura_star': {'video_path': 'C:/pythonProject1/Marksman/Kagura_star.mp4', 'price': None, 'link': '@dikayl'},
    '/kagura_summer': {'video_path': 'C:/pythonProject1/Marksman/Kagura_summer.mp4', 'price': 250, 'link': 'Скачивание запрещено/225'},
    '/kagura_star_gold_1': {'video_path': 'C:/pythonProject1/Marksman/kagura_star_gold_1.mp4', 'price': 200, 'link': 'Скачивание запрещено/226'},
    '/kagura_star_gold_2': {'video_path': 'C:/pythonProject1/Marksman/kagura_star_gold_2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['kagura'])
def show_kagura(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Kagura_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Kagura_list.keys())
def send_kagura_video(message):
    command = message.text.strip().lower()
    model_info = Kagura_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Gord_list = {
    '/gord_base': {'video_path': 'C:/pythonProject1/Marksman/Gord_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/218'},
    '/gord_christmass': {'video_path': 'C:/pythonProject1/Marksman/Gord_christmass.mp4', 'price': None, 'link': '@dikayl'},
    '/gord_legend': {'video_path': 'C:/pythonProject1/Marksman/Gord_legend.mp4', 'price': 190, 'link': 'Скачивание запрещено/219'},
    '/gord_star': {'video_path': 'C:/pythonProject1/Marksman/Gord_star.mp4', 'price': None, 'link': '@dikayl'},
    '/gord_s21': {'video_path': 'C:/pythonProject1/Marksman/Gord_s21.mp4', 'price': 200, 'link': 'Скачивание запрещено/220'},
    '/gord_legend2': {'video_path': 'C:/pythonProject1/Marksman/gord_legend2.mp4', 'price': 200, 'link': 'Скачивание запрещено/220'},
}


@bot.message_handler(commands=['gord'])
def show_gord(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Gord_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Gord_list.keys())
def send_gord_video(message):
    command = message.text.strip().lower()
    model_info = Gord_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Akai_list = {
    '/akai_base': {'video_path': 'C:/pythonProject1/Marksman/akai_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/214'},
    '/akai_elite': {'video_path': 'C:/pythonProject1/Marksman/akai_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/215'},
    '/akai_epic': {'video_path': 'C:/pythonProject1/Marksman/akai_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/216'},
    '/akai_halloween': {'video_path': 'C:/pythonProject1/Marksman/akai_halloween.mp4', 'price': 210, 'link': 'Скачивание запрещено/217'},
    '/akai_s19': {'video_path': 'C:/pythonProject1/Marksman/akai_s19.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['akai'])
def show_akai(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Akai_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Akai_list.keys())
def send_akai_video(message):
    command = message.text.strip().lower()
    model_info = Akai_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)

Alice_list = {
    '/alice_base': {'video_path': 'C:/pythonProject1/Marksman/Alice_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/214'},
    '/alice_elite': {'video_path': 'C:/pythonProject1/Marksman/Alice_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/215'},
    '/alice_epic': {'video_path': 'C:/pythonProject1/Marksman/Alice_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/216'},
    '/alice_special': {'video_path': 'C:/pythonProject1/Marksman/Alice_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/217'},
    '/alice_star': {'video_path': 'C:/pythonProject1/Marksman/Alice_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['alice'])
def show_alice(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Alice_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Alice_list.keys())
def send_alice_video(message):
    command = message.text.strip().lower()
    model_info = Alice_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Lunox_list = {
    '/lunox_base': {'video_path': 'C:/pythonProject1/Marksman/Lunox_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/208'},
    '/lunox_elite': {'video_path': 'C:/pythonProject1/Marksman/Lunox_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/209'},
    '/lunox_epic': {'video_path': 'C:/pythonProject1/Marksman/Lunox_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/210'},
    '/lunox_epic2': {'video_path': 'C:/pythonProject1/Marksman/Lunox_epic2.mp4', 'price': 200, 'link': 'Скачивание запрещено/211'},
    '/lunox_epic3': {'video_path': 'C:/pythonProject1/Marksman/Lunox_epic3.mp4', 'price': 210, 'link': 'Скачивание запрещено/212'},
    '/lunox_legend': {'video_path': 'C:/pythonProject1/Marksman/Lunox_legend.mp4', 'price': None, 'link': '@dikayl'},
    '/lunox_star': {'video_path': 'C:/pythonProject1/Marksman/Lunox_star.mp4', 'price': 200, 'link': 'Скачивание запрещено/213'},
    '/lunox_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Lunox_zodiac.mp4', 'price': None, 'link': '@dikayl'},
    '/lunox_epic4': {'video_path': 'C:/pythonProject1/Marksman/lunox_epic4.mp4', 'price': None, 'link': '@dikayl'},
    '/lunox_legend2': {'video_path': 'C:/pythonProject1/Marksman/lunox_legend2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['lunox'])
def show_lunox(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Lunox_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Lunox_list.keys())
def send_lunox_video(message):
    command = message.text.strip().lower()
    model_info = Lunox_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Aurora_list = {
    '/aurora_base': {'video_path': 'C:/pythonProject1/Marksman/Aurora_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/204'},
    '/aurora_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Aurora_zodiac.mp4', 'price': 230, 'link': 'Скачивание запрещено/205'},
    '/aurora_star': {'video_path': 'C:/pythonProject1/Marksman/Aurora_star.mp4', 'price': 230, 'link': 'Скачивание запрещено/206'},
    '/aurora_lunar': {'video_path': 'C:/pythonProject1/Marksman/Aurora_lunar.mp4', 'price': None, 'link': '@dikayl'},
    '/aurora_fighters': {'video_path': 'C:/pythonProject1/Marksman/Aurora_fighters.mp4', 'price': 210, 'link': 'Скачивание запрещено/207'},
}


@bot.message_handler(commands=['aurora'])
def show_aurora(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Aurora_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Aurora_list.keys())
def send_aurora_video(message):
    command = message.text.strip().lower()
    model_info = Aurora_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Xavier_list = {
    '/xavier_base': {'video_path': 'C:/pythonProject1/Marksman/Xavier_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/202'},
    '/xavier_base2': {'video_path': 'C:/pythonProject1/Marksman/Xavier_base2.mp4', 'price': 190, 'link': 'Скачивание запрещено/203'},
    '/xavier_jujutsu': {'video_path': 'C:/pythonProject1/Marksman/Xavier_jujutsu.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['xavier'])
def show_xavier(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Xavier_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Xavier_list.keys())
def send_xavier_video(message):
    command = message.text.strip().lower()
    model_info = Xavier_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Valentina_list = {
    '/valentina_base': {'video_path': 'C:/pythonProject1/Marksman/Valentina_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/200'},
    '/valentina_star': {'video_path': 'C:/pythonProject1/Marksman/Valentina_star.mp4', 'price': None, 'link': '@dikayl'},
    '/valentina_elite': {'video_path': 'C:/pythonProject1/Marksman/Valentina_elite.mp4', 'price': 200, 'link': 'Скачивание запрещено/201'},
    '/valentina_collector': {'video_path': 'C:/pythonProject1/Marksman/valentina_collector.mp4', 'price': 200, 'link': 'Скачивание запрещено/201'},
}


@bot.message_handler(commands=['valentina'])
def show_valentina(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Valentina_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Valentina_list.keys())
def send_valentina_video(message):
    command = message.text.strip().lower()
    model_info = Valentina_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)






Loyi_list = {
    '/louyi_base': {'video_path': 'C:/pythonProject1/Marksman/Louyi_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/194'},
    '/louyi_elite': {'video_path': 'C:/pythonProject1/Marksman/Louyi_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/195'},
    '/louyi_epic': {'video_path': 'C:/pythonProject1/Marksman/Louyi_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/196'},
    '/louyi_lunar': {'video_path': 'C:/pythonProject1/Marksman/Louyi_lunar.mp4', 'price': 210, 'link': 'Скачивание запрещено/197'},
    '/louyi_star': {'video_path': 'C:/pythonProject1/Marksman/Louyi_star.mp4', 'price': 230, 'link': 'Скачивание запрещено/198'},
    '/louyi_collector': {'video_path': 'C:/pythonProject1/Marksman/Louyi_collector.mp4', 'price': 230, 'link': 'Скачивание запрещено/199'},
}


@bot.message_handler(commands=['louyi'])
def show_louyi(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Loyi_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Loyi_list.keys())
def send_louyi_video(message):
    command = message.text.strip().lower()
    model_info = Loyi_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Esmeralda_list = {
    '/esmeralda_basic': {'video_path': 'C:/pythonProject1/Marksman/Esmeralda_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/189'},
    '/esmeralda_valentine2': {'video_path': 'C:/pythonProject1/Marksman/Esmeralda_valentine2.mp4', 'price': None, 'link': '@dikayl'},
    '/esmeralda_blazing': {'video_path': 'C:/pythonProject1/Marksman/Esmeralda_blazing.mp4', 'price': 210, 'link': 'Скачивание запрещено/190'},
    '/esmeralda_collector': {'video_path': 'C:/pythonProject1/Marksman/Esmeralda_collector.mp4', 'price': 250, 'link': 'Скачивание запрещено/191'},
    '/esmeralda_dawning': {'video_path': 'C:/pythonProject1/Marksman/Esmeralda_dawning.mp4', 'price': 210, 'link': 'Скачивание запрещено/192'},
    '/esmeralda_elite': {'video_path': 'C:/pythonProject1/Marksman/Esmeralda_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/193'},
    '/esmeralda_star': {'video_path': 'C:/pythonProject1/Marksman/Esmeralda_star.mp4', 'price': 200, 'link': 'Скачивание запрещено/194'},
    '/esmeralda_valentine': {'video_path': 'C:/pythonProject1/Marksman/Esmeralda_valentine.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['esmeralda'])
def show_esmeralda(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Esmeralda_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Esmeralda_list.keys())
def send_esmeralda_video(message):
    command = message.text.strip().lower()
    model_info = Esmeralda_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Eudora_list = {
    '/eudora_base': {'video_path': 'C:/pythonProject1/Marksman/Eudora_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/186'},
    '/eudora_star': {'video_path': 'C:/pythonProject1/Marksman/Eudora_star.mp4', 'price': 230, 'link': 'Скачивание запрещено/187'},
    '/eudora_atomic': {'video_path': 'C:/pythonProject1/Marksman/Eudora_atomic.mp4', 'price': 230, 'link': 'Скачивание запрещено/188'},
    '/eudora_christmass': {'video_path': 'C:/pythonProject1/Marksman/Eudora_christmass.mp4', 'price': None, 'link': '@dikayl'},
    '/eudora_epic': {'video_path': 'C:/pythonProject1/Marksman/Eudora_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/189'},
    '/eudora_limited': {'video_path': 'C:/pythonProject1/Marksman/Eudora_limited.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['eudora'])
def show_eudora(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Eudora_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Eudora_list.keys())
def send_eudora_video(message):
    command = message.text.strip().lower()
    model_info = Eudora_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Mathilda_list = {
    '/mathilda_basic': {'video_path': 'C:/pythonProject1/Marksman/Mathilda_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/86'},
    '/mathilda_elite': {'video_path': 'C:/pythonProject1/Marksman/Mathilda_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/87'},
    '/mathilda_mdt': {'video_path': 'C:/pythonProject1/Marksman/Mathilda_mdt.mp4', 'price': 230, 'link': 'Скачивание запрещено/88'},
}


@bot.message_handler(commands=['mathilda'])
def show_mathilda(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Mathilda_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Mathilda_list.keys())
def send_mathilda_video(message):
    command = message.text.strip().lower()
    model_info = Mathilda_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Benedetta_list = {
    '/benedetta_base': {'video_path': 'C:/pythonProject1/Marksman/Benedetta_base.mp4', 'price': 210, 'link': 'Скачивание запрещено/83'},
    '/benedetta_collector': {'video_path': 'C:/pythonProject1/Marksman/Benedetta_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/84'},
    '/benedetta_special': {'video_path': 'C:/pythonProject1/Marksman/Benedetta_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/85'},
    '/benedetta_star_1': {'video_path': 'C:/pythonProject1/Marksman/benedetta_star_1.mp4', 'price': None, 'link': '@dikayl'},
    '/benedetta_star_2': {'video_path': 'C:/pythonProject1/Marksman/benedetta_star_2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['benedetta'])
def show_benedetta(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Benedetta_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Benedetta_list.keys())
def send_benedetta_video(message):
    command = message.text.strip().lower()
    model_info = Benedetta_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Alucard_list = {
    '/alucard_basic': {'video_path': 'C:/pythonProject1/Marksman/Alucard_basic.mp4', 'price': 210, 'link': 'Скачивание запрещено/78'},
    '/alucard_agent': {'video_path': 'C:/pythonProject1/Marksman/Alucard_agent.mp4', 'price': None, 'link': '@dikayl'},
    '/alucard_epic': {'video_path': 'C:/pythonProject1/Marksman/Alucard_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/alucard_legend1': {'video_path': 'C:/pythonProject1/Marksman/Alucard_legend1.mp4', 'price': None, 'link': '@dikayl'},
    '/alucard_lightborn': {'video_path': 'C:/pythonProject1/Marksman/Alucard_lightborn.mp4', 'price': 370, 'link': 'Скачивание запрещено/79'},
    '/alucard_s2': {'video_path': 'C:/pythonProject1/Marksman/Alucard_s2.mp4', 'price': 210, 'link': 'Скачивание запрещено/80'},
    '/alucard_starwars': {'video_path': 'C:/pythonProject1/Marksman/Alucard_starwars.mp4', 'price': None, 'link': '@dikayl'},
    '/alucard_star': {'video_path': 'C:/pythonProject1/Marksman/Alucard_star.mp4', 'price': 180, 'link': 'Скачивание запрещено/81'},
    '/alucard_valentine': {'video_path': 'C:/pythonProject1/Marksman/Alucard_valentine.mp4', 'price': 250, 'link': 'Скачивание запрещено/82'},
}


@bot.message_handler(commands=['alucard'])
def show_alucard(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Alucard_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Alucard_list.keys())
def send_alucard_video(message):
    command = message.text.strip().lower()
    model_info = Alucard_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Zilong_list = {
    '/zilong_elite': {'video_path': 'C:/pythonProject1/Marksman/Zilong_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/71'},
    '/zilong_elite2': {'video_path': 'C:/pythonProject1/Marksman/Zilong_elite2.mp4', 'price': 200, 'link': 'Скачивание запрещено/72'},
    '/zilong_epic': {'video_path': 'C:/pythonProject1/Marksman/Zilong_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/73'},
    '/zilong_star': {'video_path': 'C:/pythonProject1/Marksman/Zilong_star.mp4', 'price': 200, 'link': 'Скачивание запрещено/74'},
    '/zilong_summer': {'video_path': 'C:/pythonProject1/Marksman/Zilong_summer.mp4', 'price': 200, 'link': 'Скачивание запрещено/75'},
    '/zilong_515': {'video_path': 'C:/pythonProject1/Marksman/Zilong_515.mp4', 'price': None, 'link': '@dikayl'},
    '/zilong_basic': {'video_path': 'C:/pythonProject1/Marksman/Zilong_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/76'},
    '/zilong_christmass': {'video_path': 'C:/pythonProject1/Marksman/Zilong_christmass.mp4', 'price': None, 'link': '@dikayl'},
    '/zilong_collector': {'video_path': 'C:/pythonProject1/Marksman/zilong_collector1.mp4', 'price': 310, 'link': 'Скачивание запрещено/77'},
}


@bot.message_handler(commands=['zilong'])
def show_zilong(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Zilong_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Zilong_list.keys())
def send_zilong_video(message):
    command = message.text.strip().lower()
    model_info = Zilong_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Harley_list = {
    '/harley_basic': {'video_path': 'C:/pythonProject1/Marksman/Harley_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/66'},
    '/harley_epic': {'video_path': 'C:/pythonProject1/Marksman/Harley_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/harley_special': {'video_path': 'C:/pythonProject1/Marksman/Harley_special.mp4', 'price': 200, 'link': 'Скачивание запрещено/67'},
    '/harley_star': {'video_path': 'C:/pythonProject1/Marksman/Harley_star.mp4', 'price': 200, 'link': 'Скачивание запрещено/68'},
    '/harley_collector': {'video_path': 'C:/pythonProject1/Marksman/Harley_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/69'},
    '/harley_special2_1': {'video_path': 'C:/pythonProject1/Marksman/harley_special2_1.mp4', 'price': 290, 'link': 'Скачивание запрещено/70'},
    '/harley_special2_2': {'video_path': 'C:/pythonProject1/Marksman/harley_special2_2.mp4', 'price': None, 'link': '@dikayl'},
    '/harley_special2_3': {'video_path': 'C:/pythonProject1/Marksman/harley_special2_3.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['harley'])
def show_harley(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Harley_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Harley_list.keys())
def send_harley_video(message):
    command = message.text.strip().lower()
    model_info = Harley_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Joy_list = {
    '/joy_base': {'video_path': 'C:/pythonProject1/Marksman/Joy_base.mp4', 'price': None, 'link': '@dikayl'},
    '/joy_elite': {'video_path': 'C:/pythonProject1/Marksman/joy_elite.mp4', 'price': None, 'link': '@dikayl'},
}

@bot.message_handler(commands=['joy'])
def show_joy(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Joy_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Joy_list.keys())
def send_joy_video(message):
    command = message.text.strip().lower()
    model_info = Joy_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Aamon_list = {
    '/aamon_basic': {'video_path': 'C:/pythonProject1/Marksman/Aamon_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/64'},
    '/aamon_elite': {'video_path': 'C:/pythonProject1/Marksman/Aamon_elite.mp4', 'price': 200, 'link': 'Скачивание запрещено/65'},
    '/aamon_star': {'video_path': 'C:/pythonProject1/Marksman/Aamon_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['aamon'])
def show_aamon(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Aamon_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Aamon_list.keys())
def send_aamon_video(message):
    command = message.text.strip().lower()
    model_info = Aamon_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Ling_list = {
    '/ling_base': {'video_path': 'C:/pythonProject1/Marksman/Ling_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/60'},
    '/ling_collector': {'video_path': 'C:/pythonProject1/Marksman/Ling_collector.mp4', 'price': 250, 'link': 'Скачивание запрещено/61'},
    '/ling_dragon': {'video_path': 'C:/pythonProject1/Marksman/Ling_dragon.mp4', 'price': None, 'link': '@dikayl'},
    '/ling_kungfu': {'video_path': 'C:/pythonProject1/Marksman/Ling_kungfu.mp4', 'price': 190, 'link': 'Скачивание запрещено/62'},
    '/ling_mworld': {'video_path': 'C:/pythonProject1/Marksman/Ling_mworld.mp4', 'price': None, 'link': '@dikayl'},
    '/ling_special': {'video_path': 'C:/pythonProject1/Marksman/Ling_special.mp4', 'price': 190, 'link': 'Скачивание запрещено/63'},
    '/ling_star_1': {'video_path': 'C:/pythonProject1/Marksman/ling_star_1.mp4', 'price': None, 'link': '@dikayl'},
    '/ling_star_2': {'video_path': 'C:/pythonProject1/Marksman/ling_star_2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['ling'])
def show_ling(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Ling_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Ling_list.keys())
def send_ling_video(message):
    command = message.text.strip().lower()
    model_info = Ling_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Hanzo_list = {
    '/hanzo_elite': {'video_path': 'C:/pythonProject1/Marksman/Hanzo_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/59'},
    '/hanzo_base': {'video_path': 'C:/pythonProject1/Marksman/hanzo_base.mp4', 'price': 230, 'link': 'Скачивание запрещено/58'},
    '/hanzo_special_1': {'video_path': 'C:/pythonProject1/Marksman/hanzo_special_1.mp4', 'price': None, 'link': '@dikayl'},
    '/hanzo_special_2': {'video_path': 'C:/pythonProject1/Marksman/hanzo_special_2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['hanzo'])
def show_hanzo(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Hanzo_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Hanzo_list.keys())
def send_hanzo_video(message):
    command = message.text.strip().lower()
    model_info = Hanzo_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Gusion_list = {
    '/gusion_elite': {'video_path': 'C:/pythonProject1/Marksman/Gusion_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/52'},
    '/gusion_epic': {'video_path': 'C:/pythonProject1/Marksman/Gusion_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/53'},
    '/gusion_fight': {'video_path': 'C:/pythonProject1/Marksman/Gusion_fight.mp4', 'price': 190, 'link': 'Скачивание запрещено/54'},
    '/gusion_star': {'video_path': 'C:/pythonProject1/Marksman/Gusion_star.mp4', 'price': 190, 'link': 'Скачивание запрещено/55'},
    '/gusion_valentine': {'video_path': 'C:/pythonProject1/Marksman/Gusion_valentine.mp4', 'price': None, 'link': '@dikayl'},
    '/gusion_venom': {'video_path': 'C:/pythonProject1/Marksman/Gusion_venom.mp4', 'price': None, 'link': '@dikayl'},
    '/gusion_11': {'video_path': 'C:/pythonProject1/Marksman/Gusion_11.mp4', 'price': 220, 'link': 'Скачивание запрещено/56'},
    '/gusion_basic': {'video_path': 'C:/pythonProject1/Marksman/Gusion_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/57'},
    '/gusion_collector': {'video_path': 'C:/pythonProject1/Marksman/Gusion_collector.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['gusion'])
def show_gusion(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Gusion_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Gusion_list.keys())
def send_gusion_video(message):
    command = message.text.strip().lower()
    model_info = Gusion_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Lancelot_list = {
    '/lancelot_basic': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/43'},
    '/lancelot_basic2': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_basic2.mp4', 'price': 190, 'link': 'Скачивание запрещено/44'},
    '/lancelot_star': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_star.mp4', 'price': 230, 'link': 'Скачивание запрещено/45'},
    '/lancelot_epic3': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_epic3.mp4', 'price': 200, 'link': 'Скачивание запрещено/46'},
    '/lancelot_epic2': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_epic2.mp4', 'price': 200, 'link': 'Скачивание запрещено/47'},
    '/lancelot_epic': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/lancelot_dragon': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_dragon.mp4', 'price': 230, 'link': 'Скачивание запрещено/49'},
    '/lancelot_christmass': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_christmass.mp4', 'price': None, 'link': '@dikayl'},
    '/lancelot_zodiac2': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_zodiac2.mp4', 'price': 200, 'link': 'Скачивание запрещено/50'},
    '/lancelot_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Lancelot_zodiac.mp4', 'price': 190, 'link': 'Скачивание запрещено/51'},
    '/lancelot_elite': {'video_path': 'C:/pythonProject1/Marksman/lancelot_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/51'},
}


@bot.message_handler(commands=['lancelot'])
def show_lancelot(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Lancelot_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Lancelot_list.keys())
def send_lancelot_video(message):
    command = message.text.strip().lower()
    model_info = Lancelot_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



YiSunshin_list = {
    '/yisunshin_epic': {'video_path': 'C:/pythonProject1/Marksman/YiSunshin_epic.mp4', 'price': 250, 'link': 'Скачивание запрещено/39'},
    '/yisunshin_star': {'video_path': 'C:/pythonProject1/Marksman/YiSunshin_star.mp4', 'price': None, 'link': '@dikayl'},
    '/yisunshin_basic': {'video_path': 'C:/pythonProject1/Marksman/YiSunshin_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/40'},
    '/yisunshin_elite2': {'video_path': 'C:/pythonProject1/Marksman/YiSunshin_elite2.mp4', 'price': 270, 'link': 'Скачивание запрещено/41'},
    '/yisunshin_collector_1': {'video_path': 'C:/pythonProject1/Marksman/yisunshin_collector_1.mp4', 'price': None, 'link': '@dikayl'},
    '/yisunshin_collector_2': {'video_path': 'C:/pythonProject1/Marksman/yisunshin_collector_3.mp4', 'price': None, 'link': '@dikayl'},
    '/yisunshin_collector_3': {'video_path': 'C:/pythonProject1/Marksman/yisunshin_collector_3.mp4', 'price': None, 'link': '@dikayl'},
    '/yisunshin_elite_1': {'video_path': 'C:/pythonProject1/Marksman/yisunshin_elite_1.mp4', 'price': None, 'link': '@dikayl'},
    '/yisunshin_elite_2': {'video_path': 'C:/pythonProject1/Marksman/yisunshin_elite_2.mp4', 'price': 310, 'link': 'Скачивание запрещено/42'},
    '/yisunshin_s31': {'video_path': 'C:/pythonProject1/Marksman/yisunshin_s31.mp4', 'price': 310, 'link': 'Скачивание запрещено/42'},
}


@bot.message_handler(commands=['yisunshin'])
def show_yisunshin(message):
    yisunshin_menu = "\n".join([f"{i+1}) {model}" for i, model in enumerate(YiSunshin_list)])
    bot.send_message(message.chat.id, yisunshin_menu)

@bot.message_handler(func=lambda message: message.text.lower() in YiSunshin_list.keys())
def send_yisunshin_video(message):
    command = message.text.strip().lower()
    model_info = YiSunshin_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)
Hayabusa_list = {
    '/hayabusa_elite': {'video_path': 'C:/pythonProject1/Marksman/Hayabusa_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/33'},
    '/hayabusa_11': {'video_path': 'C:/pythonProject1/Marksman/Hayabusa_11.mp4', 'price': 250, 'link': 'Скачивание запрещено/34'},
    '/hayabusa_elite2': {'video_path': 'C:/pythonProject1/Marksman/Hayabusa_elite2.mp4', 'price': 190, 'link': 'Скачивание запрещено/35'},
    '/hayabusa_star': {'video_path': 'C:/pythonProject1/Marksman/Hayabusa_star.mp4', 'price': None, 'link': '@dikayl'},
    '/hayabusa_summer': {'video_path': 'C:/pythonProject1/Marksman/Hayabusa_summer.mp4', 'price': 230, 'link': 'Скачивание запрещено/36'},
    '/hayabusa_base_1': {'video_path': 'C:/pythonProject1/Marksman/hayabusa_base_1.mp4', 'price': None, 'link': '@dikayl'},
    '/hayabusa_base_2': {'video_path': 'C:/pythonProject1/Marksman/hayabusa_base_2.mp4', 'price': 290, 'link': 'Скачивание запрещено/37'},
    '/hayabusa_base_3': {'video_path': 'C:/pythonProject1/Marksman/hayabusa_base_3.mp4', 'price': 290, 'link': 'Скачивание запрещено/38'},
    '/hayabusa_base_4': {'video_path': 'C:/pythonProject1/Marksman/hayabusa_base_4.mp4', 'price': None, 'link': '@dikayl'},
}

@bot.message_handler(commands=['hayabusa'])
def show_hayabusa(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Hayabusa_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Hayabusa_list.keys())
def send_hayabusa_video(message):
    command = message.text.strip().lower()
    model_info = Hayabusa_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)





Selena_list = {
    '/selena_base': {'video_path': 'C:/pythonProject1/Marksman/Selena_base.mp4', 'price': 100, 'link': 'Скачивание запрещено/28'},
    '/selena_elite': {'video_path': 'C:/pythonProject1/Marksman/Selena_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/29'},
    '/selena_epic': {'video_path': 'C:/pythonProject1/Marksman/Selena_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/30'},
    '/selena_abyss': {'video_path': 'C:/pythonProject1/Marksman/Selena_abyss.mp4', 'price': 210, 'link': 'Скачивание запрещено/31'},
    '/selena_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Selena_zodiac.mp4', 'price': 250, 'link': 'Скачивание запрещено/32'},
    '/selena_stun1': {'video_path': 'C:/pythonProject1/Marksman/selena_stun1.mp4', 'price': None, 'link': '@dikayl'},
    '/selena_stun2': {'video_path': 'C:/pythonProject1/Marksman/selena_stun2.mp4', 'price': None, 'link': '@dikayl'},
    '/selena_stun3': {'video_path': 'C:/pythonProject1/Marksman/selena_stun3.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['selena'])
def show_selena(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Selena_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Selena_list.keys())
def send_selena_video(message):
    command = message.text.strip().lower()
    model_info = Selena_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Natalia_list = {
    '/natalia_base': {'video_path': 'C:/pythonProject1/Marksman/Natalia_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/26'},
    '/natalia_elite': {'video_path': 'C:/pythonProject1/Marksman/Natalia_elite.mp4', 'price': 144, 'link': 'Скачивание запрещено/27'},
    '/natalia_special': {'video_path': 'C:/pythonProject1/Marksman/Natalia_special.mp4', 'price': None, 'link': '@dikayl'},
    '/natalia_star': {'video_path': 'C:/pythonProject1/Marksman/Natalia_star.mp4', 'price': None, 'link': '@dikayl'},
    '/natalia_special2': {'video_path': 'C:/pythonProject1/Marksman/Natalia_special2.mp4', 'price': None, 'link': '@dikayl'},
    '/natalia_kyber1': {'video_path': 'C:/pythonProject1/Marksman/kyber_1.mp4', 'price': None, 'link': '@dikayl'},
    '/natalia_kyber2': {'video_path': 'C:/pythonProject1/Marksman/kyber_2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['natalia'])
def show_natalia(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Natalia_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Natalia_list.keys())
def send_natalia_video(message):
    command = message.text.strip().lower()
    model_info = Natalia_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Fanny_list = {
    '/fanny_elite': {'video_path': 'C:/pythonProject1/Marksman/Fanny_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/16'},
    '/fanny_epic': {'video_path': 'C:/pythonProject1/Marksman/Fanny_epic.mp4', 'price': 250, 'link': 'Скачивание запрещено/17'},
    '/fanny_s3': {'video_path': 'C:/pythonProject1/Marksman/Fanny_s3.mp4', 'price': None, 'link': '@dikayl'},
    '/fanny_star': {'video_path': 'C:/pythonProject1/Marksman/Fanny_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/18'},
    '/fanny_summer': {'video_path': 'C:/pythonProject1/Marksman/Fanny_summer.mp4', 'price': 230, 'link': 'Скачивание запрещено/19'},
    '/fanny_basic_1': {'video_path': 'C:/pythonProject1/Marksman/Fanny_basic_1.mp4', 'price': 230, 'link': 'Скачивание запрещено/20'},
    '/fanny_basic_2': {'video_path': 'C:/pythonProject1/Marksman/Fanny_basic_2.mp4', 'price': 230, 'link': 'Скачивание запрещено/21'},
    '/fanny_christmass_1': {'video_path': 'C:/pythonProject1/Marksman/fanny_christmass_1.mp4', 'price': None, 'link': '@dikayl'},
    '/fanny_christmass_2': {'video_path': 'C:/pythonProject1/Marksman/fanny_christmass_2.mp4', 'price': None, 'link': '@dikayl'},
    '/fanny_lightborn_1': {'video_path': 'C:/pythonProject1/Marksman/fanny_lightborn_1.mp4', 'price': None, 'link': '@dikayl'},
    '/fanny_lightborn_2': {'video_path': 'C:/pythonProject1/Marksman/fanny_lightborn_2.mp4', 'price': 350, 'link': 'Скачивание запрещено/22'},
    '/fanny_lightborn_3': {'video_path': 'C:/pythonProject1/Marksman/fanny_lightborn_3.mp4', 'price': 350, 'link': 'Скачивание запрещено/23'},
    '/fanny_valentine_1': {'video_path': 'C:/pythonProject1/Marksman/fanny_valentine_1.mp4', 'price': 350, 'link': 'Скачивание запрещено/24'},
    '/fanny_valentine_2': {'video_path': 'C:/pythonProject1/Marksman/fanny_valentine_2.mp4', 'price': None, 'link': '@dikayl'},
    '/fanny_valentine_3': {'video_path': 'C:/pythonProject1/Marksman/fanny_valentine_3.mp4', 'price': None, 'link': '@dikayl'},
    '/fanny_aspirants_1': {'video_path': 'C:/pythonProject1/Marksman/fanny_aspirants_1.mp4', 'price': 350, 'link': 'Скачивание запрещено/25'},
    '/fanny_aspirants_2': {'video_path': 'C:/pythonProject1/Marksman/fanny_aspirants_2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['fanny'])
def show_fanny(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Fanny_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Fanny_list.keys())
def send_fanny_video(message):
    command = message.text.strip().lower()
    model_info = Fanny_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Karina_list = {
    '/karina_basic': {'video_path': 'C:/pythonProject1/Marksman/karina_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/10'},
    '/karina_christmass': {'video_path': 'C:/pythonProject1/Marksman/Karina_christmass.mp4', 'price': None, 'link': '@dikayl'},
    '/karina_elite': {'video_path': 'C:/pythonProject1/Marksman/Karina_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/11'},
    '/karina_elite2': {'video_path': 'C:/pythonProject1/Marksman/Karina_elite2.mp4', 'price': None, 'link': '@dikayl'},
    '/karina_epic': {'video_path': 'C:/pythonProject1/Marksman/Karina_epic.mp4', 'price': 250, 'link': 'Скачивание запрещено/12'},
    '/karina_fighter': {'video_path': 'C:/pythonProject1/Marksman/Karina_fighter.mp4', 'price': 210, 'link': 'Скачивание запрещено/13'},
    '/karina_star': {'video_path': 'C:/pythonProject1/Marksman/Karina_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/14'},
    '/karina_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Karina_zodiac.mp4', 'price': 190, 'link': 'Скачивание запрещено/15'},
}


@bot.message_handler(commands=['karina'])
def show_karina(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Karina_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Karina_list.keys())
def send_karina_video(message):
    command = message.text.strip().lower()
    model_info = Karina_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)





Saber_list = {
    '/saber_basic': {'video_path': 'C:/pythonProject1/Marksman/Saber_Basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/3'},
    '/saber_elite': {'video_path': 'C:/pythonProject1/Marksman/Saber_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/4'},
    '/saber_2': {'video_path': 'C:/pythonProject1/Marksman/Saber_2.mp4', 'price': 200, 'link': 'Скачивание запрещено/5'},
    '/saber_1': {'video_path': 'C:/pythonProject1/Marksman/Saber_1.mp4', 'price': 200, 'link': 'Скачивание запрещено/6'},
    '/saber_legend': {'video_path': 'C:/pythonProject1/Marksman/Saber_legend.mp4', 'price': None, 'link': '@dikayl'},
    '/saber_epic': {'video_path': 'C:/pythonProject1/Marksman/Saber_epic.mp4', 'price': 200, 'link': 'Скачивание запрещено/7'},
    '/saber_star2': {'video_path': 'C:/pythonProject1/Marksman/Saber_star2.mp4', 'price': 200, 'link': 'Скачивание запрещено/8'},
    '/saber_star': {'video_path': 'C:/pythonProject1/Marksman/Saber_star.mp4', 'price': 200, 'link': 'Скачивание запрещено/9'},
}


@bot.message_handler(commands=['saber'])
def show_saber(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Saber_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Saber_list.keys())
def send_saber_video(message):
    command = message.text.strip().lower()
    model_info = Saber_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Zhong_list = {
    '/zhong_base': {'video_path': 'C:/pythonProject1/Marksman/Yu-Zhong_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/180'},
    '/zhong_collector': {'video_path': 'C:/pythonProject1/Marksman/Yu-Zhong_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/181'},
    '/zhong_star': {'video_path': 'C:/pythonProject1/Marksman/Yu-Zhong_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/182'},
    '/zhong_exorcists1': {'video_path': 'C:/pythonProject1/Marksman/exorcists_1.mp4', 'price': 210, 'link': 'Скачивание запрещено/183'},
    '/zhong_exorcists2': {'video_path': 'C:/pythonProject1/Marksman/exorcists_2.mp4', 'price': 210, 'link': 'Скачивание запрещено/184'},
    '/zhong_m5': {'video_path': 'C:/pythonProject1/Marksman/zhong_m5.mp4', 'price': 210, 'link': 'Скачивание запрещено/184'},
    '/zhong_prime': {'video_path': 'C:/pythonProject1/Marksman/zhong_prime.mp4', 'price': 210, 'link': 'Скачивание запрещено/184'},
}


@bot.message_handler(commands=['zhong'])
def show_zhong(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Zhong_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Zhong_list.keys())
def send_zhong_video(message):
    command = message.text.strip().lower()
    model_info = Zhong_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Yin_list = {
    '/yin_base': {'video_path': 'C:/pythonProject1/Marksman/in_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/178'},
    '/yin_jujutsu': {'video_path': 'C:/pythonProject1/Marksman/in_jujutsu.mp4', 'price': None, 'link': '@dikayl'},
    '/yin_worl': {'video_path': 'C:/pythonProject1/Marksman/in_worl.mp4', 'price': 250, 'link': 'Скачивание запрещено/179'},
}


@bot.message_handler(commands=['yin'])
def show_yin(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Yin_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Yin_list.keys())
def send_yin_video(message):
    command = message.text.strip().lower()
    model_info = Yin_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Xborg_list = {
    '/xborg_base': {'video_path': 'C:/pythonProject1/Marksman/XBorg_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/174'},
    '/xborg_elite': {'video_path': 'C:/pythonProject1/Marksman/XBorg_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/175'},
    '/xborg_star': {'video_path': 'C:/pythonProject1/Marksman/XBorg_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/176'},
    '/xborg_11': {'video_path': 'C:/pythonProject1/Marksman/XBorg_11-11.mp4', 'price': None, 'link': '@dikayl'},
    '/xborg_transformer': {'video_path': 'C:/pythonProject1/Marksman/XBorg_transformer.mp4', 'price': 210, 'link': 'Скачивание запрещено/177'},
}


@bot.message_handler(commands=['xborg'])
def show_xborg(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Xborg_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Xborg_list.keys())
def send_xborg_video(message):
    command = message.text.strip().lower()
    model_info = Xborg_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Thamuz_list = {
    '/thamuz_base': {'video_path': 'C:/pythonProject1/Marksman/Thamuz_base.mp4', 'price': 330, 'link': 'Скачивание запрещено/170'},
    '/thamuz_elite': {'video_path': 'C:/pythonProject1/Marksman/Thamuz_elite.mp4', 'price': 33, 'link': 'Скачивание запрещено/171'},
    '/thamuz_special': {'video_path': 'C:/pythonProject1/Marksman/Thamuz_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/172'},
    '/thamuz_star': {'video_path': 'C:/pythonProject1/Marksman/Thamuz_star.mp4', 'price': 190, 'link': 'Скачивание запрещено/173'},
    '/thamuz_kungfu': {'video_path': 'C:/pythonProject1/Marksman/Thamuz_kungfu.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['thamuz'])
def show_thamuz(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Thamuz_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Thamuz_list.keys())
def send_thamuz_video(message):
    command = message.text.strip().lower()
    model_info = Thamuz_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Terizla_list = {
    '/terizla_base': {'video_path': 'C:/pythonProject1/Marksman/Terizla_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/168'},
    '/terizla_elite': {'video_path': 'C:/pythonProject1/Marksman/Terizla_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/169'},
    '/terizla_special': {'video_path': 'C:/pythonProject1/Marksman/Terizla_special.mp4', 'price': None, 'link': '@dikayl'},
    '/terizla_s22': {'video_path': 'C:/pythonProject1/Marksman/Terizla_s22.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['terizla'])
def show_terizla(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Terizla_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Terizla_list.keys())
def send_terizla_video(message):
    command = message.text.strip().lower()
    model_info = Terizla_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Sun_list = {
    '/sun_base': {'video_path': 'C:/pythonProject1/Marksman/Sun_base.mp4', 'price': 210, 'link': 'Скачивание запрещено/165'},
    '/sun_star': {'video_path': 'C:/pythonProject1/Marksman/Sun_star.mp4', 'price': 250, 'link': 'Скачивание запрещено/166'},
    '/sun_special': {'video_path': 'C:/pythonProject1/Marksman/Sun_special.mp4', 'price': None, 'link': '@dikayl'},
    '/sun_collector': {'video_path': 'C:/pythonProject1/Marksman/Sun_collector.mp4', 'price': 250, 'link': 'Скачивание запрещено/167'},
}


@bot.message_handler(commands=['sun'])
def show_sun(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Sun_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Sun_list.keys())
def send_sun_video(message):
    command = message.text.strip().lower()
    model_info = Sun_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Silvanna_list = {
    '/silvanna_basic': {'video_path': 'C:/pythonProject1/Marksman/Silvanna_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/159'},
    '/silvanna_elite': {'video_path': 'C:/pythonProject1/Marksman/Silvanna_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/160'},
    '/silvanna_elite2': {'video_path': 'C:/pythonProject1/Marksman/Silvanna_elite2.mp4', 'price': 210, 'link': 'Скачивание запрещено/161'},
    '/silvanna_collector': {'video_path': 'C:/pythonProject1/Marksman/Silvanna_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/162'},
    '/silvanna_star': {'video_path': 'C:/pythonProject1/Marksman/Silvanna_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/163'},
    '/silvanna_collector2': {'video_path': 'C:/pythonProject1/Marksman/Silvanna_collector2.mp4', 'price': 210, 'link': 'Скачивание запрещено/164'},
}


@bot.message_handler(commands=['silvanna'])
def show_silvanna(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Silvanna_list)])
    bot.send_message(message.chat.id, fighters_menu)


@bot.message_handler(func=lambda message: message.text.lower() in Silvanna_list.keys())
def send_silvanna_video(message):
    command = message.text.strip().lower()
    model_info = Silvanna_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


# Define the callback handler for the "Buy" button
@bot.callback_query_handler(func=lambda call: call.data.startswith("Buy_silvanna"))
def Buy_silvanna_callback(call):
    user_id = call.from_user.id
    user_data = db.get_user_data(user_id)
    if user_data is None:
        bot.send_message(user_id, "Write me bro -> @dikayl.")
        return

    model_name = call.data[13:]  # Remove the 'Buy_silvanna' prefix from callback_data
    model_info = Silvanna_list.get(f'/{model_name}')
    if model_info is None:
        bot.send_message(user_id, "Write me bro -> @dikayl")
        return




Ruby_list = {
    '/ruby_base': {'video_path': 'C:/pythonProject1/Marksman/Ruby_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/152'},
    '/ruby_base2': {'video_path': 'C:/pythonProject1/Marksman/Ruby_base2.mp4', 'price': 210, 'link': 'Скачивание запрещено/153'},
    '/ruby_star': {'video_path': 'C:/pythonProject1/Marksman/Ruby_star.mp4', 'price': None, 'link': '@dikayl'},
    '/ruby_aspirants': {'video_path': 'C:/pythonProject1/Marksman/Ruby_aspirants.mp4', 'price': 270, 'link': 'Скачивание запрещено/154'},
    '/ruby_elite1': {'video_path': 'C:/pythonProject1/Marksman/ruby_elite1.mp4', 'price': 250, 'link': 'Скачивание запрещено/155'},
    '/ruby_elite2': {'video_path': 'C:/pythonProject1/Marksman/ruby_elite2.mp4', 'price': 250, 'link': 'Скачивание запрещено/156'},
    '/ruby_elite2_1': {'video_path': 'C:/pythonProject1/Marksman/ruby_elite2_1.mp4', 'price': 290, 'link': 'Скачивание запрещено/157'},
    '/ruby_elite2_2': {'video_path': 'C:/pythonProject1/Marksman/ruby_elite2_2.mp4', 'price': None, 'link': '@dikayl'},
    '/ruby_epic_1': {'video_path': 'C:/pythonProject1/Marksman/ruby_epic_1.mp4', 'price': None, 'link': '@dikayl'},
    '/ruby_epic_2': {'video_path': 'C:/pythonProject1/Marksman/ruby_epic_2.mp4', 'price': 290, 'link': 'Скачивание запрещено/158'},
}


@bot.message_handler(commands=['ruby'])
def show_ruby(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Ruby_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Ruby_list.keys())
def send_ruby_video(message):
    command = message.text.strip().lower()
    model_info = Ruby_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Phoeveus_list = {
    '/phoeveus_base': {'video_path': 'C:/pythonProject1/Marksman/Phoeveus_base.mp4', 'price': 210, 'link': 'Скачивание запрещено/151'},
}


@bot.message_handler(commands=['phoeveus'])
def show_phoeveus(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Phoeveus_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Phoeveus_list.keys())
def send_phoeveus_video(message):
    command = message.text.strip().lower()
    model_info = Phoeveus_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Paquito_list = {
    '/paquito_base': {'video_path': 'C:/pythonProject1/Marksman/Paquito_base.mp4', 'price': 210, 'link': 'Скачивание запрещено/147'},
    '/paquito_base2': {'video_path': 'C:/pythonProject1/Marksman/Paquito_base2.mp4', 'price': 333, 'link': 'Скачивание запрещено/148'},
    '/paquito_collector': {'video_path': 'C:/pythonProject1/Marksman/Paquito_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/149'},
    '/paquito_special': {'video_path': 'C:/pythonProject1/Marksman/Paquito_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/150'},
    '/paquito_special2': {'video_path': 'C:/pythonProject1/Marksman/Paquito_special2.mp4', 'price': None, 'link': '@dikayl'},
    '/paquito_star': {'video_path': 'C:/pythonProject1/Marksman/Paquito_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['paquito'])
def show_paquito(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Paquito_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Paquito_list.keys())
def send_paquito_video(message):
    command = message.text.strip().lower()
    model_info = Paquito_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Minsitthar_list = {
    '/minsitthar_base': {'video_path': 'C:/pythonProject1/Marksman/Minsitthar_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/144'},
    '/minsitthar_base2': {'video_path': 'C:/pythonProject1/Marksman/Minsitthar_base2.mp4', 'price': 190, 'link': 'Скачивание запрещено/145'},
    '/minsitthar_elite': {'video_path': 'C:/pythonProject1/Marksman/Minsitthar_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/146'},
}


@bot.message_handler(commands=['minsitthar'])
def show_minsitthar(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Minsitthar_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Minsitthar_list.keys())
def send_minsitthar_video(message):
    command = message.text.strip().lower()
    model_info = Minsitthar_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Masha_list = {
    '/masha_basic': {'video_path': 'C:/pythonProject1/Marksman/Masha_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/442'},
    '/masha_dragon': {'video_path': 'C:/pythonProject1/Marksman/Masha_dragon.mp4', 'price': 210, 'link': 'Скачивание запрещено/443'},
    '/masha_s23': {'video_path': 'C:/pythonProject1/Marksman/Masha_s23.mp4', 'price': 230, 'link': 'Скачивание запрещено/444'},
    '/masha_special': {'video_path': 'C:/pythonProject1/Marksman/Masha_special.mp4', 'price': None, 'link': '@dikayl'},
    '/masha_star': {'video_path': 'C:/pythonProject1/Marksman/Masha_star.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['masha'])
def show_masha(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Masha_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Masha_list.keys())
def send_masha_video(message):
    command = message.text.strip().lower()
    model_info = Masha_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Martis_list = {
    '/martis_base': {'video_path': 'C:/pythonProject1/Marksman/Martis_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/140'},
    '/martis_epic': {'video_path': 'C:/pythonProject1/Marksman/Martis_epic.mp4', 'price': 310, 'link': 'Скачивание запрещено/141'},
    '/martis_star': {'video_path': 'C:/pythonProject1/Marksman/Martis_star.mp4', 'price': 270, 'link': 'Скачивание запрещено/142'},
    '/martis_special_1': {'video_path': 'C:/pythonProject1/Marksman/martis_special_1.mp4', 'price': 310, 'link': 'Скачивание запрещено/143'},
    '/martis_special_2': {'video_path': 'C:/pythonProject1/Marksman/martis_special_2.mp4', 'price': None, 'link': '@dikayl'},
    '/martis_zodiac': {'video_path': 'C:/pythonProject1/Marksman/martis_zodiac.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['martis'])
def show_martis(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Martis_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Martis_list.keys())
def send_martis_video(message):
    command = message.text.strip().lower()
    model_info = Martis_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



LapuLapu_list = {
    '/lapulapu_base': {'video_path': 'C:/pythonProject1/Marksman/Lapu-Lapu_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/137'},
    '/lapulapu_star': {'video_path': 'C:/pythonProject1/Marksman/Lapu-Lapu_star.mp4', 'price': None, 'link': '@dikayl'},
    '/lapulapu_s28': {'video_path': 'C:/pythonProject1/Marksman/Lapu-Lapu_s28.mp4', 'price': 250, 'link': 'Скачивание запрещено/138'},
    '/lapulapu_special': {'video_path': 'C:/pythonProject1/Marksman/Lapu-Lapu_special.mp4', 'price': 230, 'link': 'Скачивание запрещено/139'},
}


@bot.message_handler(commands=['lapulapu'])
def show_lapulapu(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(LapuLapu_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in LapuLapu_list.keys())
def send_lapulapu_video(message):
    command = message.text.strip().lower()
    model_info = LapuLapu_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Khaleed_list = {
    '/khaleed_base': {'video_path': 'C:/pythonProject1/Marksman/Khaleed_base.mp4', 'price': 200, 'link': 'Скачивание запрещено/135'},
    '/khaleed_elite': {'video_path': 'C:/pythonProject1/Marksman/Khaleed_elite.mp4', 'price': 200, 'link': 'Скачивание запрещено/136'},
}


@bot.message_handler(commands=['khaleed'])
def show_khaleed(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Khaleed_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Khaleed_list.keys())
def send_khaleed_video(message):
    command = message.text.strip().lower()
    model_info = Khaleed_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Leomord_list = {
    '/leomord_epic': {'video_path': 'C:/pythonProject1/Marksman/leomord_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/leomord_special_1': {'video_path': 'C:/pythonProject1/Marksman/leomord_special_1.mp4', 'price': None, 'link': '@dikayl'},
    '/leomord_special_2': {'video_path': 'C:/pythonProject1/Marksman/leomord_special_2.mp4', 'price': None, 'link': '@dikayl'},
    '/leomord_special_3': {'video_path': 'C:/pythonProject1/Marksman/leomord_special_3.mp4', 'price': None, 'link': '@dikayl'},
    '/leomord_star_1': {'video_path': 'C:/pythonProject1/Marksman/leomord_star_1.mp4', 'price': None, 'link': '@dikayl'},
    '/leomord_star_2': {'video_path': 'C:/pythonProject1/Marksman/leomord_star_2.mp4', 'price': None, 'link': '@dikayl'},
    '/leomord_star_3': {'video_path': 'C:/pythonProject1/Marksman/leomord_star_3.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['leomord'])
def show_leomord(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Leomord_list)])
    bot.send_message(message.chat.id, fighters_menu)


@bot.message_handler(func=lambda message: message.text.lower() in Leomord_list.keys())
def send_leomord_video(message):
    command = message.text.strip().lower()
    model_info = Leomord_list.get(command)

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Jawhead_list = {
    '/jawhead_collector': {'video_path': 'C:/pythonProject1/Marksman/Jawhead_collector.mp4', 'price': 190, 'link': 'Скачивание запрещено/130'},
    '/jawhead_elite': {'video_path': 'C:/pythonProject1/Marksman/Jawhead_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/jawhead_mdt': {'video_path': 'C:/pythonProject1/Marksman/Jawhead_mdt.mp4', 'price': None, 'link': '@dikayl'},
    '/jawhead_special': {'video_path': 'C:/pythonProject1/Marksman/Jawhead_special.mp4', 'price': 250, 'link': 'Скачивание запрещено/131'},
    '/jawhead_special2': {'video_path': 'C:/pythonProject1/Marksman/Jawhead_special2.mp4', 'price': 290, 'link': 'Скачивание запрещено/132'},
    '/jawhead_star': {'video_path': 'C:/pythonProject1/Marksman/Jawhead_star.mp4', 'price': None, 'link': '@dikayl'},
    '/jawhead_base_1': {'video_path': 'C:/pythonProject1/Marksman/jawhead_base_1.mp4', 'price': 200, 'link': 'Скачивание запрещено/133'},
    '/jawhead_base_2': {'video_path': 'C:/pythonProject1/Marksman/jawhead_base_2.mp4', 'price': 200, 'link': 'Скачивание запрещено/134'},
}


@bot.message_handler(commands=['jawhead'])
def show_jawhead(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Jawhead_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Jawhead_list.keys())
def send_jawhead_video(message):
    command = message.text.strip().lower()
    model_info = Jawhead_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Hilda_list = {
    '/hilda_basic': {'video_path': 'C:/pythonProject1/Marksman/Hilda_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/126'},
    '/hilda_elite': {'video_path': 'C:/pythonProject1/Marksman/Hilda_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/127'},
    '/hilda_s5': {'video_path': 'C:/pythonProject1/Marksman/Hilda_s5.mp4', 'price': 230, 'link': 'Скачивание запрещено/128'},
    '/hilda_zodiac': {'video_path': 'C:/pythonProject1/Marksman/Hilda_zodiac.mp4', 'price': 250, 'link': 'Скачивание запрещено/129'},
    '/hilda_special2': {'video_path': 'C:/pythonProject1/Marksman/Hilda_special2.mp4', 'price': None, 'link': '@dikayl'},
    '/hilda_special': {'video_path': 'C:/pythonProject1/Marksman/Hilda_special.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['hilda'])
def show_hilda(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Hilda_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Hilda_list.keys())
def send_hilda_video(message):
    command = message.text.strip().lower()
    model_info = Hilda_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Guinevere_list = {
    '/guinevere_base': {'video_path': 'C:/pythonProject1/Marksman/Guinevere_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/120'},
    '/guinevere_epic': {'video_path': 'C:/pythonProject1/Marksman/Guinevere_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/guinevere_legend': {'video_path': 'C:/pythonProject1/Marksman/Guinevere_legend.mp4', 'price': 210, 'link': 'Скачивание запрещено/121'},
    '/guinevere_special': {'video_path': 'C:/pythonProject1/Marksman/Guinevere_special.mp4', 'price': 210, 'link': 'Скачивание запрещено/122'},
    '/guinevere_summer': {'video_path': 'C:/pythonProject1/Marksman/Guinevere_summer.mp4', 'price': None, 'link': '@dikayl'},
    '/guinevere_star': {'video_path': 'C:/pythonProject1/Marksman/Guinevere_star.mp4', 'price': None, 'link': '@dikayl'},
    '/guinevere_special2': {'video_path': 'C:/pythonProject1/Marksman/Guinevere_special2.mp4', 'price': 230, 'link': 'Скачивание запрещено/123'},
    '/guinevere_fighters1': {'video_path': 'C:/pythonProject1/Marksman/fighters_1.mp4', 'price': 350, 'link': 'Скачивание запрещено/124'},
    '/guinevere_fighters2': {'video_path': 'C:/pythonProject1/Marksman/fighters_2.mp4', 'price': 350, 'link': 'Скачивание запрещено/125'},
    '/guinevere_fighters3': {'video_path': 'C:/pythonProject1/Marksman/fighters_3.mp4', 'price': None, 'link': '@dikayl'},
    '/guinevere_elite': {'video_path': 'C:/pythonProject1/Marksman/guinevere_elite.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['guinevere'])
def show_guinevere(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Guinevere_list)])
    bot.send_message(message.chat.id, fighters_menu)


@bot.message_handler(func=lambda message: message.text.lower() in Guinevere_list.keys())
def send_guinevere_video(message):
    command = message.text.strip().lower()
    model_info = Guinevere_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


# Define the callback handler for the "Buy" button
@bot.callback_query_handler(func=lambda call: call.data.startswith("Buy_guinevere"))
def Buy_guinevere_callback(call):
    user_id = call.from_user.id
    user_data = db.get_user_data(user_id)
    if user_data is None:
        bot.send_message(user_id, "Write me bro -> @dikayl.")
        return

    model_name = call.data[14:]  # Remove the 'Buy_guinevere' prefix from callback_data
    model_info = Guinevere_list.get(f'/{model_name}')
    if model_info is None:
        bot.send_message(user_id, "Write me bro -> @dikayl")
        return




Dyrroth_list = {
    '/dyrroth_base': {'video_path': 'C:/pythonProject1/Marksman/Dyrroth_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/117'},
    '/dyrroth_collector': {'video_path': 'C:/pythonProject1/Marksman/Dyrroth_collector.mp4', 'price': 360, 'link': 'Скачивание запрещено/118'},
    '/dyrroth_star': {'video_path': 'C:/pythonProject1/Marksman/Dyrroth_star.mp4', 'price': 270, 'link': 'Скачивание запрещено/119'},
    '/dyrroth_venom': {'video_path': 'C:/pythonProject1/Marksman/Dyrroth_venom.mp4', 'price': None, 'link': '@dikayl'},
    '/dyrroth_limited1': {'video_path': 'C:/pythonProject1/Marksman/limited_1.mp4', 'price': None, 'link': '@dikayl'},
    '/dyrroth_limited2': {'video_path': 'C:/pythonProject1/Marksman/limited_2.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['dyrroth'])
def show_dyrroth(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Dyrroth_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Dyrroth_list.keys())
def send_dyrroth_video(message):
    command = message.text.strip().lower()
    model_info = Dyrroth_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Chou_list = {
    '/chou_basic': {'video_path': 'C:/pythonProject1/Marksman/Chou_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/111'},
    '/chou_star': {'video_path': 'C:/pythonProject1/Marksman/Chou_star.mp4', 'price': 210, 'link': 'Скачивание запрещено/112'},
    '/chou_special': {'video_path': 'C:/pythonProject1/Marksman/Chou_special.mp4', 'price': 230, 'link': 'Скачивание запрещено/113'},
    '/chou_hiphop': {'video_path': 'C:/pythonProject1/Marksman/Chou_hiphop.mp4', 'price': 210, 'link': 'Скачивание запрещено/114'},
    '/chou_fighters': {'video_path': 'C:/pythonProject1/Marksman/Chou_fighters.mp4', 'price': None, 'link': '@dikayl'},
    '/chou_epic': {'video_path': 'C:/pythonProject1/Marksman/Chou_epic.mp4', 'price': 230, 'link': 'Скачивание запрещено/115'},
    '/chou_elite': {'video_path': 'C:/pythonProject1/Marksman/Chou_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/116'},
    '/chou_dawning': {'video_path': 'C:/pythonProject1/Marksman/Chou_dawning.mp4', 'price': None, 'link': '@dikayl'},
    '/chou_stun3': {'video_path': 'C:/pythonProject1/Marksman/stun_3.mp4', 'price': None, 'link': '@dikayl'},
    '/chou_stun4': {'video_path': 'C:/pythonProject1/Marksman/STUN_4.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['chou'])
def show_chou(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Chou_list)])
    bot.send_message(message.chat.id, fighters_menu)


@bot.message_handler(func=lambda message: message.text.lower() in Chou_list.keys())
def send_chou_video(message):
    command = message.text.strip().lower()
    model_info = Chou_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


# Define the callback handler for the "Buy" button
@bot.callback_query_handler(func=lambda call: call.data.startswith("Buy_chou"))
def Buy_chou_callback(call):
    user_id = call.from_user.id
    user_data = db.get_user_data(user_id)
    if user_data is None:
        bot.send_message(user_id, "Write me bro -> @dikayl.")
        return

    model_name = call.data[9:]  # Remove the 'Buy_chou' prefix from callback_data
    model_info = Chou_list.get(f'/{model_name}')
    if model_info is None:
        bot.send_message(user_id, "Write me bro -> @dikayl")
        return

    model_

    if model_price is not None:
        if user_data['diamonds'] >= model_price:
            user_data['diamonds'] -= model_price
            bot.send_message(user_id, f"Вы успешно приобрели {model_name} модель.")
            # Replace the link with the actual link for the purchased model
            bot.send_message(user_id, model_info['link'])
            db.insert_user_data(user_id, user_data['diamonds'], str(user_data['printers']), str(user_data['models']), str(user_data['printed_models']))
        else:
            bot.send_message(user_id, "Write me bro -> @dikayl")
    #bot.send_message(user_id, "write me bro @dikayl")



Badang_list = {
    '/badang_base': {'video_path': 'C:/pythonProject1/Marksman/Badang_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/108'},
    '/badang_collector': {'video_path': 'C:/pythonProject1/Marksman/Badang_collector.mp4', 'price': None, 'link': '@dikayl'},
    '/badang_saint': {'video_path': 'C:/pythonProject1/Marksman/Badang_saint.mp4', 'price': 210, 'link': 'Скачивание запрещено/109'},
    '/badang_special': {'video_path': 'C:/pythonProject1/Marksman/Badang_special.mp4', 'price': 220, 'link': 'Скачивание запрещено/110'},
}


@bot.message_handler(commands=['badang'])
def show_badang(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Badang_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Badang_list.keys())
def send_badang_video(message):
    command = message.text.strip().lower()
    model_info = Badang_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Aulus_list = {
    '/aulus_basic': {'video_path': 'C:/pythonProject1/Marksman/Aulus_basic.mp4', 'price': 190, 'link': 'Скачивание запрещено/107'},
    '/aulus_elite': {'video_path': 'C:/pythonProject1/Marksman/Aulus_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/aulus_special': {'video_path': 'C:/pythonProject1/Marksman/Aulus_special.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['aulus'])
def show_aulus(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Aulus_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Aulus_list.keys())
def send_aulus_video(message):
    command = message.text.strip().lower()
    model_info = Aulus_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Arlott_list = {
    '/arlott_base': {'video_path': 'C:/pythonProject1/Marksman/Arlott_base.mp4', 'price': 210, 'link': 'Скачивание запрещено/106'},
}

@bot.message_handler(commands=['arlott'])
def show_arlott(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Arlott_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Arlott_list.keys())
def send_arlott_video(message):
    command = message.text.strip().lower()
    model_info = Arlott_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)




Freya_list = {
    '/freya_base': {'video_path': 'C:/pythonProject1/Marksman/Freya_base.mp4', 'price': 190, 'link': 'www.com.ua'},
    '/freya_base2': {'video_path': 'C:/pythonProject1/Marksman/Freya_base2.mp4', 'price': 210, 'link': '@dikayl'},
    '/freya_star': {'video_path': 'C:/pythonProject1/Marksman/Freya_star.mp4', 'price': 230, 'link': 'www.com.ua2'},
    '/freya_christmass': {'video_path': 'C:/pythonProject1/Marksman/Freya_christmass.mp4', 'price': 250, 'link': 'www.com.ua3'},
    '/freya_elite': {'video_path': 'C:/pythonProject1/Marksman/Freya_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/freya_epic': {'video_path': 'C:/pythonProject1/Marksman/Freya_epic.mp4', 'price': None, 'link': '@dikayl'},
    '/freya_epic2': {'video_path': 'C:/pythonProject1/Marksman/Freya_epic2.mp4', 'price': None, 'link': '@dikayl'},
    '/freya_saber': {'video_path': 'C:/pythonProject1/Marksman/Freya_saber.mp4', 'price': None, 'link': '@dikayl'},
    '/freuya_legend': {'video_path': 'C:/pythonProject1/Marksman/freuya_legend.mp4', 'price': None, 'link': '@dikayl'},
}


@bot.message_handler(commands=['freya'])
def show_freya(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Freya_list)])
    bot.send_message(message.chat.id, fighters_menu)


@bot.message_handler(func=lambda message: message.text.lower() in Freya_list.keys())
def send_freya_video(message):
    command = message.text.strip().lower()
    model_info = Freya_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


# Define the callback handler for the "Buy" button
@bot.callback_query_handler(func=lambda call: call.data.startswith("Buy_freya"))
def Buy_freya_callback(call):
    user_id = call.from_user.id
    user_data = db.get_user_data(user_id)
    if user_data is None:
        bot.send_message(user_id, "Write me bro -> @dikayl.")
        return

    model_name = call.data[10:]  # Remove the 'Buy_freya' prefix from callback_data
    model_info = Freya_list.get(f'/{model_name}')
    if model_info is None:
        bot.send_message(user_id, "Write me bro -> @dikayl")
        return

    model_

    if model_price is not None:
        if user_data['diamonds'] >= model_price:
            user_data['diamonds'] -= model_price
            bot.send_message(user_id, f"Вы успешно приобрели {model_name} модель.")
            # Replace the link with the actual link for the purchased model
            bot.send_message(user_id, model_info['link'])
            db.insert_user_data(user_id, user_data['diamonds'], str(user_data['printers']), str(user_data['models']), str(user_data['printed_models']))
        else:
            bot.send_message(user_id, "Write me bro -> @dikayl")
    #bot.send_message(user_id, "write me bro @dikayl")



Aldous_list = {
    '/aldous_base': {'video_path': 'C:/pythonProject1/Marksman/Aldous_base.mp4', 'price': 180, 'link': 'Скачивание запрещено/98'},
    '/aldous_elite': {'video_path': 'C:/pythonProject1/Marksman/Aldous_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/99'},
    '/aldous_m1': {'video_path': 'C:/pythonProject1/Marksman/Aldous_m1.mp4', 'price': None, 'link': '@dikayl'},
    '/aldous_transformer': {'video_path': 'C:/pythonProject1/Marksman/Aldous_transformer.mp4', 'price': 190, 'link': 'Скачивание запрещено/100'},
    '/aldous_collector': {'video_path': 'C:/pythonProject1/Marksman/Aldous_collector.mp4', 'price': 230, 'link': 'Скачивание запрещено/101'},
    '/aldous_star': {'video_path': 'C:/pythonProject1/Marksman/Aldous_star.mp4', 'price': 190, 'link': 'Скачивание запрещено/102'},
    '/aldous_blazing': {'video_path': 'C:/pythonProject1/Marksman/Aldous_blazing.mp4', 'price': None, 'link': '@dikayl'}
}

@bot.message_handler(commands=['aldous'])
def show_aldous(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Aldous_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Aldous_list.keys())
def send_aldous_video(message):
    command = message.text.strip().lower()
    model_info = Aldous_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)

Bane_list = {
    '/bane_basic': {'video_path': 'C:/pythonProject1/Marksman/Bane_basic.mp4', 'price': 180, 'link': 'Скачивание запрещено/93'},
    '/bane_basic2': {'video_path': 'C:/pythonProject1/Marksman/Bane_basic2.mp4', 'price': 180, 'link': 'Скачивание запрещено/94'},
    '/bane_elite': {'video_path': 'C:/pythonProject1/Marksman/Bane_elite.mp4', 'price': None, 'link': '@dikayl'},
    '/bane_epic': {'video_path': 'C:/pythonProject1/Marksman/Bane_epic.mp4', 'price': 280, 'link': 'Скачивание запрещено/95'},
    '/bane_epic2': {'video_path': 'C:/pythonProject1/Marksman/Bane_epic2.mp4', 'price': None, 'link': '@dikayl'},
    '/bane_basic': {'video_path': 'C:/pythonProject1/Marksman/Bane_basic.mp4', 'price': None, 'link': '@dikayl'}
}


@bot.message_handler(commands=['bane'])
def show_bane(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Bane_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Bane_list.keys())
def send_bane_video(message):
    command = message.text.strip().lower()
    model_info = Bane_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Balmond_list = {
    '/balmond_basic': {'video_path': 'C:/pythonProject1/Marksman/Balmond_basic.mp4', 'price': None, 'link': '@dikayl'},
    '/balmond_collector': {'video_path': 'C:/pythonProject1/Marksman/Balmond_collector.mp4', 'price': 210, 'link': 'Скачивание запрещено/89'},
    '/balmond_elite': {'video_path': 'C:/pythonProject1/Marksman/Balmond_elite.mp4', 'price': 210, 'link': 'Скачивание запрещено/90'},
    '/balmond_elite2': {'video_path': 'C:/pythonProject1/Marksman/Balmond_elite2.mp4', 'price': 210, 'link': 'Скачивание запрещено/91'},
    '/balmond_special': {'video_path': 'C:/pythonProject1/Marksman/Balmond_special.mp4', 'price': None, 'link': '@dikayl'},
    '/balmond_special2': {'video_path': 'C:/pythonProject1/Marksman/Balmond_special2.mp4', 'price': 350, 'link': 'Скачивание запрещено/92'},
}


@bot.message_handler(commands=['balmond'])
def show_balmond(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Balmond_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Balmond_list.keys())
def send_balmond_video(message):
    command = message.text.strip().lower()
    model_info = Balmond_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)


Argus_list = {
    '/argus_base': {'video_path': 'C:/pythonProject1/Marksman/Argus_base.mp4', 'price': 190, 'link': 'Скачивание запрещено/103'},
    '/argus_elite': {'video_path': 'C:/pythonProject1/Marksman/Argus_elite.mp4', 'price': 190, 'link': 'Скачивание запрещено/104'},
    '/argus_star': {'video_path': 'C:/pythonProject1/Marksman/Argus_star.mp4', 'price': None, 'link': '@dikayl'},
    '/argus_s27': {'video_path': 'C:/pythonProject1/Marksman/Argus_s27.mp4', 'price': None, 'link': '@dikayl'},
    '/argus_starwars': {'video_path': 'C:/pythonProject1/Marksman/Argus_starwars.mp4', 'price': 222, 'link': 'Скачивание запрещено/105'},
}


@bot.message_handler(commands=['argus'])
def show_argus(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Argus_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Argus_list.keys())
def send_argus_video(message):
    command = message.text.strip().lower()
    model_info = Argus_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)



Alpha_list = {
    '/alpha_basic': {'video_path': 'C:/pythonProject1/Marksman/Alpha_basic.mp4', 'price': None, 'link': '@dikayl'},
    '/alpha_epic': {'video_path': 'C:/pythonProject1/Marksman/Alpha_epic.mp4', 'price': 210, 'link': 'Скачивание запрещено/96'},
    '/alpha_s6': {'video_path': 'C:/pythonProject1/Marksman/Alpha_s6.mp4', 'price': 200, 'link': 'Скачивание запрещено/97'},
    '/alpha_abbys': {'video_path': 'C:/pythonProject1/Marksman/alpha_abbys.mp4', 'price': 200, 'link': 'Скачивание запрещено/97'},
    '/alpha_star': {'video_path': 'C:/pythonProject1/Marksman/alpha_star.mp4', 'price': 200, 'link': 'Скачивание запрещено/97'},
    '/alpha_special': {'video_path': 'C:/pythonProject1/Marksman/alpha_special.mp4', 'price': 200, 'link': 'Скачивание запрещено/97'},
}


@bot.message_handler(commands=['alpha'])
def show_alpha(message):
    fighters_menu = "\n".join([f"{i+1}) {fighter}" for i, fighter in enumerate(Alpha_list)])
    bot.send_message(message.chat.id, fighters_menu)

@bot.message_handler(func=lambda message: message.text.lower() in Alpha_list.keys())
def send_alpha_video(message):
    command = message.text.strip().lower()
    model_info = Alpha_list.get(command)
    bot.send_message(message.chat.id, "Загрузка... ")

    if model_info is None:
        bot.reply_to(message, "Invalid command. Please use one of the provided commands.")
        return

    video_path = model_info['video_path']
    

    if not os.path.exists(video_path):
        bot.reply_to(message, "К сожалению, видеофайл не был найден.")
        return

    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)

    # Блок для отправки инлайн-кнопки "Заказать модель"
    markup = types.InlineKeyboardMarkup()
    order_button = types.InlineKeyboardButton(text="Заказать модель", callback_data="order_model")
    markup.add(order_button)
    bot.send_message(message.chat.id, "Получить модель", reply_markup=markup)





models = [
    {'name': 'Random file.stl', 'price': 10},
    {'name': 'Фигурка Гаррош', 'price': 25},  # Добавляем фигурку Гаррош
    {'name': 'Фигурка на заказ', 'price': 30},  # Добавляем фигурку на заказ
    {'name': 'Фигурка из warcraft', 'price': 15},
    {'name': 'Модель 3', 'price': 8},
    {'name': 'Модель 4', 'price': 12},
    {'name': 'Модель 5', 'price': 22}
]

printers = [
    {'name': 'Anycubic', 'price': 90, 'print_speed': 10}
]

first_model = False



Model_list = [
    'miya_base /miyab',
    'cloud_base',
    'fanny_base',
    'alucard_base'
]


site_models = [
    'miya_base: https://site1.com',
    'cloud_base: https://site2.com',
    'fanny_base: https://site3.com',
    'alucard_base: https://site4.com'
]

model_prices = {
    'miya_base': 20,
    'cloud_base': 30,
    'fanny_base': 40,
    'alucard_base': 180,
    'alucard_epic': 190
}

@bot.message_handler(commands=['models'])
def show_models_menu(message):
    models_menu = "\n".join(Model_list)
    bot.send_message(message.chat.id, f"Меню моделей:\n{models_menu}")



def generate_main_menu():
    """
    Формирует главное меню пользователя. Удалены пункты, связанные с мини‑играми,
    обменом алмазов и инвестициями. При необходимости сюда можно добавить
    другие рабочие разделы.
    """
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton('Menu'))
    return markup

def generate_print_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton('Купить 3D принтер'))
    markup.add(types.KeyboardButton('Напечатать 3D модель'))
    markup.add(types.KeyboardButton('Продать модель💸'))
    markup.add(types.KeyboardButton('Назад в меню'))
    return markup

def generate_earn_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton('Игра в кости🎲'))
    markup.add(types.KeyboardButton('Игра в баскетбол🏀'))
    markup.add(types.KeyboardButton('Игра в футбол⚽'))
    markup.add(types.KeyboardButton('Назад в меню'))
    return markup


# Обработчик для кнопки "Инвестировать💎"
@bot.message_handler(func=lambda message: message.text == 'Инвестировать💎')
def handle_invest(message):
    tech_menu = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    tech_menu.add(types.KeyboardButton('Мой баланс 💎'), types.KeyboardButton('Инвестировать в BTC'),
                  types.KeyboardButton('Назад в меню'))

    bot.send_message(message.chat.id, "Выберите действие:", reply_markup=tech_menu)



# Функция для создания инлайн-меню
def create_technical_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_Buy_bitcoin = types.InlineKeyboardButton('Купить Биткоин', callback_data='Buy_bitcoin')
    btn_sell_bitcoin = types.InlineKeyboardButton('Продать Биткоин', callback_data='sell_bitcoin')
    btn_check_balance = types.InlineKeyboardButton('Мой баланс', callback_data='check_balance')
    btn_close_menu = types.InlineKeyboardButton('Закрыть меню', callback_data='close_menu')
    markup.add(btn_Buy_bitcoin, btn_sell_bitcoin, btn_check_balance, btn_close_menu)
    return markup

# Обработчик нажатия на кнопку "Инвестировать💎"
@bot.message_handler(func=lambda message: message.text == 'Инвестировать в BTC')
def handle_technical_button(message):
    # Отправляем инлайн-меню пользователю
    msg = bot.send_message(message.chat.id, 'Выберите действие:', reply_markup=create_technical_menu())

# Обработчик нажатия на инлайн-кнопку "Закрыть меню"
@bot.callback_query_handler(func=lambda call: call.data == 'close_menu')
def handle_close_menu(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # Удаляем инлайн-кнопки и сообщение "Выберите действие"
    bot.delete_message(chat_id, message_id)


# Обработчик нажатия на инлайн-кнопку "Купить Биткоин"
@bot.callback_query_handler(func=lambda call: call.data == 'Buy_bitcoin')
def handle_Buy_bitcoin(call):
    chat_id = call.message.chat.id

    # Получаем текущий курс биткоина из API
    try:
        response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT')
        bitcoin_price = float(response.json()['price'])
    except Exception as e:
        bitcoin_price = None

    if bitcoin_price is not None:
        user_id = call.from_user.id
        user_diamonds = get_user_diamonds(user_id)

        # Рассчитываем количество биткоинов, которое пользователь получит за обмен
        bitcoin_amount = user_diamonds / bitcoin_price

        # Обновляем сообщение с информацией о покупке биткоина и указываем пользователю ввести количество алмазов
        message_text = f"1💎 = 1 💵\n"
        message_text += f"Текущий курс биткоина: {bitcoin_price} USDT\n"
        message_text += f"У вас доступно: {user_diamonds}💎\n"
        message_text += f"Сколько алмазов хотите обменять? (Введите число)"
        bot.send_message(chat_id, message_text)

        # Устанавливаем состояние пользователя для ожидания количества алмазов для обмена
        bot.register_next_step_handler(call.message, process_diamonds_for_bitcoin, bitcoin_price)
    else:
        bot.send_message(chat_id, "Не удалось получить текущий курс биткоина. Попробуйте позже.")

# Обработчик для обработки количества алмазов и выполнения обмена
def process_diamonds_for_bitcoin(message, bitcoin_price):
    chat_id = message.chat.id
    user_id = message.from_user.id

    try:
        diamonds_to_exchange = int(message.text)
        user_diamonds = get_user_diamonds(user_id)

        if diamonds_to_exchange <= user_diamonds:
            # Вычисляем количество биткоинов, которое пользователь получит
            bitcoin_amount = diamonds_to_exchange / bitcoin_price

            # Обновляем количество алмазов у пользователя
            new_diamonds = user_diamonds - diamonds_to_exchange
            update_user_diamonds(user_id, new_diamonds)

            # Обновляем баланс биткоинов у пользователя
            user_bitcoin_balance = get_user_bitcoin_balance(user_id)
            new_bitcoin_balance = user_bitcoin_balance + bitcoin_amount
            update_user_bitcoin_balance(user_id, new_bitcoin_balance)

            bot.send_message(chat_id, f"Вы успешно обменяли {diamonds_to_exchange} алмазов на {bitcoin_amount:.8f} BTC.")
        else:
            bot.send_message(chat_id, "У вас недостаточно алмазов для обмена.")
    except ValueError:
        bot.send_message(chat_id, "Нажми на кнопку еще раз")


# Обработчик нажатия на инлайн-кнопку "Продать Биткоин"
@bot.callback_query_handler(func=lambda call: call.data == 'sell_bitcoin')
def handle_sell_bitcoin(call):
    chat_id = call.message.chat.id

    # Получаем текущий курс биткоина из API
    try:
        response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT')
        bitcoin_price = float(response.json()['price'])
    except Exception as e:
        bitcoin_price = None

    if bitcoin_price is not None:
        user_id = call.from_user.id
        user_bitcoin_balance = get_user_bitcoin_balance(user_id)  # Замените на функцию получения баланса биткоина

        # Создаем клавиатуру с дополнительной кнопкой "Продать все BTC"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Продать все BTC", callback_data="sell_all_bitcoin"))

        # Обновляем сообщение с информацией о продаже биткоина и клавиатурой
        message_text = f"1💎 = 1 💵\n"
        message_text += f"Текущий курс биткоина: {bitcoin_price} USDT\n"
        message_text += f"У вас доступно: {user_bitcoin_balance:.8f} BTC\n"
        message_text += f"Сколько биткоина вы хотите продать? (Введите число)"
        bot.send_message(chat_id, message_text, reply_markup=markup)

        # Устанавливаем состояние пользователя для ожидания количества биткоина для продажи
        bot.register_next_step_handler(call.message, process_bitcoin_for_diamonds, bitcoin_price)
    else:
        bot.send_message(chat_id, "Не удалось получить текущий курс биткоина. Попробуйте позже.")

# Обработчик нажатия на инлайн-кнопку "Продать все BTC"
@bot.callback_query_handler(func=lambda call: call.data == 'sell_all_bitcoin')
def handle_sell_all_bitcoin(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    # Получаем текущий курс биткоина из API
    try:
        response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT')
        bitcoin_price = float(response.json()['price'])
    except Exception as e:
        bitcoin_price = None

    if bitcoin_price is not None:
        user_bitcoin_balance = get_user_bitcoin_balance(user_id)  # Замените на функцию получения баланса биткоина

        if user_bitcoin_balance > 0:
            # Вычисляем количество алмазов, которое пользователь получит за продажу всех биткоинов
            diamonds_to_receive = user_bitcoin_balance * bitcoin_price

            # Обновляем баланс биткоина и количество алмазов у пользователя
            new_bitcoin_balance = 0
            update_user_bitcoin_balance(user_id, new_bitcoin_balance)  # Замените на функцию обновления баланса биткоина
            user_diamonds = get_user_diamonds(user_id)
            new_diamonds = user_diamonds + diamonds_to_receive
            update_user_diamonds(user_id, new_diamonds)

            bot.send_message(chat_id, f"Вы успешно продали все BTC за {diamonds_to_receive}💎.")
        else:
            bot.send_message(chat_id, "У вас нет доступных BTC для продажи.")
    else:
        bot.send_message(chat_id, "Не удалось получить текущий курс биткоина. Попробуйте позже.")
# Обработчик для обработки количества биткоина и выполнения обмена
def process_bitcoin_for_diamonds(message, bitcoin_price):
    chat_id = message.chat.id
    user_id = message.from_user.id

    try:
        bitcoin_to_sell = float(message.text)
        user_bitcoin_balance = get_user_bitcoin_balance(user_id)  # Замените на функцию получения баланса биткоина

        if bitcoin_to_sell > user_bitcoin_balance:
            bot.send_message(chat_id, "У вас недостаточно биткоина для продажи.")
        elif bitcoin_to_sell <= 0:
            bot.send_message(chat_id, "Нажми на кнопку еще раз")
        else:
            # Вычисляем количество алмазов, которое пользователь получит за продажу биткоина
            diamonds_to_receive = bitcoin_to_sell * bitcoin_price

            # Обновляем баланс биткоина у пользователя
            new_bitcoin_balance = user_bitcoin_balance - bitcoin_to_sell
            update_user_bitcoin_balance(user_id, new_bitcoin_balance)  # Замените на функцию обновления баланса биткоина

            # Обновляем количество алмазов у пользователя
            user_diamonds = get_user_diamonds(user_id)
            new_diamonds = user_diamonds + diamonds_to_receive
            update_user_diamonds(user_id, new_diamonds)

            bot.send_message(chat_id, f"Вы успешно продали {bitcoin_to_sell:.8f} BTC за {diamonds_to_receive} алмазов.")
    except ValueError:
        bot.send_message(chat_id, "Нажми на кнопку еще раз")


# Обработчик нажатия на инлайн-кнопку "Мой баланс"
@bot.callback_query_handler(func=lambda call: call.data == 'check_balance')
def handle_check_balance(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    # Получаем текущий курс биткоина из API
    try:
        response = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT')
        bitcoin_price = float(response.json()['price'])
    except Exception as e:
        bitcoin_price = None

    if bitcoin_price is not None:
        user_bitcoin_balance = get_user_bitcoin_balance(user_id)  # Замените на функцию получения баланса биткоина
        user_diamonds = get_user_diamonds(user_id)  # Замените на функцию получения количества алмазов

        message_text = f"""Текущий курс биткоина: {bitcoin_price} USDT
        У вас доступно: {user_bitcoin_balance:.8f} BTC
        ({user_bitcoin_balance * bitcoin_price:.2f}💎 по текущему курсу)"""

        bot.send_message(chat_id, message_text)
    else:
        bot.send_message(chat_id, "Не удалось получить текущий курс биткоина. Попробуйте позже.")


@bot.message_handler(func=lambda message: message.text == 'Мини-игры💎')
def handle_earn_button(message):
    earn_markup = generate_earn_menu()
    bot.send_message(message.chat.id, 'Будь осторожен, играй с умом', reply_markup=earn_markup)

@bot.message_handler(func=lambda message: message.text == '3D принтер🖨')
def handle_print_button(message):
    earn_markup = generate_print_menu()
    bot.send_message(message.chat.id, 'Печатай фигурки и зарабатывай:)', reply_markup=earn_markup)

def generate_business_stats_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton('3D каталог моделей'))
    markup.add(types.KeyboardButton('Назад в меню'))
    return markup

# Кнопки для игры в баскетбол
play_button = types.InlineKeyboardButton("Играть в баскетбол🏀", callback_data="play_basketball")
exit_button = types.InlineKeyboardButton("Выйти в меню", callback_data="exit")

@bot.message_handler(func=lambda message: message.text == 'Игра в баскетбол🏀')
def start_playing_basketball(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(play_button, exit_button)

    bot.send_message(user_id, "🏀 Игра в баскетбол 🏀\n\n"
                              "Вы соревнуетесь с ботом в игре в баскетбол! Забейте мяч в кольцо и выиграйте!\n\n"
                              "Сумма ставки: от 1💎 до 1000💎\n"
                              "Коэффициент выигрыша: x2",
                     reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "play_basketball")
def play_basketball_callback(call):
    user_id = call.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data:
        bot.send_message(user_id, 'Произошла ошибка при получении информации о пользователе.')
        return

    user_diamonds = user_data['diamonds']

    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(user_id, f"Ваш текущий баланс: {user_diamonds} 💎\n"
                              f"Введите сумму ставки 👇:", reply_markup=markup)
    bot.register_next_step_handler(call.message, process_basketball_bet_input)

def process_basketball_bet_input(message):
    user_id = message.from_user.id
    bet_amount = message.text

    if not bet_amount.isdigit():
        bot.send_message(user_id, "Пожалуйста, введите числовое значение.")
        return

    bet_amount = int(bet_amount)
    user_data = db.get_user_data(user_id)

    if not user_data:
        bot.send_message(user_id, 'Произошла ошибка при получении информации о пользователе.')
        return

    user_diamonds = user_data['diamonds']

    if bet_amount <= 0 or bet_amount > 1000 or bet_amount > user_diamonds:
        bot.send_message(user_id, f"Сумма ставки должна быть от 1 до {min(1000, user_diamonds)} алмазов.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    play_button = types.InlineKeyboardButton("Бросить мяч", callback_data=f"throw_{bet_amount}")
    exit_button = types.InlineKeyboardButton("Выйти в меню", callback_data="exit")
    markup.add(play_button, exit_button)

    bot.send_message(user_id, f"Вы выбрали ставку: {bet_amount} 💎. Бросаем мяч?", reply_markup=markup)

# Обработка коллбэков от кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('throw_') or call.data == 'play_againb')
def handle_throw(call):
    user_id = call.from_user.id

    if call.data == 'play_againb':
        markup = types.ReplyKeyboardRemove(selective=False)
        bot.send_message(user_id, "Введите сумму ставки 👇:", reply_markup=markup)
        bot.register_next_step_handler(call.message, process_basketball_bet_input)
        return

    bet_amount = int(call.data.split('_')[1])

    user_data = db.get_user_data(user_id)

    if not user_data:
        bot.send_message(user_id, 'Произошла ошибка при получении информации о пользователе.')
        return

    user_diamonds = user_data['diamonds']

    if user_diamonds < bet_amount:
        bot.send_message(user_id, "Недостаточно алмазов для ставки.")
        return

    bot.send_message(user_id, "🏀 Бот бросает мяч...", reply_markup=types.ReplyKeyboardRemove())

    bot_throw = random.randint(1, 2)
    bot_throw_sticker = {
        1: "CAACAgIAAxkBAAEKLbdk8GFYfLjMpT8_ecczi8XmIgzqMgACWQQCAAFji0YMwCIz_zSpTHkwBA",
        2: "CAACAgIAAxkBAAEKLbVk8GFMQtMm-LiyzWda-v1x00wZuQACVgQCAAFji0YM2aLIfdfeRH0wBA"
    }

    bot.send_sticker(user_id, bot_throw_sticker[bot_throw])
    time.sleep(3)  # Подождать 3 секунды

    user_throw = random.randint(1, 2)
    user_throw_sticker = {
        1: "CAACAgIAAxkBAAEKLbNk8GE8C3Oc1Blux-dC9dm8E6JhxwACWAQCAAFji0YMGj-bQIU9fHgwBA",
        2: "CAACAgIAAxkBAAEKLa9k8GEcO45-Bt8rt083ZGXewnQKBQACWgQCAAFji0YMFd5S-a1aadkwBA"
    }

    bot.send_message(user_id, "🏀 Вы бросаете мяч...", reply_markup=types.ReplyKeyboardRemove())
    bot.send_sticker(user_id, user_throw_sticker[user_throw])
    time.sleep(3)  # Подождать 3 секунды

    winnings = 0  # Инициализация переменной выигрыша
    if user_throw == 1 and bot_throw == 2:
        winnings = bet_amount
        result_text = f"🏀 Ваш бросок: {'Забросили'}\n🏀 Бросок бота: {'Промахнули'}\n\n✅ Поздравляем! Вы победили, и ваш выигрыш составляет {winnings} 💎"
    elif user_throw == 2 and bot_throw == 1:
        winnings = -bet_amount
        result_text = f"🏀 Ваш бросок: {'Промахнули'}\n🏀 Бросок бота: {'Забросили'}\n\n❌ К сожалению, вы проиграли. Ваш проигрыш составляет {bet_amount} 💎"
    else:
        winnings = 0
        result_text = f"🏀 Ваш бросок: {'Промахнули' if user_throw == 2 else 'Забросили'}\n🏀 Бросок бота: {'Промахнули' if bot_throw == 2 else 'Забросили'}\n\n🤝 Ничья! Ваши ставки возвращены вам."

    new_diamonds = user_diamonds + winnings
    db.update_user_diamonds(user_id, new_diamonds)

    markup = types.InlineKeyboardMarkup(row_width=1)
    play_again_button = types.InlineKeyboardButton("Сыграть еще", callback_data="play_againb")
    exit_to_menu_button = types.InlineKeyboardButton("Вернуться в меню", callback_data="exit")
    markup.add(play_again_button, exit_to_menu_button)

    bot.send_message(user_id, result_text, reply_markup=markup)
    bot.send_message(user_id, f"Ваш новый баланс: {new_diamonds} 💎")



# Кнопки для игры в футбол
play_football_button = types.InlineKeyboardButton("Играть в футбол⚽", callback_data="play_football")



@bot.message_handler(func=lambda message: message.text == 'Игра в футбол⚽')
def start_playing_football(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(play_football_button, exit_button)

    bot.send_message(user_id, "⚽ Игра в футбол ⚽\n\n"
                              "Вы соревнуетесь с ботом в игре в футбол! Забейте гол и выиграйте!\n\n"
                              "Сумма ставки: от 1💎 до 1000💎\n"
                              "Коэффициент выигрыша: x2",
                     reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "play_football")
def play_football_callback(call):
    user_id = call.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data:
        bot.send_message(user_id, 'Произошла ошибка при получении информации о пользователе.')
        return

    user_diamonds = user_data['diamonds']

    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(user_id, f"Ваш текущий баланс: {user_diamonds} 💎\n"
                              f"Введите сумму ставки 👇:", reply_markup=markup)
    bot.register_next_step_handler(call.message, process_football_bet_input)

def process_football_bet_input(message):
    user_id = message.from_user.id
    bet_amount = message.text

    if not bet_amount.isdigit():
        bot.send_message(user_id, "Пожалуйста, введите числовое значение.")
        return

    bet_amount = int(bet_amount)
    user_data = db.get_user_data(user_id)

    if not user_data:
        bot.send_message(user_id, 'Произошла ошибка при получении информации о пользователе.')
        return

    user_diamonds = user_data['diamonds']

    if bet_amount <= 0 or bet_amount > 1000 or bet_amount > user_diamonds:
        bot.send_message(user_id, f"Сумма ставки должна быть от 1 до {min(1000, user_diamonds)} алмазов.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    play_button = types.InlineKeyboardButton("Ударить мяч", callback_data=f"kick_{bet_amount}")
    exit_button = types.InlineKeyboardButton("Выйти в меню", callback_data="exit")
    markup.add(play_button, exit_button)

    bot.send_message(user_id, f"Вы выбрали ставку: {bet_amount} 💎. Ударяем мяч?", reply_markup=markup)

# Обработка коллбэков от кнопок
@bot.callback_query_handler(func=lambda call: call.data.startswith('kick_') or call.data == 'play_againf')
def handle_kick(call):
    user_id = call.from_user.id

    if call.data == 'play_againf':
        markup = types.ReplyKeyboardRemove(selective=False)
        bot.send_message(user_id, "Введите сумму ставки 👇:", reply_markup=markup)
        bot.register_next_step_handler(call.message, process_football_bet_input)
        return

    bet_amount = int(call.data.split('_')[1])

    user_data = db.get_user_data(user_id)

    if not user_data:
        bot.send_message(user_id, 'Произошла ошибка при получении информации о пользователе.')
        return

    user_diamonds = user_data['diamonds']

    if user_diamonds < bet_amount:
        bot.send_message(user_id, "Недостаточно алмазов для ставки.")
        return

    bot.send_message(user_id, "⚽️ Бот бьет по мячу...", reply_markup=types.ReplyKeyboardRemove())

    bot_kick = random.randint(1, 2)
    bot_kick_sticker = {
        1: "CAACAgIAAxkBAAEKLatk8FoTa0jU_npQUsJhFg6iJ5UaFwACqiQCAAFji0YMZPMcKAKmcWUwBA",
        2: "CAACAgIAAxkBAAEKLadk8Fn029-OUHTIh0KzXPdR4TH2-AACqCQCAAFji0YM8_Ro6iDiPDkwBA"
    }

    bot.send_sticker(user_id, bot_kick_sticker[bot_kick])
    time.sleep(3)  # Подождать 3 секунды

    user_kick = random.randint(1, 2)
    user_kick_sticker = {
        1: "CAACAgIAAxkBAAEKLa1k8FpxWWOq3qg0PQ2jAAFmCI9ZrpIAAqskAgABY4tGDDotLSIztUJNMAQ",
        2: "CAACAgIAAxkBAAEKLaVk8FnYU4cGtvWakNrEiR6Qmg9G-wACpiQCAAFji0YMdECRufFjw88wBA"
    }

    bot.send_message(user_id, "⚽️ Вы бьете по мячу...", reply_markup=types.ReplyKeyboardRemove())
    bot.send_sticker(user_id, user_kick_sticker[user_kick])
    time.sleep(3)  # Подождать 3 секунды

    winnings = 0  # Инициализация переменной выигрыша
    if user_kick == 1 and bot_kick == 2:
        winnings = bet_amount
        result_text = f"⚽ Ваш удар: {'Забил гол'}\n⚽ Удар бота: {'Промахнулся'}\n\n✅ Поздравляем! Вы победили, и ваш выигрыш составляет {winnings} 💎"
    elif user_kick == 2 and bot_kick == 1:
        winnings = -bet_amount
        result_text = f"⚽ Ваш удар: {'Промахнулся'}\n⚽ Удар бота: {'Забил гол'}\n\n❌ К сожалению, вы проиграли. Ваш проигрыш составляет {bet_amount} 💎"
    else:
        winnings = 0
        result_text = f"⚽ Ваш удар: {'Промахнулся' if user_kick == 2 else 'Забил гол'}\n⚽ Удар бота: {'Промахнулся' if bot_kick == 2 else 'Забил гол'}\n\n🤝 Ничья! Ваши ставки возвращены вам."

    new_diamonds = user_diamonds + winnings
    db.update_user_diamonds(user_id, new_diamonds)

    markup = types.InlineKeyboardMarkup(row_width=1)
    play_again_button = types.InlineKeyboardButton("Сыграть еще", callback_data="play_againf")
    exit_to_menu_button = types.InlineKeyboardButton("Вернуться в меню", callback_data="exit")
    markup.add(play_again_button, exit_to_menu_button)

    bot.send_message(user_id, result_text, reply_markup=markup)
    bot.send_message(user_id, f"Ваш новый баланс: {new_diamonds} 💎")


@bot.callback_query_handler(func=lambda call: call.data == "exit")
def handle_exit(call):
    user_id = call.from_user.id
    markup = generate_earn_menu()  # Получаем клавиатуру меню
    bot.send_message(user_id, "Вы вернулись в меню.", reply_markup=markup)




@bot.callback_query_handler(func=lambda call: call.data == "exit")
def handle_exit_duplicate(call):
    """
    Дублирующий обработчик выхода был оставлен для совместимости, но ничего не делает.
    """
    return



# Обработчик команды "Игра в кости🎲":
@bot.message_handler(func=lambda message: message.text == 'Игра в кости🎲')
def start_playing(message):
    user_id = message.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    play_button = types.InlineKeyboardButton("Играть", callback_data="play")
    exit_button = types.InlineKeyboardButton("Выйти назад", callback_data="exit")
    markup.add(play_button, exit_button)

    bot.send_message(user_id, "🎲 [Кости] 🎲\n\n"
                              "Вы с ботом подбрасываете кубик, у кого выпадет большее число — тот и победил!\n\n"
                              "Сумма ставки: от 1💎 до 1000💎\n"
                              "Коэффициент выигрыша: x2",
                     reply_markup=markup, parse_mode='Markdown')


@bot.callback_query_handler(func=lambda call: call.data == "exit")
def exit_game_callback(call):
    user_id = call.from_user.id
    markup = generate_earn_menu()  # Получаем клавиатуру меню
    bot.send_message(user_id, "Вы вернулись в меню.", reply_markup=markup)


## Удалено: остатки кода мини-игр вне функции

## Удалено: обработчики мини-игр и алмазов

    if call.data == 'play_again':
        markup = types.ReplyKeyboardRemove(selective=False)
    # Удалено: остатки логики мини-игры с алмазами и ставками

@bot.callback_query_handler(func=lambda call: call.data == "exit")
def handle_exit(call):
    user_id = call.from_user.id
    markup = generate_earn_menu()  # Получаем клавиатуру меню
    bot.send_message(user_id, "Вы вернулись в меню.", reply_markup=markup)



def generate_investment_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton('100 💎 - Прибыль 22-35 💎', callback_data='invest_100'),
        types.InlineKeyboardButton('500 💎 - Прибыль 35-65 💎', callback_data='invest_500'),
        types.InlineKeyboardButton('1000 💎 - Прибыль 65-89 💎', callback_data='invest_1000'),
        types.InlineKeyboardButton('2000 💎 - Прибыль 89-148 💎', callback_data='invest_2000')
    )
    return markup

#@bot.message_handler(func=lambda message: message.text == 'Инвестировать📈')
def invest(message):
    user_id = message.from_user.id

    # Проверяем, есть ли у пользователя активная инвестиция
    if not db.has_active_investment(user_id):
        bot.send_message(user_id, 'Выберите сумму инвестиций 💎\nСрок инвестирования: 24 часа ⏰', reply_markup=generate_investment_menu())
    else:
        bot.send_message(user_id, 'У вас уже есть активная инвестиция. Пожалуйста, дождитесь ее завершения.')


def investment_completion(user_id, investment_amount):
    time.sleep(86290)  # Ждем определенное время (например, 5 секунд)

    return_amount = investment_amount + db.get_investment_income(investment_amount)
    db.add_returned_diamonds(user_id, return_amount)  # Добавляем возвращенные алмазы в баланс пользователя

    bot.send_message(user_id, f'Инвестирование завершено! Вам были выплачены проценты по депозиту.\n'
                              f'Вам возвращено {return_amount} 💎')

    db.remove_completed_investments(user_id)  # Удаляем запись об инвестировании из базы данных

    # Удалено: остатки логики инвестиций и вложенных блоков с return вне функции


def check_investment_completion():
    while True:
        active_investments = db.get_active_investments()  # Получаем информацию об активных инвестициях
        for investment in active_investments:
            user_id, investment_amount = investment
            investment_completion(user_id, investment_amount)  # Обрабатываем завершение инвестирования

        time.sleep(60)  # Проверяем каждую минуту


# Создаем и запускаем отдельный поток для проверки завершения инвестирования
investment_thread = threading.Thread(target=check_investment_completion)
investment_thread.start()




# Функция для генерации меню выбора игры
def generate_game_selection_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(types.KeyboardButton('Mobile Legends BB'))
    markup.add(types.KeyboardButton('World of Warcraft (в разработке)'))
    markup.add(types.KeyboardButton('Dota2'))
    markup.add(types.KeyboardButton('Brawl Stars'))
    markup.add(types.KeyboardButton('Где бесплатные модели?'))
    markup.add(types.KeyboardButton('Назад в меню'))
    return markup


# Обработчик для кнопки "3D каталог моделей"
@bot.message_handler(func=lambda message: message.text == '3D каталог моделей', content_types=['text'])
def game_selection(message):
    game_menu = generate_game_selection_menu()
    bot.send_message(message.chat.id, "3D каталог моделей:", reply_markup=game_menu)


# Обработчик для кнопок выбора игр
@bot.message_handler(func=lambda message: message.text in ['Mobile Legends BB', 'Brawl Stars', 'World of Warcraft', 'разработка...'], content_types=['text'])
def game_selected(message):
    selected_game = message.text

    if selected_game == 'Mobile Legends BB':
        model_menu = generate_model_options_menu()
        bot.send_message(message.chat.id, "Выберите модель для MLBB:", reply_markup=model_menu)
    elif selected_game == 'Brawl Stars':
        brawl_menu = generate_brawl_stars_menu()
        bot.send_message(message.chat.id, "Выберите опцию для Brawl Stars:", reply_markup=brawl_menu)
    elif selected_game == 'World of Warcraft':
        wow_menu = generate_wow_faction_menu()
        bot.send_message(message.chat.id, "Выберите фракцию для WoW:", reply_markup=wow_menu)
    elif selected_game == 'разработка...':
        # Добавьте свою логику для этой опции
        pass

# Функция для генерации меню выбора опций в игре Brawl Stars
def generate_brawl_stars_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(types.KeyboardButton('/barley'))
    markup.add(types.KeyboardButton('/brawler2'))
    markup.add(types.KeyboardButton('/brawler3'))
    markup.add(types.KeyboardButton('Назад в выбор игры'))
    return markup

# Список бравлеров с информацией
brawler_list = {
    '/barley': {
        'name': 'Барлей',
        'photo_path': 'C:/pythonProject1/brawl/barley.jpg',
        'link': 'https://disk.yandex.ru/d/HyHgUkwZDhQANQ'
    },
    '/biba': {
        'name': 'Биба',
        'photo_path': 'C:/pythonProject1/brawls/biba.jpg',
        'link': 'https://disk.yandex.ru/d/eCir-y3Aum5NOw'
    },
    '/bo': {
        'name': 'Бо',
        'photo_path': 'C:/pythonProject1/brawls/bo.jpg',
        'link': 'https://disk.yandex.ru/d/cs15J9xKzW55Sg'
    },
    '/brock': {
        'name': 'Брок',
        'photo_path': 'C:/pythonProject1/brawls/brock.jpg',
        'link': 'https://disk.yandex.ru/d/CX_BSkD82920Og'
    },
    '/bull': {
        'name': 'Булл',
        'photo_path': 'C:/pythonProject1/brawls/bull.jpg',
        'link': 'https://disk.yandex.ru/d/Z2B9xco3ND624Q'
    },
    '/darryl': {
        'name': 'Дэррил',
        'photo_path': 'C:/pythonProject1/brawls/darryl.jpg',
        'link': 'https://disk.yandex.ru/d/8S4OG2KjEs_Gyw'
    },
    '/jessie': {
        'name': 'Джесси',
        'photo_path': 'C:/pythonProject1/brawls/jessie.jpg',
        'link': 'https://disk.yandex.ru/d/v_1cPHAwYa2RGQ'
    },
    '/dynamike': {
        'name': 'Динамайк',
        'photo_path': 'C:/pythonProject1/brawls/dynamike.jpg',
        'link': 'https://disk.yandex.ru/d/ZSC75jOak6By7Q'
    },
    '/karl': {
        'name': 'Карл',
        'photo_path': 'C:/pythonProject1/brawls/karl.jpg',
        'link': 'https://disk.yandex.ru/d/9XXCGA3RUV6JTg'
    },
    '/colt': {
        'name': 'Кольт',
        'photo_path': 'C:/pythonProject1/brawls/colt.jpg',
        'link': 'https://disk.yandex.ru/d/-qgniFaRqbBefQ'
    },
    '/crow': {
        'name': 'Кроу',
        'photo_path': 'C:/pythonProject1/brawls/crow.jpg',
        'link': 'https://disk.yandex.ru/d/8VL_O0nsTuO_lg'
    },
    '/leon': {
        'name': 'Леон',
        'photo_path': 'C:/pythonProject1/brawls/leon.jpg',
        'link': 'https://disk.yandex.ru/d/3Ykh1VZgYGLZEw'
    },
    '/mimdera': {
        'name': 'Мимдера',
        'photo_path': 'C:/pythonProject1/brawls/mimdera.jpg',
        'link': 'https://disk.yandex.ru/d/LotwRfTo3ParCQ'
    },
    '/mortira': {
        'name': 'Мортира',
        'photo_path': 'C:/pythonProject1/brawls/mortira.jpg',
        'link': 'https://disk.yandex.ru/d/clVX1j-TIz1sUg'
    },
    '/mortis': {
        'name': 'Мортис',
        'photo_path': 'C:/pythonProject1/brawls/mortis.jpg',
        'link': 'https://disk.yandex.ru/d/busPi0cEpjaHcA'
    },
    '/nita': {
        'name': 'Нита',
        'photo_path': 'C:/pythonProject1/brawls/nita.jpg',
        'link': 'https://disk.yandex.ru/d/busPi0cEpjaHcA'
    },
    '/piper': {
        'name': 'Пайпер',
        'photo_path': 'C:/pythonProject1/brawls/piper.jpg',
        'link': 'https://disk.yandex.ru/d/zUNOpbJityzang'
    },
    '/penny': {
        'name': 'Пенни',
        'photo_path': 'C:/pythonProject1/brawls/penny.jpg',
        'link': 'https://disk.yandex.ru/d/cynAKQuKuphWvg'
    },
    '/poco': {
        'name': 'Поко',
        'photo_path': 'C:/pythonProject1/brawls/poco.jpg',
        'link': 'https://disk.yandex.ru/d/Ls5tWb2jADKHqA'
    },
    '/pam': {
        'name': 'Пэм',
        'photo_path': 'C:/pythonProject1/brawls/pam.jpg',
        'link': 'https://disk.yandex.ru/d/6OVrzP3r_e_KnQ'
    },
    '/rosa': {
        'name': 'Роза',
        'photo_path': 'C:/pythonProject1/brawls/rosa.jpg',
        'link': 'https://disk.yandex.ru/d/leuEN2EFwyjF9Q'
    },
    '/spike': {
        'name': 'Спайк',
        'photo_path': 'C:/pythonProject1/brawls/spike.jpg',
        'link': 'https://disk.yandex.ru/d/v0p_B4opNkeJFw'
    },
    '/tara': {
        'name': 'Тара',
        'photo_path': 'C:/pythonProject1/brawls/tara.jpg',
        'link': 'https://disk.yandex.ru/d/lildY1hj0N7egw'
    },
    '/frank': {
        'name': 'Фрэнк',
        'photo_path': 'C:/pythonProject1/brawls/frank.jpg',
        'link': 'https://disk.yandex.ru/d/lPPF0lKMX8LdwQ'
    },
    '/el_pedro': {
        'name': 'Эль Педро',
        'photo_path': 'C:/pythonProject1/brawls/el_pedro.jpg',
        'link': 'https://disk.yandex.ru/d/KV9o1nxAm9XVFA'
    }
    
    
}

# Функция для генерации меню выбора бравлеров
def generate_brawl_stars_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for brawler in brawler_list:
        markup.add(types.KeyboardButton(brawler))
    # Добавляем кнопку "Назад" в самый конец меню
    markup.add(types.KeyboardButton('Назад в выбор игры'))
    return markup

# Обработчик для опций в меню Brawl Stars
@bot.message_handler(func=lambda message: message.text in brawler_list.keys(), content_types=['text'])
def brawl_stars_option_selected(message):
    brawler_info = brawler_list.get(message.text)
    if brawler_info:
        name = brawler_info['name']
        photo_path = brawler_info['photo_path']
        link = brawler_info['link']
        
        # Создаем инлайн-кнопку "Скачать"
        markup = types.InlineKeyboardMarkup()
        button_download = types.InlineKeyboardButton('Скачать', url=link)
        markup.add(button_download)
        
        # Отправляем фото и информацию о бравлере с кнопкой "Скачать"
        try:
            with open(photo_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=f"Вы выбрали {name}.", reply_markup=markup)
        except Exception as e:
            bot.send_message(message.chat.id, f"Не удалось отправить информацию о {name}.")
            print(f"Ошибка при отправке фото: {e}")

# Обработчик для кнопки "Назад в выбор игры"
@bot.message_handler(func=lambda message: message.text == 'Назад в выбор игры', content_types=['text'])
def back_to_previous_menu(message):
    handle_start(message)  # Функция, которая возвращает пользователя в начальное меню


# Обработчик для кнопок выбора игр
@bot.message_handler(func=lambda message: message.text.lower() == 'dota2', content_types=['text'])
def game_selected(message):
    selected_game = message.text.lower()

    if selected_game == 'dota2':
        model_menu = generate_dota_options_menu()
        bot.send_message(message.chat.id, "Выберите модель для Dota 2:", reply_markup=model_menu)

# Функция для генерации меню выбора модели
def generate_dota_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(types.KeyboardButton('Back'))  # Изменил текст кнопки на 'Back'
    markup.add(types.KeyboardButton('Бесплатные модели'))
    return markup

# Обработка текстового сообщения "Back"
@bot.message_handler(func=lambda message: message.text == 'Back')
def handle_back(message):
    # Вызов функции, которая позволяет вернуться в главное меню
    onemenu(message)

# Функция для генерации меню выбора модели
def generate_model_options_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(types.KeyboardButton('/back'))
    markup.add(types.KeyboardButton('/fighters'))
    markup.add(types.KeyboardButton('/assassin'))
    markup.add(types.KeyboardButton('/mage'))
    markup.add(types.KeyboardButton('/marksman'))
    markup.add(types.KeyboardButton('/support'))
    markup.add(types.KeyboardButton('/tank'))
    return markup

# Обработка команды /back
@bot.message_handler(commands=['back'])
def handle_back(message):
    onemenu(message)

# Функция для генерации меню выбора стороны в игре WoW
def generate_wow_faction_menu():
    markup = types.ReplyKeyboardMarkup(row_width=1)
    markup.add(types.KeyboardButton('/horde'))
    markup.add(types.KeyboardButton('/alliance'))
    markup.add(types.KeyboardButton('/world_boss'))
    markup.add(types.KeyboardButton('Назад в выбор игры'))
    return markup

# Обработчик для кнопок "Назад в выбор игры"
@bot.message_handler(func=lambda message: message.text == 'Назад в выбор игры', content_types=['text'])
def back_to_previous_menu(message):
    handle_start(message)

# Обработчик для кнопки "back" в меню '/business_stats'
@bot.message_handler(func=lambda message: message.text == 'Назад в меню', content_types=['text'])
def back_to_generate_main_menu(message):
    main_menu = generate_main_menu()
    bot.send_message(message.chat.id, "Меню:", reply_markup=main_menu)

@bot.message_handler(func=lambda message: message.text == 'Где бесплатные модели?')
def handle_buttonn_clickk(message):
    response_text = '''
    Дорогие пользователи!
    Мы ценим ваш интерес к нашему каналу и хотим объяснить вам как работает система алмазов.
    Мы уделяем много времени и усилий, чтобы предоставить вам качественные 3D-модели. Для поддержания качества и развития канала нам нужны ресурсы. Именно поэтому мы ввели систему алмазов.
    Алмазы - это наш способ вас наградить за активность и лояльность. Вы можете накапливать алмазы абсолютно бесплатно, участвуя в активностях нашего бота. Когда у вас наберется достаточное количество алмазов, вы сможете обменять их на интересные 3D-модели.
    Эта система помогает нам поддерживать качество контента и делает его более доступным для всех. Мы надеемся, что вы цените наши усилия и продолжите нас поддерживать.
    Спасибо, что выбрали наш канал! Мы всегда готовы предоставить вам лучшие 3D-модели.
    С наилучшими пожеланиями,
    [@dikayl]
    '''
    bot.send_message(message.chat.id, response_text)


@bot.message_handler(func=lambda message: message.text == 'Заказать модель')
def handle_buttonn_click(message):
    bot.send_message(message.chat.id, 'За 💎 ты так же можешь заказать индивидуальную модель OBJ/STL формат 3D')
    bot.send_message(message.chat.id, 'Заказать можно: (Персонажа, здание, маунта, NPC итд...')


    # Создаем инлайн-клавиатуру с одной кнопкой
    keyboard = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text="Подробнее?", callback_data="continue_readingg")
    keyboard.add(button)

    bot.send_message(message.chat.id,
                     'Работаем на аддонах 3.3.5а - 7.2.5. Цена за услугу - индивидуальна, ~3000💎 или 500р',
                     reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data == "continue_readingg")
def continue_reading(call):
    # Отправляем фотографию
    photo_path = 'C:/pythonProject1/wow/IMG_5264.JPG'
    with open(photo_path, 'rb') as photo:
        bot.send_photo(call.message.chat.id, photo)

    # Отправляем текст
    bot.send_message(call.message.chat.id, 'Мы поможем оживить твоего персонажа. Создадим для тебя 3D копию твоего персонажа готовую для 3D печати')
    bot.send_message(call.message.chat.id,
                     'Пиши -> @dikayl ...')







@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.send_message(message.from_user.id, "/start <== нажми для перезапуска бота")



@bot.message_handler(commands=['miyab'])
def send_video(message):
    video_path = 'C:/pythonProject1/Marksman/miya_base.mp4'  # Путь к видеофайлу

    # Отправляем видеофайл пользователю
    with open(video_path, 'rb') as video:
        bot.send_video(message.chat.id, video)



def run_bot():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Произошла ошибка: {str(e)}")
            # Можно добавить логирование ошибки
            time.sleep(10)  # Подождать некоторое время перед повторной попыткой

if __name__ == '__main__':
    run_bot()
    db.close()


