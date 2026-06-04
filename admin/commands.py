import json
import state
import config as cfg_mod
from admin.parser import parse


def handle(driver, sender: str, msg: str, bot_config: dict, send_fn):
    command, rest = parse(msg)
    if command is None:
        return

    handlers = {
        "status":      _status,
        "reload":      _reload,
        "reset":       _reset,
        "broadcast":   _broadcast,
        "setgreeting": _setgreeting,
        "setfallback": _setfallback,
        "addmenu":     _addmenu,
        "addoption":   _addoption,
        "deloption":   _deloption,
        "delmenu":     _delmenu,
        "addflow":     _addflow,
        "addstep":     _addstep,
        "delstep":     _delstep,
        "delflow":     _delflow,
        "setcomplete": _setcomplete,
        "addreply":    _addreply,
        "editreply":   _editreply,
        "delreply":    _delreply,
        "schedule":      _schedule,
        "delschedule":   _delschedule,
        "addkeyword":    _addkeyword,
        "delkeyword":    _delkeyword,
        "listkeywords":  _listkeywords,
        "aion":          _aion,
        "aioff":         _aioff,
        "setaiprompt":   _setaiprompt,
        "setaikey":      _setaikey,
        "listmenus":     _listmenus,
        "listflows":     _listflows,
        "listreplies":   _listreplies,
        "help":          _help,
    }

    fn = handlers.get(command)
    if fn:
        fn(driver, sender, rest, bot_config, send_fn)
    else:
        send_fn(driver, sender, f"❓ Unknown command: *!{command}*\nSend *!help* for a list.")


# ── Save helpers ───────────────────────────────────────────────────────────────

def _save(bot_config: dict):
    with open(cfg_mod.CONFIG_PATH, "w") as f:
        json.dump(bot_config, f, indent=2, ensure_ascii=False)


def _ok(driver, sender, send_fn, text="✅ Done."):
    send_fn(driver, sender, text)


# ── Commands ───────────────────────────────────────────────────────────────────

def _status(driver, sender, rest, cfg, send_fn):
    total = len(state.all_users())
    active = state.active_count()
    menus = len(cfg.get("menus", {}))
    flows = len(cfg.get("flows", {}))
    replies = len(cfg.get("replies", {}))
    schedules = len(cfg.get("scheduled_messages", []))
    send_fn(driver, sender,
        f"📊 *Bot Status*\n\n"
        f"⏱ Uptime: {state.uptime_str()}\n"
        f"👥 Total contacts: {total}\n"
        f"💬 Active chats: {active}\n"
        f"📋 Menus: {menus} | Flows: {flows}\n"
        f"💬 Replies: {replies} | Schedules: {schedules}"
    )


def _reload(driver, sender, rest, cfg, send_fn):
    try:
        with open(cfg_mod.CONFIG_PATH) as f:
            new_cfg = json.load(f)
        cfg.clear()
        cfg.update(new_cfg)
        _ok(driver, sender, send_fn, "♻️ Config reloaded.")
    except Exception as e:
        send_fn(driver, sender, f"❌ Reload failed: {e}")


def _reset(driver, sender, rest, cfg, send_fn):
    target = rest.strip()
    if not target:
        send_fn(driver, sender, "Usage: *!reset <number_or_name>*")
        return
    state.clear(target)
    _ok(driver, sender, send_fn, f"✅ State cleared for {target}.")


def _broadcast(driver, sender, rest, cfg, send_fn):
    msg = rest.strip()
    if not msg:
        send_fn(driver, sender, "Usage: *!broadcast <message>*")
        return
    contacts = cfg.get("known_contacts", [])
    if not contacts:
        send_fn(driver, sender, "⚠️ No known contacts yet. Users must message the bot first.")
        return
    for contact in contacts:
        try:
            send_fn(driver, contact, f"📢 {msg}")
        except Exception as e:
            print(f"[Broadcast] Failed for {contact}: {e}")
    _ok(driver, sender, send_fn, f"✅ Broadcast sent to {len(contacts)} contacts.")


def _setgreeting(driver, sender, rest, cfg, send_fn):
    if not rest.strip():
        send_fn(driver, sender, "Usage: *!setgreeting <text>*")
        return
    cfg["greeting"] = rest.strip()
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Greeting updated.")


def _setfallback(driver, sender, rest, cfg, send_fn):
    if not rest.strip():
        send_fn(driver, sender, "Usage: *!setfallback <text>*")
        return
    cfg["fallback"] = rest.strip()
    _save(cfg)
    _ok(driver, sender, send_fn)


