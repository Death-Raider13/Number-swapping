import time

_states = {}
_start_time = time.time()


def get(sender: str) -> str:
    return _states.get(sender, "idle")


def set(sender: str, state: str):
    _states[sender] = state


def clear(sender: str):
    _states.pop(sender, None)


def all_users() -> list:
    return list(_states.keys())


def active_count() -> int:
    return sum(1 for s in _states.values() if s != "idle")


def uptime_str() -> str:
    secs = int(time.time() - _start_time)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h {m}m {s}s"


# Per-user temporary data store for flow answers
_flow_data = {}


def get_flow_data(sender: str) -> dict:
    return _flow_data.get(sender, {})


def set_flow_data(sender: str, key: str, value: str):
    if sender not in _flow_data:
        _flow_data[sender] = {}
    _flow_data[sender][key] = value


def clear_flow_data(sender: str):
    _flow_data.pop(sender, None)
