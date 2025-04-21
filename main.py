from telegram import Update, InputMediaPhoto
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import re
from tiktok_service import get_bytes  # Импортируем вашу функцию
from dotenv import load_dotenv
import os

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

def main():
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчик сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()