def _addmenu(driver, sender, rest, cfg, send_fn):
    parts = rest.split(None, 1)
    if len(parts) < 2:
        send_fn(driver, sender, "Usage: *!addmenu <menu_id> <prompt text>*")
        return
    menu_id, text = parts[0], parts[1]
    if menu_id in cfg.get("menus", {}):
        send_fn(driver, sender, f"⚠️ Menu *{menu_id}* already exists. Use *!addoption* to add options.")
        return
    cfg.setdefault("menus", {})[menu_id] = {"text": text, "options": {}}
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Menu *{menu_id}* created.")


def _addoption(driver, sender, rest, cfg, send_fn):
    # Format: <menu_id> <num> <label> | <action>
    if "|" not in rest:
        send_fn(driver, sender, "Usage: *!addoption <menu_id> <num> <label> | <action>*\nExample: `!addoption main 5 New Service | flow:service`")
        return
    label_part, action = rest.rsplit("|", 1)
    parts = label_part.split(None, 2)
    if len(parts) < 3:
        send_fn(driver, sender, "Usage: *!addoption <menu_id> <num> <label> | <action>*")
        return
    menu_id, num, label = parts[0], parts[1], parts[2].strip()
    action = action.strip()
    menus = cfg.get("menus", {})
    if menu_id not in menus:
        send_fn(driver, sender, f"❌ Menu *{menu_id}* not found. Create it first with *!addmenu*.")
        return
    menus[menu_id]["options"][num] = {"label": label, "action": action}
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Option {num} added to *{menu_id}*.")


def _deloption(driver, sender, rest, cfg, send_fn):
    parts = rest.split()
    if len(parts) < 2:
        send_fn(driver, sender, "Usage: *!deloption <menu_id> <num>*")
        return
    menu_id, num = parts[0], parts[1]
    menus = cfg.get("menus", {})
    if menu_id not in menus or num not in menus[menu_id].get("options", {}):
        send_fn(driver, sender, f"❌ Option {num} not found in *{menu_id}*.")
        return
    del menus[menu_id]["options"][num]
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Option {num} removed from *{menu_id}*.")


def _delmenu(driver, sender, rest, cfg, send_fn):
    menu_id = rest.strip()
    if not menu_id:
        send_fn(driver, sender, "Usage: *!delmenu <menu_id>*")
        return
    if menu_id == "main":
        send_fn(driver, sender, "❌ Cannot delete the *main* menu.")
        return
    cfg.get("menus", {}).pop(menu_id, None)
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Menu *{menu_id}* deleted.")


def _addflow(driver, sender, rest, cfg, send_fn):
    flow_id = rest.strip()
    if not flow_id:
        send_fn(driver, sender, "Usage: *!addflow <flow_id>*")
        return
    if flow_id in cfg.get("flows", {}):
        send_fn(driver, sender, f"⚠️ Flow *{flow_id}* already exists.")
        return
    cfg.setdefault("flows", {})[flow_id] = {
        "steps": [],
        "on_complete": {"reply": "✅ Thank you!", "log_to_sheets": True, "send_email": True}
    }
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Flow *{flow_id}* created. Add steps with *!addstep*.")


def _addstep(driver, sender, rest, cfg, send_fn):
    # Format: <flow_id> <key> <prompt text>
    parts = rest.split(None, 2)
    if len(parts) < 3:
        send_fn(driver, sender, "Usage: *!addstep <flow_id> <key> <prompt text>*\nExample: `!addstep booking phone What is your phone number?`")
        return
    flow_id, key, prompt = parts
    flows = cfg.get("flows", {})
    if flow_id not in flows:
        send_fn(driver, sender, f"❌ Flow *{flow_id}* not found. Create it first with *!addflow*.")
        return
    flows[flow_id]["steps"].append({"key": key, "prompt": prompt})
    _save(cfg)
    step_num = len(flows[flow_id]["steps"])
    _ok(driver, sender, send_fn, f"✅ Step {step_num} (*{key}*) added to flow *{flow_id}*.")


def _delstep(driver, sender, rest, cfg, send_fn):
    parts = rest.split()
    if len(parts) < 2:
        send_fn(driver, sender, "Usage: *!delstep <flow_id> <step_number>* (1-based)")
        return
    flow_id = parts[0]
    try:
        idx = int(parts[1]) - 1
    except ValueError:
        send_fn(driver, sender, "❌ Step number must be an integer.")
        return
    flows = cfg.get("flows", {})
    if flow_id not in flows:
        send_fn(driver, sender, f"❌ Flow *{flow_id}* not found.")
        return
    steps = flows[flow_id].get("steps", [])
    if idx < 0 or idx >= len(steps):
        send_fn(driver, sender, f"❌ Step {idx+1} doesn't exist in *{flow_id}*.")
        return
    removed = steps.pop(idx)
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Removed step *{removed['key']}* from *{flow_id}*.")


