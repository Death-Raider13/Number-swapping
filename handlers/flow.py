import state
from integrations import sheets, email_notify


def start(driver, sender: str, flow_id: str, cfg: dict, send_fn):
    flows = cfg.get("flows", {})
    if flow_id not in flows:
        send_fn(driver, sender, cfg.get("fallback", "Flow not found."))
        return

    state.clear_flow_data(sender)
    state.set(sender, f"flow:{flow_id}:0")
    _ask_step(driver, sender, flow_id, 0, cfg, send_fn)


def handle(driver, sender: str, msg: str, cfg: dict, send_fn):
    current = state.get(sender)
    parts = current.split(":")
    if len(parts) < 3:
        state.set(sender, "idle")
        return

    flow_id, step_idx = parts[1], int(parts[2])
    flows = cfg.get("flows", {})
    flow = flows.get(flow_id, {})
    steps = flow.get("steps", [])

    if step_idx >= len(steps):
        state.set(sender, "idle")
        return

    key = steps[step_idx]["key"]
    state.set_flow_data(sender, key, msg.strip())

    next_step = step_idx + 1
    if next_step < len(steps):
        state.set(sender, f"flow:{flow_id}:{next_step}")
        _ask_step(driver, sender, flow_id, next_step, cfg, send_fn)
    else:
        _complete(driver, sender, flow_id, cfg, send_fn)


def _ask_step(driver, sender: str, flow_id: str, step_idx: int, cfg: dict, send_fn):
    step = cfg["flows"][flow_id]["steps"][step_idx]
    send_fn(driver, sender, step["prompt"])


def _complete(driver, sender: str, flow_id: str, cfg: dict, send_fn):
    flow = cfg["flows"][flow_id]
    data = state.get_flow_data(sender)
    on_complete = flow.get("on_complete", {})

    reply_template = on_complete.get("reply", "✅ Done! Thank you.")
    reply_text = reply_template.format(**data)
    send_fn(driver, sender, reply_text)

    if on_complete.get("log_to_sheets"):
        try:
            sheets.log(flow_id, sender, data)
        except Exception as e:
            print(f"[Sheets] Error: {e}")

    if on_complete.get("send_email"):
        try:
            email_notify.send(flow_id, sender, data)
        except Exception as e:
            print(f"[Email] Error: {e}")

    state.clear_flow_data(sender)
    state.set(sender, "idle")
