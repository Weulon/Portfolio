import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# ========================
# Настройки (через переменные окружения)
# ========================
# Установите TELEGRAM_BOT_TOKEN в переменных окружения для безопасности
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Укажите публичный URL вашего сайта (GitHub Pages) в WEBAPP_URL
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")


# ========================
# Логирование
# ========================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================
# Обработчики
# ========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    # если WEBAPP_URL не задан, кнопка не будет добавлена
    keyboard = []
    if WEBAPP_URL:
        keyboard = [
            [InlineKeyboardButton("🎨 Открыть каталог", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Добро пожаловать в каталог авторских фигурок!\n\n"
        "Нажмите кнопку ниже, чтобы открыть каталог и посмотреть коллекции.",
        reply_markup=reply_markup
    )

# ========================
# Основная функция
# ========================

def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не задан. Установите переменную окружения TELEGRAM_BOT_TOKEN и повторите запуск.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))

    logger.info("Бот запущен. Ждем сообщений...")
    application.run_polling()

# ========================
# Запуск
# ========================
if __name__ == "__main__":
    main()
