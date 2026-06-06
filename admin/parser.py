def parse(msg: str) -> tuple:
    """
    Returns (command, args_list) from a raw admin message like '!addoption main 1 Label | action'.
    The pipe character separates label from action for !addoption.
    """
    msg = msg.strip()
    if not msg.startswith("!"):
        return None, []

    parts = msg[1:].split(None, 1)
    command = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    return command, rest
