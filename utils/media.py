import os
import logging
from config.settings import MEDIA_DIR


async def download_media(client, message, sender_name, timestamp):
    """Скачивает медиа файл в папку media"""
    try:
        date_str = timestamp.replace(":", "-").replace(" ", "_")
        safe_sender = "".join(c for c in sender_name if c.isalnum() or c in (' ', '-', '_'))

        if message.photo:
            filename = f"{date_str}_{safe_sender}_photo.jpg"
            filepath = os.path.join(MEDIA_DIR, filename)
            await client.download_media(message.photo, filepath)
            return f"[📷 Фото: {filename}]"

        elif message.document:
            for attr in message.document.attributes:
                if hasattr(attr, 'file_name'):
                    original_name = attr.file_name
                    filename = f"{date_str}_{safe_sender}_{original_name}"
                    filepath = os.path.join(MEDIA_DIR, filename)
                    await client.download_media(message.document, filepath)
                    return f"[📄 Файл: {filename}]"

            filename = f"{date_str}_{safe_sender}_doc_{message.document.id}"
            filepath = os.path.join(MEDIA_DIR, filename)
            await client.download_media(message.document, filepath)
            return f"[📄 Файл: {filename}]"

        elif message.video:
            filename = f"{date_str}_{safe_sender}_video.mp4"
            filepath = os.path.join(MEDIA_DIR, filename)
            await client.download_media(message.video, filepath)
            return f"[🎥 Видео: {filename}]"

        elif message.voice:
            filename = f"{date_str}_{safe_sender}_voice.ogg"
            filepath = os.path.join(MEDIA_DIR, filename)
            await client.download_media(message.voice, filepath)
            return f"[🎤 Голосовое: {filename}]"

        elif message.audio:
            filename = f"{date_str}_{safe_sender}_audio.mp3"
            filepath = os.path.join(MEDIA_DIR, filename)
            await client.download_media(message.audio, filepath)
            return f"[🎵 Аудио: {filename}]"

        else:
            return "[📎 Медиа]"

    except Exception as e:
        logging.error(f"Ошибка загрузки медиа: {e}")
        return "[Ошибка загрузки]"