def _delflow(driver, sender, rest, cfg, send_fn):
    flow_id = rest.strip()
    if not flow_id:
        send_fn(driver, sender, "Usage: *!delflow <flow_id>*")
        return
    cfg.get("flows", {}).pop(flow_id, None)
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Flow *{flow_id}* deleted.")


def _setcomplete(driver, sender, rest, cfg, send_fn):
    parts = rest.split(None, 1)
    if len(parts) < 2:
        send_fn(driver, sender, "Usage: *!setcomplete <flow_id> <reply text>*\nUse {key} placeholders for collected answers.")
        return
    flow_id, reply_text = parts
    flows = cfg.get("flows", {})
    if flow_id not in flows:
        send_fn(driver, sender, f"❌ Flow *{flow_id}* not found.")
        return
    flows[flow_id].setdefault("on_complete", {})["reply"] = reply_text
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Completion message updated for *{flow_id}*.")


def _addreply(driver, sender, rest, cfg, send_fn):
    parts = rest.split(None, 1)
    if len(parts) < 2:
        send_fn(driver, sender, "Usage: *!addreply <reply_id> <text>*")
        return
    reply_id, text = parts
    cfg.setdefault("replies", {})[reply_id] = text
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Reply *{reply_id}* saved.")


def _editreply(driver, sender, rest, cfg, send_fn):
    _addreply(driver, sender, rest, cfg, send_fn)


def _delreply(driver, sender, rest, cfg, send_fn):
    reply_id = rest.strip()
    if not reply_id:
        send_fn(driver, sender, "Usage: *!delreply <reply_id>*")
        return
    cfg.get("replies", {}).pop(reply_id, None)
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Reply *{reply_id}* deleted.")


def _schedule(driver, sender, rest, cfg, send_fn):
    # Format: <HH:MM> <Mon,Tue,...|daily> <message text>
    parts = rest.split(None, 2)
    if len(parts) < 3:
        send_fn(driver, sender,
            "Usage: *!schedule <HH:MM> <days> <message>*\n"
            "Days: *daily* or comma-separated like *Mon,Wed,Fri*\n"
            "Example: `!schedule 09:00 Mon,Fri Good morning everyone!`"
        )
        return
    time_str, days_str, msg = parts
    if days_str.lower() == "daily":
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    else:
        days = [d.strip() for d in days_str.split(",")]

    import uuid
    sched_id = str(uuid.uuid4())[:8]
    cfg.setdefault("scheduled_messages", []).append({
        "id": sched_id,
        "text": msg,
        "time": time_str,
        "days": days,
        "recipients": []
    })
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Schedule *{sched_id}* created: {time_str} on {days_str}.")


def _delschedule(driver, sender, rest, cfg, send_fn):
    sched_id = rest.strip()
    before = len(cfg.get("scheduled_messages", []))
    cfg["scheduled_messages"] = [s for s in cfg.get("scheduled_messages", []) if s["id"] != sched_id]
    after = len(cfg.get("scheduled_messages", []))
    if before == after:
        send_fn(driver, sender, f"❌ Schedule *{sched_id}* not found.")
        return
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Schedule *{sched_id}* deleted.")


def _addkeyword(driver, sender, rest, cfg, send_fn):
    # Format: <keyword> <reply text>
    parts = rest.split(None, 1)
    if len(parts) < 2:
        send_fn(driver, sender, "Usage: *!addkeyword <keyword> <reply text>*\nExample: `!addkeyword price Our prices start from ₦5,000`")
        return
    keyword, reply = parts
    cfg.setdefault("keywords", {})[keyword.lower()] = reply
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Keyword *{keyword}* saved.")


def _delkeyword(driver, sender, rest, cfg, send_fn):
    keyword = rest.strip().lower()
    if not keyword:
        send_fn(driver, sender, "Usage: *!delkeyword <keyword>*")
        return
    if keyword not in cfg.get("keywords", {}):
        send_fn(driver, sender, f"❌ Keyword *{keyword}* not found.")
        return
    del cfg["keywords"][keyword]
    _save(cfg)
    _ok(driver, sender, send_fn, f"✅ Keyword *{keyword}* deleted.")


def _listkeywords(driver, sender, rest, cfg, send_fn):
    keywords = cfg.get("keywords", {})
    if not keywords:
        send_fn(driver, sender, "No keywords configured.")
        return
    lines = ["🔑 *Keywords:*", ""]
    for kw, reply in keywords.items():
        preview = reply[:55] + ("..." if len(reply) > 55 else "")
        lines.append(f"*{kw}* → {preview}")
    send_fn(driver, sender, "\n".join(lines))


