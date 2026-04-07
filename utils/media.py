import os
import logging
from config.settings import MEDIA_DIR


def _sanitize_sender(sender_name):
    safe_sender = "".join(c for c in sender_name if c.isalnum() or c in (" ", "-", "_"))
    return safe_sender.strip() or "unknown"


def _message_suffix(message):
    message_id = getattr(message, "id", None)
    return str(message_id) if message_id is not None else "msg"


def _build_media_result(label, filename=None, downloaded=False):
    path_value = os.path.join(MEDIA_DIR, filename) if filename else None
    if filename:
        text = f"[{label}: {filename}]"
    else:
        text = f"[{label}]"
    return {
        "text": text,
        "filename": filename,
        "path": path_value,
        "is_media": True,
        "downloaded": downloaded,
    }


def describe_media(message, sender_name, timestamp):
    date_str = timestamp.replace(":", "-").replace(" ", "_")
    safe_sender = _sanitize_sender(sender_name)
    suffix = _message_suffix(message)

    if message.photo:
        filename = f"{date_str}_{safe_sender}_{suffix}_photo.jpg"
        path_value = os.path.join(MEDIA_DIR, filename)
        return _build_media_result("Photo", filename, downloaded=os.path.exists(path_value))

    if message.document:
        for attr in message.document.attributes:
            if hasattr(attr, "file_name") and attr.file_name:
                filename = f"{date_str}_{safe_sender}_{suffix}_{attr.file_name}"
                path_value = os.path.join(MEDIA_DIR, filename)
                return _build_media_result("File", filename, downloaded=os.path.exists(path_value))
        filename = f"{date_str}_{safe_sender}_{suffix}_doc_{message.document.id}"
        path_value = os.path.join(MEDIA_DIR, filename)
        return _build_media_result("File", filename, downloaded=os.path.exists(path_value))

    if message.video:
        filename = f"{date_str}_{safe_sender}_{suffix}_video.mp4"
        path_value = os.path.join(MEDIA_DIR, filename)
        return _build_media_result("Video", filename, downloaded=os.path.exists(path_value))

    if message.voice:
        filename = f"{date_str}_{safe_sender}_{suffix}_voice.ogg"
        path_value = os.path.join(MEDIA_DIR, filename)
        return _build_media_result("Voice", filename, downloaded=os.path.exists(path_value))

    if message.audio:
        filename = f"{date_str}_{safe_sender}_{suffix}_audio.mp3"
        path_value = os.path.join(MEDIA_DIR, filename)
        return _build_media_result("Audio", filename, downloaded=os.path.exists(path_value))

    return _build_media_result("Media", None, downloaded=False)


async def download_media(client, message, sender_name, timestamp):
    try:
        result = describe_media(message, sender_name, timestamp)
        filepath = result.get("path")
        if not filepath:
            return result
        if os.path.exists(filepath):
            result["downloaded"] = True
            return result

        if message.photo:
            await client.download_media(message.photo, filepath)
        elif message.document:
            await client.download_media(message.document, filepath)
        elif message.video:
            await client.download_media(message.video, filepath)
        elif message.voice:
            await client.download_media(message.voice, filepath)
        elif message.audio:
            await client.download_media(message.audio, filepath)

        result["downloaded"] = os.path.exists(filepath)
        return result
    except Exception as e:
        logging.error(f"Media download error: {e}")
        return {
            "text": "[Media download error]",
            "filename": None,
            "path": None,
            "is_media": False,
            "downloaded": False,
        }
