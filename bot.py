import time
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException
)
from webdriver_manager.chrome import ChromeDriverManager

import config as cfg_mod
import router


WHATSAPP_URL = "https://web.whatsapp.com"
POLL_INTERVAL = 2  # seconds between message checks

# XPath selectors — these target WhatsApp Web's current DOM structure.
XPATH_CHAT_LIST_LOADED = '//div[@aria-label="Chat list"]'
XPATH_UNREAD_CHATS = '//div[@aria-label="Chat list"]//div[@data-testid="cell-frame-container"][.//span[@data-testid="icon-unread-count" or @aria-label="Unread message"]]'
XPATH_MSG_INPUT = '//div[@data-testid="conversation-compose-box-input" or @contenteditable="true"][@role="textbox"]'
XPATH_LAST_INCOMING = '//div[contains(@class,"message-in")]//span[@class="selectable-text copyable-text"]'
XPATH_ATTACHMENT_BTN = '//div[@data-testid="clip"]//button | //button[@aria-label="Attach"]'
XPATH_ATTACH_IMAGE = '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]'
XPATH_ATTACH_DOC = '//input[@accept="*"]'
XPATH_SEND_BTN = '//button[@data-testid="send" or @aria-label="Send"]'
XPATH_OPEN_CHAT_NAME = '//header//span[@data-testid="conversation-info-header-chat-title"]'


class WhatsAppBot:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.driver = None
        self._seen_msgs = {}  # sender → last seen message text

    def start(self):
        self.driver = _build_driver()
        self.driver.get(WHATSAPP_URL)
        print("[Bot] Waiting for WhatsApp Web to load (scan QR if needed)...")
        try:
            WebDriverWait(self.driver, 120).until(
                EC.presence_of_element_located((By.XPATH, XPATH_CHAT_LIST_LOADED))
            )
        except TimeoutException:
            print("[Bot] Timed out waiting for WhatsApp Web. Check if QR was scanned.")
            raise
        print("[Bot] WhatsApp Web loaded. Bot is running.")

    def get_driver(self):
        return self.driver

    def run_loop(self):
        while True:
            try:
                self._poll()
            except Exception as e:
                print(f"[Bot] Poll error: {e}")
            time.sleep(POLL_INTERVAL)

    def _poll(self):
        # Find chats with unread messages
        try:
            unread = self.driver.find_elements(By.XPATH, XPATH_UNREAD_CHATS)
        except Exception:
            return

        for chat_el in unread:
            try:
                chat_el.click()
                time.sleep(1)
                sender = self._get_chat_name()
                msg = self._get_latest_incoming()
                if msg is None:
                    continue
                last = self._seen_msgs.get(sender)
                if msg == last:
                    continue
                self._seen_msgs[sender] = msg
                print(f"[Bot] Message from {sender}: {msg}")
                router.route(self.driver, sender, msg, self.cfg, self.send_message)
            except StaleElementReferenceException:
                continue
            except Exception as e:
                print(f"[Bot] Error handling chat: {e}")

    def _get_chat_name(self) -> str:
        try:
            el = self.driver.find_element(By.XPATH, XPATH_OPEN_CHAT_NAME)
            return el.text.strip()
        except NoSuchElementException:
            return "Unknown"

    def _get_latest_incoming(self):
        try:
            msgs = self.driver.find_elements(By.XPATH, XPATH_LAST_INCOMING)
            if not msgs:
                return None
            return msgs[-1].text.strip()
        except Exception:
            return None

    def send_message(self, driver, sender: str, text: str, media_path: str = None):
        # If sender is not the currently open chat, open it first
        current = self._get_chat_name()
        if current != sender:
            self._open_chat(sender)

        if media_path:
            self._send_media(media_path)
        if text:
            self._type_and_send(text)

    def _type_and_send(self, text: str):
        try:
            box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, XPATH_MSG_INPUT))
            )
            box.click()
            # Handle multi-line messages
            for i, line in enumerate(text.split("\n")):
                if i > 0:
                    box.send_keys(Keys.SHIFT, Keys.ENTER)
                box.send_keys(line)
            box.send_keys(Keys.ENTER)
            time.sleep(0.5)
        except Exception as e:
            print(f"[Bot] Send error: {e}")

    def _send_media(self, file_path: str):
        try:
            attach_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, XPATH_ATTACHMENT_BTN))
            )
            attach_btn.click()
            time.sleep(0.5)

            # Determine file type
            ext = os.path.splitext(file_path)[1].lower()
            if ext in (".jpg", ".jpeg", ".png", ".gif", ".mp4"):
                inp = self.driver.find_element(By.XPATH, XPATH_ATTACH_IMAGE)
            else:
                inp = self.driver.find_element(By.XPATH, XPATH_ATTACH_DOC)

            inp.send_keys(file_path)
            time.sleep(1.5)

            send_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, XPATH_SEND_BTN))
            )
            send_btn.click()
            time.sleep(1)
        except Exception as e:
            print(f"[Bot] Media send error: {e}")

    def _open_chat(self, name: str):
        # Search for the contact by name in the search box
        try:
            search_xpath = '//div[@data-testid="chat-list-search" or @aria-label="Search input textbox"]'
            box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, search_xpath))
            )
            box.click()
            box.clear()
            box.send_keys(name)
            time.sleep(1.5)

            result_xpath = f'//span[@title="{name}"]'
            result = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, result_xpath))
            )
            result.click()
            time.sleep(1)

            # Close search
            box.send_keys(Keys.ESCAPE)
        except Exception as e:
            print(f"[Bot] Could not open chat for '{name}': {e}")


def _build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument(f"--user-data-dir={os.path.abspath(cfg_mod.CHROME_PROFILE_PATH)}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver
