import state
import config as cfg_mod
from handlers import menu, flow
from admin import commands


def is_admin(sender: str) -> bool:
    clean = sender.replace("+", "").replace(" ", "").replace("-", "")
    return clean == cfg_mod.ADMIN_NUMBER


def route(driver, sender: str, msg: str, cfg: dict, send_fn):
    msg_stripped = msg.strip()
    if not msg_stripped:
        return

    # Track contact for broadcasts
    contacts = cfg.setdefault("known_contacts", [])
    if sender not in contacts:
        contacts.append(sender)

    # Admin commands
    if is_admin(sender) and msg_stripped.startswith("!"):
        commands.handle(driver, sender, msg_stripped, cfg, send_fn)
        return

    user_state = state.get(sender)

    # Active flow — pass message straight to flow handler
    if user_state.startswith("flow:"):
        flow.handle(driver, sender, msg_stripped, cfg, send_fn)
        return

    # Active menu — pass message straight to menu handler
    if user_state.startswith("menu:"):
        menu.handle(driver, sender, msg_stripped, cfg, send_fn)
        return

    # Trigger words → greeting + main menu
    if msg_stripped.lower() in [w.lower() for w in cfg.get("trigger_words", [])]:
        send_fn(driver, sender, cfg.get("greeting", "Hello!"))
        menu.show(driver, sender, "main", cfg, send_fn)
        return

    # Keyword auto-replies (case-insensitive substring match)
    keyword_reply = _match_keyword(msg_stripped, cfg.get("keywords", {}))
    if keyword_reply:
        send_fn(driver, sender, keyword_reply)
        return

    # AI fallback (if enabled)
    ai_cfg = cfg.get("ai_fallback", {})
    if ai_cfg.get("enabled") and ai_cfg.get("api_key"):
        ai_reply = _get_ai_reply(msg_stripped, sender, cfg)
        if ai_reply:
            send_fn(driver, sender, ai_reply)
            return

    # Final fallback
    send_fn(driver, sender, cfg.get("fallback", "Type *hi* to start."))


def _match_keyword(msg: str, keywords: dict) -> str | None:
    msg_lower = msg.lower()
    for keyword, reply in keywords.items():
        if keyword.lower() in msg_lower:
            return reply
    return None


def _get_ai_reply(msg: str, sender: str, cfg: dict) -> str | None:
    try:
        import anthropic

        ai_cfg = cfg.get("ai_fallback", {})
        client = anthropic.Anthropic(api_key=ai_cfg["api_key"])

        system = ai_cfg.get(
            "system_prompt",
            "You are a helpful customer service assistant. Be concise and friendly."
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system,
            messages=[{"role": "user", "content": msg}],
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"[AI] Fallback error: {e}")
        return None
