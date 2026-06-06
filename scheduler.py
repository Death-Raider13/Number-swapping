import threading
import time
import datetime


class Scheduler:
    def __init__(self, cfg: dict, send_fn, driver_getter):
        self.cfg = cfg
        self.send_fn = send_fn
        self.driver_getter = driver_getter
        self._thread = None
        self._stop_event = threading.Event()
        self._sent_today = set()  # (sched_id, date) pairs already sent

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[Scheduler] Started.")

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            self._tick()
            time.sleep(60)

    def _tick(self):
        now = datetime.datetime.now()
        day_abbr = now.strftime("%a")  # Mon, Tue, etc.
        time_str = now.strftime("%H:%M")
        today_str = now.strftime("%Y-%m-%d")

        for sched in self.cfg.get("scheduled_messages", []):
            sched_id = sched.get("id", "")
            key = (sched_id, today_str)
            if key in self._sent_today:
                continue
            if sched.get("time") != time_str:
                continue
            days = sched.get("days", [])
            if day_abbr not in days and "all" not in [d.lower() for d in days]:
                continue

            self._fire(sched)
            self._sent_today.add(key)

    def _fire(self, sched: dict):
        driver = self.driver_getter()
        if driver is None:
            print(f"[Scheduler] No driver available, skipping schedule {sched.get('id')}")
            return

        recipients = sched.get("recipients", [])
        if not recipients:
            recipients = self.cfg.get("known_contacts", [])

        text = sched.get("text", "")
        for recipient in recipients:
            try:
                self.send_fn(driver, recipient, text)
                print(f"[Scheduler] Sent '{sched.get('id')}' to {recipient}")
            except Exception as e:
                print(f"[Scheduler] Failed to send to {recipient}: {e}")
