import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.error import Conflict
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
# Backoff при конфликте getUpdates
_conflict_backoff = 1
_conflict_backoff_max = 60
_conflict_lock = asyncio.Lock()
from urllib.parse import urlparse

# ========================
# Настройки (через переменные окружения)
# ========================
# Установите TELEGRAM_BOT_TOKEN в переменных окружения для безопасности
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Укажите публичный URL вашего сайта (GitHub Pages) в WEBAPP_URL
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
TELEGRAM_WEBHOOK_URL = os.environ.get("TELEGRAM_WEBHOOK_URL", "")
PORT = int(os.environ.get("PORT", "8443"))
USE_WEBHOOK = os.environ.get("USE_WEBHOOK", "0").lower() in ("1", "true", "yes")


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


async def error_handler(update: object | None, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок для Application.
    Перехватывает telegram.error.Conflict и логирует предупреждение вместо падения приложения.
    """
    err = context.error
    # Conflict возникает, когда другой экземпляр использует getUpdates (polling)
    if isinstance(err, Conflict):
        logger.warning(
            "telegram.error.Conflict: терминовано другим getUpdates; убедитесь, что запущен только один экземпляр бота."
        )
        # Экспоненциальный backoff, защищённый lock'ом
        try:
            async with _conflict_lock:
                wait = _conflict_backoff
                logger.info(f"Waiting {wait}s before retrying polling")
                await asyncio.sleep(wait)
                # увеличиваем backoff для следующего раза
                globals()['_conflict_backoff'] = min(_conflict_backoff * 2, _conflict_backoff_max)
        except Exception:
            pass
        return

    # Для остальных ошибок — логируем стектрейс
    logger.exception("Unhandled exception in update handler", exc_info=err)

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
    # Регистрируем глобальный обработчик ошибок
    application.add_error_handler(error_handler)

    if USE_WEBHOOK and TELEGRAM_WEBHOOK_URL:
        # Запускаем в режиме webhook. Определяем путь из TELEGRAM_WEBHOOK_URL
        parsed = urlparse(TELEGRAM_WEBHOOK_URL)
        path = parsed.path or "/"
        # PTB ожидает путь без домена
        logger.info(f"Запуск в режиме webhook на {TELEGRAM_WEBHOOK_URL} (listen 0.0.0.0:{PORT}, path={path})")
        application.run_webhook(listen="0.0.0.0", port=PORT, path=path, webhook_url=TELEGRAM_WEBHOOK_URL)
    else:
        logger.info("Бот запущен в режиме polling. Ждем сообщений...")
        application.run_polling()

# ========================
# Запуск
# ========================
if __name__ == "__main__":
    main()
