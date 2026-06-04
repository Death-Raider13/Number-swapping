import json
import sys
import config as cfg_mod
from bot import WhatsAppBot
from scheduler import Scheduler


def load_config() -> dict:
    try:
        with open(cfg_mod.CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[Error] config.json not found at: {cfg_mod.CONFIG_PATH}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[Error] config.json is invalid JSON: {e}")
        sys.exit(1)


def main():
    print("=" * 50)
    print("  WhatsApp Business Bot")
    print("=" * 50)

    cfg = load_config()
    print(f"[Main] Loaded config: '{cfg.get('bot_name', 'Bot')}'")
    print(f"[Main] Menus: {list(cfg.get('menus', {}).keys())}")
    print(f"[Main] Flows: {list(cfg.get('flows', {}).keys())}")

    bot = WhatsAppBot(cfg)
    bot.start()

    scheduler = Scheduler(cfg, bot.send_message, bot.get_driver)
    scheduler.start()

    print("[Main] Bot is running. Press Ctrl+C to stop.")
    try:
        bot.run_loop()
    except KeyboardInterrupt:
        print("\n[Main] Shutting down...")
        scheduler.stop()
        bot.driver.quit()
        print("[Main] Stopped.")


if __name__ == "__main__":
    main()
