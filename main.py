from telegram import Update, InputMediaPhoto
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re
from tiktok_service import get_bytes  # Импортируем вашу функцию
from dotenv import load_dotenv
import os
import time
from telegram.error import NetworkError
import asyncio
load_dotenv()
# Токен вашего бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Регулярное выражение для поиска ссылок на TikTok
TIKTOK_PATTERN = r"(https?://(www\.)?(vm\.)?tiktok\.com/[^\s]+)"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что сообщение из группы и содержит текст
    if update.message and update.message.text:
        # Ищем ссылку на TikTok в тексте сообщения
        match = re.search(TIKTOK_PATTERN, update.message.text)
        if match:
            tiktok_url = match.group(0)
            try:
                # Получаем данные от TikTok
                tiktok_bytes = get_bytes(tiktok_url)
                
                # Удаляем оригинальное сообщение
                await update.message.delete()
                
                # Определяем идентификатор отправителя
                sender = update.message.from_user
                sender_name = (sender.full_name or sender.username or str(sender.id))
                
                if isinstance(tiktok_bytes, list):
                    # Если вернулся список (фотографии)
                    if len(tiktok_bytes) <= 10:
                        # Отправляем альбом, если фотографий 10 или меньше
                        media = [InputMediaPhoto(photo) for photo in tiktok_bytes]
                        await context.bot.send_media_group(
                            chat_id=update.message.chat_id,
                            media=media,
                            caption=f"Отправлено: {sender_name}" if media else None
                        )
                    else:
                        # Отправляем фотографии по одной, если их больше 10
                        for photo in tiktok_bytes:
                            await context.bot.send_photo(
                                chat_id=update.message.chat_id,
                                photo=photo,
                                caption=f"Отправлено: {sender_name}"
                            )
                else:
                    # Если вернулось видео (байты)
                    video_bytes = tiktok_bytes
                    await context.bot.send_video(
                        chat_id=update.message.chat_id,
                        video=video_bytes,
                        supports_streaming=True,
                        caption=f"Отправлено: {sender_name}"
                    )
            except Exception as e:
                # В случае ошибки отправляем сообщение об ошибке
                sender = update.message.from_user
                sender_name = (sender.full_name or sender.username or str(sender.id))
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=f"Ошибка при обработке TikTok ссылки: {str(e)}\nОтправлено: {sender_name}"
                )

async def error_handler(update: Update, context):
    """Custom error handler to suppress stack traces and print clean error messages."""
    if isinstance(context.error, NetworkError):
        print("Ошибка сети")
    else:
        print(f"Unexpected error during polling: {context.error}")

async def run_bot():
    # Create the application
    application = Application.builder().token(TOKEN).build()

    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add custom error handler
    application.add_error_handler(error_handler)

    initialized = False  # Track if initialize() succeeded
    started = False  # Track if start() succeeded

    while True:
        try:
            # Initialize and start the bot
            await application.initialize()
            initialized = True
            await application.start()
            started = True
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            print("Программа запущена")
            
            # Keep the bot running until stopped
            await asyncio.Future()  # Infinite wait
            break  # Exit loop if polling starts successfully

        except NetworkError as e:
            print(f"Ошибка сети, повторная попытка через 60 секунд: {e}")
            await asyncio.sleep(60)  # Wait 60 seconds before retrying
            
            # Clean up only if necessary
            if application.updater.running:
                await application.updater.stop()
            if started:
                await application.stop()
            if initialized:
                await application.shutdown()

            initialized = False
            started = False

        except Exception as e:
            print(f"Unexpected error: {e}. Stopping bot.")
            # Clean up only if necessary
            if application.updater.running:
                await application.updater.stop()
            if started:
                await application.stop()
            if initialized:
                await application.shutdown()
            break

def main():
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()