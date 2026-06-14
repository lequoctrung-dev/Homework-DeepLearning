import streamlit as st
import cv2
import numpy as np
import tensorflow as tf
import os
import time
from telegram_utils import send_telegram_alert
# --- THÊM ĐOẠN NÀY ĐỂ ĐỌC FILE BẢO MẬT .ENV ---
from dotenv import load_dotenv
load_dotenv()

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & ĐỒ ÁN
# ==========================================
st.set_page_config(page_title="UCF5 Action Recognition", layout="wide", page_icon="🎬")

# Đường dẫn mô hình và cấu hình đầu vào theo thực nghiệm
MODEL_PATH = "models/best_cnn_lstm_model.keras"
SEQUENCE_LENGTH = 30
IMAGE_SIZE = (128, 128)  # Thay đổi lại kích thước này nếu kiến trúc CNN của bạn dùng size khác (vd: 128x128)
CLASSES_LIST = ["Bowling", "BoxingPunchingBag", "Biking", "JumpRope", "PlayingGuitar"]

# Thay vì gán chuỗi rỗng, ta lấy giá trị từ file .env thông qua os.environ.get()
# Nếu file .env không tồn tại, nó sẽ trả về chuỗi trống mặc định ""
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ==========================================
# 2. TẢI MÔ HÌNH VÀO BỘ NHỚ (CÓ CACHING)
# ==========================================
@st.cache_resource
def load_ai_model():
    if not os.path.exists(MODEL_PATH):
        st.error(f"Không tìm thấy file mô hình tại: {MODEL_PATH}. Vui lòng kiểm tra lại thư mục!")
        return None
    try:
        # Load mô hình với tên biến thống nhất: loaded_model
        model = tf.keras.models.load_model(MODEL_PATH)
        return model
    except Exception as e:
        st.error(f"Lỗi khi tải mô hình: {e}")
        return None

loaded_model = load_ai_model()

# ==========================================
# 3. HÀM TIỀN XỬ LÝ KHUNG HÌNH (PREPROCESSING)
# ==========================================
def preprocess_frame(frame):
    """Chuẩn hóa 1 khung hình đơn lẻ về đúng định dạng đầu vào của CNN"""
    resized_frame = cv2.resize(frame, (128,128))
    normalized_frame = resized_frame / 255.0  # Ràng buộc chuẩn hóa về đoạn [0, 1]
    return normalized_frame

# ==========================================
# 4. GIAO DIỆN NGƯỜI DÙNG (STREAMLIT UI)
# ==========================================
st.title("🎬 Đồ Án Deep Learning: Hệ Thống Nhận Diện Hành Động Trong Video")
st.markdown("---")

# Thanh SideBar chứa thông số cấu hình hệ thống
st.sidebar.header("⚙️ Cấu Hình Hệ Thống")
st.sidebar.info(
    f"**Mô hình:** Custom CNN + LSTM\n\n"
    f"**Số khung hình đầu vào (Sequence):** {SEQUENCE_LENGTH}\n\n"
    f"**Độ chính xác thực nghiệm:** 95.00%"
)

#st.sidebar.subheader("📢 Cấu hình Cảnh báo Telegram")
#tg_token = st.sidebar.text_input("Telegram Bot Token", value=TELEGRAM_TOKEN, type="password")
#tg_chat_id = st.sidebar.text_input("Telegram Chat ID", value=TELEGRAM_CHAT_ID)

# Tạo các Tab tính năng chính
tab1, tab2 = st.tabs(["📁 Tải Lên File Video", "🎥 Nhận Diện Realtime Qua Webcam"])

