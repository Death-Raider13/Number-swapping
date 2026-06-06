import os


def handle(driver, sender: str, content: str, cfg: dict, send_fn, is_media: bool = False):
    if is_media:
        media_path = os.path.join("media", content)
        if os.path.exists(media_path):
            send_fn(driver, sender, None, media_path=os.path.abspath(media_path))
        else:
            send_fn(driver, sender, f"⚠️ File '{content}' not found.")
    else:
        send_fn(driver, sender, content)
