import datetime
import config as cfg_mod

_client = None
_sheet = None


def _get_sheet():
    global _client, _sheet
    if _sheet:
        return _sheet
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(cfg_mod.GOOGLE_CREDENTIALS_FILE, scopes=scopes)
        _client = gspread.authorize(creds)
        _sheet = _client.open(cfg_mod.GOOGLE_SHEET_NAME).sheet1
        return _sheet
    except Exception as e:
        print(f"[Sheets] Could not connect: {e}")
        return None


def log(flow_id: str, sender: str, data: dict):
    sheet = _get_sheet()
    if not sheet:
        return
    row = [
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        flow_id,
        sender,
    ] + [f"{k}: {v}" for k, v in data.items()]
    sheet.append_row(row)
    print(f"[Sheets] Logged row for flow '{flow_id}' from {sender}")
