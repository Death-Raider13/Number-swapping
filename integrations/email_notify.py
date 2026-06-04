import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config as cfg_mod


def send(flow_id: str, sender: str, data: dict):
    subject = f"[WhatsApp Bot] New {flow_id} submission from {sender}"
    rows = "\n".join(f"  {k}: {v}" for k, v in data.items())
    body = (
        f"New submission received via WhatsApp bot.\n\n"
        f"Flow: {flow_id}\n"
        f"From: {sender}\n"
        f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Details:\n{rows}"
    )

    msg = MIMEMultipart()
    msg["From"] = cfg_mod.SMTP_USER
    msg["To"] = cfg_mod.ADMIN_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(cfg_mod.SMTP_HOST, cfg_mod.SMTP_PORT) as server:
        server.starttls()
        server.login(cfg_mod.SMTP_USER, cfg_mod.SMTP_PASSWORD)
        server.send_message(msg)

    print(f"[Email] Notification sent for flow '{flow_id}' from {sender}")
