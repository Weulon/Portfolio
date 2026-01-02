import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# ========================
# Настройки
# ========================
TELEGRAM_BOT_TOKEN = "8579039126:AAFduTOX1YZKw0Y41T-rCWEuygLC_cVdSMw"

# сюда вставь свой ngrok HTTPS URL
WEBAPP_URL = "https://authorless-theo-apogeotropic.ngrok-free.dev"


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