def _aion(driver, sender, rest, cfg, send_fn):
    cfg.setdefault("ai_fallback", {})["enabled"] = True
    _save(cfg)
    _ok(driver, sender, send_fn, "🤖 AI fallback *enabled*.")


def _aioff(driver, sender, rest, cfg, send_fn):
    cfg.setdefault("ai_fallback", {})["enabled"] = False
    _save(cfg)
    _ok(driver, sender, send_fn, "🤖 AI fallback *disabled*.")


def _setaiprompt(driver, sender, rest, cfg, send_fn):
    if not rest.strip():
        send_fn(driver, sender, "Usage: *!setaiprompt <system prompt text>*")
        return
    cfg.setdefault("ai_fallback", {})["system_prompt"] = rest.strip()
    _save(cfg)
    _ok(driver, sender, send_fn, "✅ AI system prompt updated.")


def _setaikey(driver, sender, rest, cfg, send_fn):
    if not rest.strip():
        send_fn(driver, sender, "Usage: *!setaikey <your_anthropic_api_key>*")
        return
    cfg.setdefault("ai_fallback", {})["api_key"] = rest.strip()
    _save(cfg)
    _ok(driver, sender, send_fn, "✅ AI API key saved.")


def _listmenus(driver, sender, rest, cfg, send_fn):
    menus = cfg.get("menus", {})
    if not menus:
        send_fn(driver, sender, "No menus configured.")
        return
    lines = ["📋 *Menus:*", ""]
    for mid, menu in menus.items():
        lines.append(f"*{mid}* — {menu['text']}")
        for num, opt in menu.get("options", {}).items():
            lines.append(f"  {num}. {opt['label']} → {opt['action']}")
        lines.append("")
    send_fn(driver, sender, "\n".join(lines).strip())


def _listflows(driver, sender, rest, cfg, send_fn):
    flows = cfg.get("flows", {})
    if not flows:
        send_fn(driver, sender, "No flows configured.")
        return
    lines = ["🔄 *Flows:*", ""]
    for fid, flow in flows.items():
        steps = flow.get("steps", [])
        lines.append(f"*{fid}* ({len(steps)} steps)")
        for i, step in enumerate(steps, 1):
            lines.append(f"  {i}. [{step['key']}] {step['prompt']}")
        lines.append(f"  ✅ On complete: {flow.get('on_complete',{}).get('reply','(not set)')[:50]}...")
        lines.append("")
    send_fn(driver, sender, "\n".join(lines).strip())


def _listreplies(driver, sender, rest, cfg, send_fn):
    replies = cfg.get("replies", {})
    if not replies:
        send_fn(driver, sender, "No quick replies configured.")
        return
    lines = ["💬 *Quick Replies:*", ""]
    for rid, text in replies.items():
        lines.append(f"*{rid}:* {text[:60]}{'...' if len(text) > 60 else ''}")
    send_fn(driver, sender, "\n".join(lines))


def _help(driver, sender, rest, cfg, send_fn):
    help_text = (
        "🤖 *Admin Commands*\n\n"
        "*General*\n"
        "!status — Bot stats\n"
        "!reload — Reload config file\n"
        "!reset <name> — Clear user state\n"
        "!broadcast <msg> — Send to all contacts\n\n"
        "*Menus*\n"
        "!addmenu <id> <text>\n"
        "!addoption <menu> <num> <label> | <action>\n"
        "!deloption <menu> <num>\n"
        "!delmenu <id>\n"
        "!listmenus\n\n"
        "*Flows*\n"
        "!addflow <id>\n"
        "!addstep <flow> <key> <prompt>\n"
        "!delstep <flow> <num>\n"
        "!setcomplete <flow> <reply text>\n"
        "!delflow <id>\n"
        "!listflows\n\n"
        "*Replies*\n"
        "!addreply <id> <text>\n"
        "!editreply <id> <text>\n"
        "!delreply <id>\n"
        "!listreplies\n\n"
        "*Keywords*\n"
        "!addkeyword <word> <reply>\n"
        "!delkeyword <word>\n"
        "!listkeywords\n\n"
        "*AI Fallback*\n"
        "!aion — Enable AI replies\n"
        "!aioff — Disable AI replies\n"
        "!setaikey <api_key>\n"
        "!setaiprompt <prompt>\n\n"
        "*Schedules*\n"
        "!schedule <HH:MM> <days|daily> <msg>\n"
        "!delschedule <id>\n\n"
        "*Bot text*\n"
        "!setgreeting <text>\n"
        "!setfallback <text>"
    )
    send_fn(driver, sender, help_text)
