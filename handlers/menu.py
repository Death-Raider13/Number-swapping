import state


def show(driver, sender: str, menu_id: str, cfg: dict, send_fn):
    menus = cfg.get("menus", {})
    if menu_id not in menus:
        send_fn(driver, sender, cfg.get("fallback", "Menu not found."))
        return

    menu = menus[menu_id]
    lines = [menu["text"], ""]
    for num, opt in menu["options"].items():
        lines.append(f"*{num}.* {opt['label']}")
    send_fn(driver, sender, "\n".join(lines))
    state.set(sender, f"menu:{menu_id}")


def handle(driver, sender: str, msg: str, cfg: dict, send_fn):
    current = state.get(sender)
    menu_id = current.split(":")[1] if ":" in current else "main"
    menus = cfg.get("menus", {})
    menu = menus.get(menu_id, {})
    options = menu.get("options", {})

    choice = msg.strip()
    if choice not in options:
        lines = ["❓ Please choose one of the options below:", ""]
        for num, opt in options.items():
            lines.append(f"*{num}.* {opt['label']}")
        send_fn(driver, sender, "\n".join(lines))
        return

    action = options[choice]["action"]
    _dispatch_action(driver, sender, action, cfg, send_fn)


def _dispatch_action(driver, sender: str, action: str, cfg: dict, send_fn):
    from handlers.flow import start as flow_start
    from handlers.reply import handle as reply_handle

    if action.startswith("menu:"):
        target = action[5:]
        show(driver, sender, target, cfg, send_fn)

    elif action.startswith("flow:"):
        flow_id = action[5:]
        flow_start(driver, sender, flow_id, cfg, send_fn)

    elif action.startswith("reply:"):
        reply_id = action[6:]
        text = cfg.get("replies", {}).get(reply_id, "No reply configured.")
        send_fn(driver, sender, text)
        state.set(sender, "idle")

    elif action.startswith("media:"):
        filename = action[6:]
        reply_handle(driver, sender, filename, cfg, send_fn, is_media=True)
        state.set(sender, "idle")

    else:
        send_fn(driver, sender, cfg.get("fallback", "Unknown action."))
