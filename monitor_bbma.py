"""
Monitor tin nhắn mới từ kênh Telegram public (qua trang preview t.me/s/...)
và gửi thông báo về Telegram bot cá nhân của bạn.

Cách hoạt động:
- Trang t.me/s/<channel_name> là trang preview CÔNG KHAI, không cần đăng nhập/join.
- Script tải trang, parse tin nhắn mới nhất, so sánh với lần trước.
- Nếu có tin mới -> gửi qua Telegram Bot API tới chat cá nhân của bạn.

Yêu cầu:
    pip install requests beautifulsoup4
"""

import os
import json
import requests
from bs4 import BeautifulSoup

# ====== CẤU HÌNH ======
CHANNEL_USERNAME = "Signal_BBMA_OA_H1"   # không có @ hay t.me/
# BOT_TOKEN và CHAT_ID PHẢI được set qua biến môi trường (GitHub Secrets),
# KHÔNG hardcode thẳng giá trị vào đây, đặc biệt nếu repo là Public.
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
STATE_FILE = "last_seen.json"  # lưu id tin nhắn cuối cùng đã gửi
# ========================

PREVIEW_URL = f"https://t.me/s/{CHANNEL_USERNAME}"


def fetch_messages():
    """Lấy danh sách tin nhắn (id, text) từ trang preview công khai."""
    resp = requests.get(PREVIEW_URL, timeout=15, headers={
        "User-Agent": "Mozilla/5.0"
    })
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    messages = []
    for msg_div in soup.select("div.tgme_widget_message"):
        msg_id = msg_div.get("data-post")  # dạng "channel/123"
        text_div = msg_div.select_one("div.tgme_widget_message_text")
        if not msg_id or not text_div:
            continue
        text = text_div.get_text(separator="\n").strip()
        messages.append({"id": msg_id, "text": text})
    return messages


def load_last_seen_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f).get("last_id")
    return None


def save_last_seen_id(msg_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_id": msg_id}, f)


def send_telegram_notification(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": f"🔔 Tín hiệu mới từ {CHANNEL_USERNAME}:\n\n{text}",
    }
    r = requests.post(url, data=payload, timeout=15)
    r.raise_for_status()


def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise SystemExit(
            "Thiếu BOT_TOKEN hoặc CHAT_ID. Hãy set 2 biến này qua GitHub Secrets "
            "(Settings -> Secrets and variables -> Actions), không hardcode vào file."
        )

    messages = fetch_messages()
    if not messages:
        print("Không lấy được tin nhắn nào (có thể kênh trống hoặc lỗi mạng).")
        return

    last_seen_id = load_last_seen_id()
    # Tin nhắn trên trang xếp theo thứ tự cũ -> mới
    new_messages = []
    if last_seen_id is None:
        # Lần đầu chạy: chỉ lưu lại tin mới nhất, không spam thông báo cũ
        new_messages = []
    else:
        found = False
        for m in messages:
            if found:
                new_messages.append(m)
            if m["id"] == last_seen_id:
                found = True
        if not found:
            # last_seen_id không còn trong danh sách (kênh có nhiều tin mới) -> gửi hết
            new_messages = messages

    for m in new_messages:
        try:
            send_telegram_notification(m["text"])
            print(f"Đã gửi thông báo cho tin {m['id']}")
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi gửi thông báo cho tin {m['id']}: {e}")

    save_last_seen_id(messages[-1]["id"])
    print(f"Hoàn tất. Tổng {len(messages)} tin, {len(new_messages)} tin mới.")


if __name__ == "__main__":
    main()
