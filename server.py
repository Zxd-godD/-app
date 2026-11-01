"""Local confession app server. Run: python server.py"""

from __future__ import annotations

import json
import smtplib
import ssl
import threading
import time
import uuid
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "responses.json"
RECORDS_LOCK = threading.Lock()

EXPECTED = {
    "name": "温洁",
    "gender": "女",
    "myName": "赵旭东",
}


def normalize_date(value: str) -> str:
    value = value.strip().replace("/", "-").replace(".", "-")
    parts = value.split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts):
        return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    return value


def read_records() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def write_records(records: list[dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATA_FILE)


def validate(payload: dict) -> str | None:
    answers = payload.get("answers", {})
    for key, expected in EXPECTED.items():
        answer = answers.get(key, "").strip()
        if answer != expected:
            return "验证答案不正确，暂时无法提交。"
    for key in ("yourBirthday", "favoriteSong", "travelCity"):
        if not answers.get(key, "").strip():
            return "请完成所有问题。"
    try:
        if float(payload.get("affection", 0)) <= 50:
            return "好感度需要超过 50%。"
    except (TypeError, ValueError):
        return "好感度无效。"
    if payload.get("choice") not in {"香水", "键盘", "耳机", "口红"}:
        return "请选择一个最喜欢的选项。"
    return None


def email_body(payload: dict, submitted_at: str) -> str:
    answers = payload["answers"]
    return "\n".join([
        "收到一份新的表白问答结果：",
        "",
        f"提交时间：{submitted_at}",
        f"姓名：{answers['name']}",
        f"性别：{answers['gender']}",
        f"我的名字：{answers['myName']}",
        f"你的生日：{answers['yourBirthday']}",
        f"最喜欢的歌：{answers['favoriteSong']}",
        f"最想去旅游的城市：{answers['travelCity']}",
        f"好感度：{payload['affection']}%",
        f"最喜欢的选项：{payload['choice']}",
    ])


def send_email(payload: dict, submitted_at: str) -> None:
    message = MIMEText(email_body(payload, submitted_at), "plain", "utf-8")
    message["Subject"] = Header("新的表白问答结果", "utf-8")
    message["From"] = config.SMTP_USERNAME
    message["To"] = config.RECIPIENT_EMAIL
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=context, timeout=20) as client:
        client.login(config.SMTP_USERNAME, config.SMTP_AUTH_CODE)
        client.sendmail(config.SMTP_USERNAME, [config.RECIPIENT_EMAIL], message.as_string())


def retry_pending_emails() -> None:
    """Try unsent local records once a minute while the app is open."""
    while True:
        time.sleep(60)
        with RECORDS_LOCK:
            records = read_records()
            changed = False
            for record in records:
                if record.get("emailStatus") not in {"pending", "failed"}:
                    continue
                try:
                    send_email(record, record["submittedAt"])
                    record["emailStatus"] = "sent"
                    changed = True
                except Exception:
                    # Keep the record for the next retry when the network returns.
                    record["emailStatus"] = "failed"
                    changed = True
            if changed:
                write_records(records)


class AppHandler(SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/api/submit":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self.respond_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": "提交内容无效。"})
            return

        problem = validate(payload)
        if problem:
            self.respond_json(HTTPStatus.BAD_REQUEST, {"ok": False, "message": problem})
            return

        submitted_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        record = {
            "id": str(uuid.uuid4()),
            "submittedAt": submitted_at,
            "answers": payload["answers"],
            "affection": float(payload["affection"]),
            "choice": payload["choice"],
            "emailStatus": "pending",
        }
        with RECORDS_LOCK:
            records = read_records()
            records.append(record)
            write_records(records)
            try:
                send_email(payload, submitted_at)
                record["emailStatus"] = "sent"
                write_records(records)
                self.respond_json(HTTPStatus.OK, {"ok": True})
            except Exception:
                record["emailStatus"] = "failed"
                write_records(records)
                # The background retry will send it once the computer is online again.
                self.respond_json(HTTPStatus.OK, {
                    "ok": True,
                    "queued": True,
                })

    def respond_json(self, status: HTTPStatus, body: dict) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


if __name__ == "__main__":
    print("表白 app 已启动。")
    print("电脑访问：http://localhost:8000")
    print("手机访问：使用电脑局域网 IPv4 地址，例如 http://192.168.x.x:8000")
    threading.Thread(target=retry_pending_emails, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", 8000), AppHandler).serve_forever()

