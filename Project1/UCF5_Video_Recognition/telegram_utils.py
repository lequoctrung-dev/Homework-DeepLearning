import requests

def send_telegram_alert(token, chat_id, action_name, confidence):
    """
    Gửi tin nhắn cảnh báo nhận diện hành động qua Telegram API.
    """
    if not token or not chat_id:
        print("[WARNING] Telegram Token hoặc Chat ID chưa được cấu hình.")
        return False
        
    message = (
        "🚨 **[HỆ THỐNG CẢNH BÁO AI]** 🚨\n"
        "-------------------------------------\n"
        f"🎬 **Hành động phát hiện:** {action_name}\n"
        f"🎯 **Độ tự tin (Confidence):** {confidence:.2f}%\n"
        "-------------------------------------\n"
        "📱 Hệ thống nhận diện thời gian thực đang hoạt động ổn định."
    )
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"[INFO] Đã gửi cảnh báo Telegram cho hành động: {action_name}")
            return True
        else:
            print(f"[ERROR] Gửi Telegram thất bại. Mã lỗi: {response.status_code}")
            return False
    except Exception as e:
        print(f"[EXCEPTION] Lỗi khi kết nối Telegram API: {e}")
        return False