# ------------------------------------------
# TÍNH NĂNG 1 & 3: TẢI FILE VIDEO & GỬI CẢNH BÁO
# ------------------------------------------
with tab1:
    st.header("Xử lý và nhận diện hành động từ File")
    uploaded_file = st.file_uploader("Chọn file video (.mp4, .avi, .mov)...", type=["mp4", "avi", "mov"])
    
    if uploaded_file is not None and loaded_model is not None:
        # Lưu file tạm thời xuống local để OpenCV có thể đọc đường dẫn
        tfile = open("temp_video.mp4", "wb")
        tfile.write(uploaded_file.read())
        tfile.close()
        
        st.video(uploaded_file)
        
        with st.spinner("Đang trích xuất khung hình và phân tích diễn biến thời gian..."):
            video_reader = cv2.VideoCapture("temp_video.mp4")
            frames_list = []
            
            # Tính toán toán học để lấy đều 30 khung hình từ toàn bộ video
            video_frames_count = int(video_reader.get(cv2.CAP_PROP_FRAME_COUNT))
            skip_frames_window = max(int(video_frames_count / SEQUENCE_LENGTH), 1)
            
            for frame_counter in range(SEQUENCE_LENGTH):
                video_reader.set(cv2.CAP_PROP_POS_FRAMES, frame_counter * skip_frames_window)
                success, frame = video_reader.read()
                if not success:
                    break
                # Chuyển đổi BGR của OpenCV sang RGB để đồng bộ tập huấn luyện
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                prep_frame = preprocess_frame(frame_rgb)
                frames_list.append(prep_frame)
                
            video_reader.release()
            
            # Kiểm tra nếu đủ 30 khung hình thì tiến hành dự đoán
            if len(frames_list) == SEQUENCE_LENGTH:
                # Định dạng Tensor đầu vào: (1, 30, Width, Height, Channels)
                input_data = np.expand_dims(frames_list, axis=0)
                
                start_time = time.time()
                predictions = loaded_model.predict(input_data)[0]
                inference_time = (time.time() - start_time) * 1000
                
                predicted_label_index = np.argmax(predictions)
                predicted_class_name = CLASSES_LIST[predicted_label_index]
                confidence = predictions[predicted_label_index] * 100
                
                # Hiển thị kết quả lên giao diện Web
                st.success(f"### Kết quả dự đoán: **{predicted_class_name}**")
                st.metric(label="Độ tự tin (Confidence)", value=f"{confidence:.2f}%")
                st.text(f"Thời gian suy luận của mô hình: {inference_time:.2f} ms")
                
                # Kích hoạt Tính năng số 3: Gửi cảnh báo tự động qua Telegram
                if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
                    with st.spinner("Có tín hiệu hành động, đang gửi cảnh báo qua Telegram..."):
                        send_telegram_alert(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, predicted_class_name, confidence)
            else:
                st.error("Video quá ngắn hoặc lỗi định dạng, không thể trích xuất đủ 30 khung hình mẫu.")

# ------------------------------------------
# TÍNH NĂNG 2: NHẬN DIỆN WEB CAMERA TRỰC TIẾP
# ------------------------------------------
with tab2:
    st.header("Nhận diện chuỗi hành động trực tiếp từ Webcam")
    st.caption("Hệ thống sẽ liên tục tích lũy 30 khung hình gần nhất theo thời gian thực đưa vào mạng LSTM.")
    
    run_webcam = st.checkbox("Bật/Tắt Webcam")
    FRAME_WINDOW = st.image([]) # Khung chứa luồng hiển thị video động của Streamlit
    
    if run_webcam and loaded_model is not None:
        # Khởi tạo camera kết nối trực tiếp phần cứng máy tính
        camera = cv2.VideoCapture(0)
        webcam_frames_buffer = [] # Buffer hàng đợi lưu chuỗi thời gian
        
        # Tạo khu vực hiển thị nhãn Realtime động tránh render lại toàn bộ trang
        status_text = st.empty()
        
        while run_webcam:
            success, frame = camera.read()
            if not success:
                st.warning("Không thể truy cập vào thiết bị camera phần cứng.")
                break
                
            # Xử lý hình ảnh hiển thị ra Web giao diện (chuẩn RGB)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Tiền xử lý khung hình hiện tại và thêm vào bộ nhớ đệm (Queue)
            prep_frame = preprocess_frame(frame_rgb)
            webcam_frames_buffer.append(prep_frame)
            
            # Ràng buộc cơ chế trượt: Giữ lại đúng 30 khung hình gần nhất
            if len(webcam_frames_buffer) > SEQUENCE_LENGTH:
                webcam_frames_buffer.pop(0)
                
            # Khi bộ nhớ đệm tích lũy đủ 30 khung hình liên tục
            if len(webcam_frames_buffer) == SEQUENCE_LENGTH:
                input_data = np.expand_dims(webcam_frames_buffer, axis=0)
                predictions = loaded_model.predict(input_data, verbose=0)[0]
                
                predicted_label_index = np.argmax(predictions)
                predicted_class_name = CLASSES_LIST[predicted_label_index]
                confidence = predictions[predicted_label_index] * 100
                
                # Vẽ thông tin kết quả trực tiếp lên khung hình hiển thị
                cv2.putText(frame_rgb, f"{predicted_class_name} ({confidence:.1f}%)", (20, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
                
                # Cập nhật trạng thái text text bên dưới
                status_text.markdown(f"👉 **Đang phát hiện:** `{predicted_class_name}` | Độ tự tin: **{confidence:.2f}%**")
            else:
                cv2.putText(frame_rgb, f"Dang khoi tao Buffer: {len(webcam_frames_buffer)}/{SEQUENCE_LENGTH}", 
                            (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 165, 0), 2, cv2.LINE_AA)
                status_text.info("Đang tích lũy đủ 30 khung hình để kích hoạt mạng LSTM...")
            
            # Đẩy ảnh đã xử lý lên giao diện Web Streamlit
            FRAME_WINDOW.image(frame_rgb)
            
        camera.release()
        st.info("Đã tắt Webcam kết nối.")