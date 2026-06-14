import streamlit as st
from ultralytics import YOLO
import PIL.Image
import numpy as np
import cv2
import requests
import os
import time
import pandas as pd

# ---- 1. ĐỘT PHÁ THẨM MỸ: GLASSMORPHISM & NEON GLOW EFFECTS ----
st.set_page_config(
    page_title="PestVision Command Center",
    page_icon="🌾",
    layout="wide"
)

st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1.5rem; }
    
    /* Vách ngăn nét đứt dọc phân chia rạch ròi 2 khu lớn tầng trên */
    div[data-testid="column"] { padding: 0px 25px; }
    div[data-testid="column"]:not(:first-child) {
        border-left: 2px dashed #475569; 
    }
    
    /* Khung Banner tiêu đề định danh tối giản công nghệ */
    .brand-banner-vi {
        background: linear-gradient(135deg, #1e3a8a 0%, #020617 100%);
        padding: 25px;
        border-radius: 14px;
        text-align: center;
        margin-bottom: 25px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    
    /* BỘ NEON ACCORDION: THẺ GẬP ĐÓNG MỞ THÔNG MINH CỦA KHANG */
    .neon-accordion {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 5px solid #3b82f6; /* Viền nhấn dọc bên trái mặc định */
        margin-bottom: 16px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        overflow: hidden;
    }
    
    /* Hiệu ứng trượt ngang và phát quang Neon khi Hover chuột */
    .neon-accordion:hover {
        transform: translateX(6px);
        border-left: 5px solid #10b981;
        box-shadow: -5px 0 25px rgba(16, 185, 129, 0.4);
    }
    
    /* Nút bấm tiêu đề gọn gàng */
    .neon-accordion summary {
        padding: 18px 22px;
        cursor: pointer;
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc;
        list-style: none; /* Xóa mũi tên tam giác xấu xí mặc định của trình duyệt */
        display: flex;
        justify-content: space-between;
        align-items: center;
        outline: none;
        user-select: none;
    }
    
    .neon-accordion summary::-webkit-details-marker {
        display: none;
    }
    
    /* Hiệu ứng khi được bấm mở ra (Tách viền đứt) */
    .neon-accordion[open] summary {
        border-bottom: 1px dashed rgba(255, 255, 255, 0.2);
    }
    
    /* Nội dung chi tiết bung ra */
    .neon-accordion-content {
        padding: 20px 22px;
        color: #cbd5e1;
        line-height: 1.6;
        animation: slideDown 0.3s ease-in-out;
        background: rgba(0, 0, 0, 0.2);
    }
    
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
""", unsafe_allow_html=True)

# ---- 2. ĐƯỜNG ỐNG TELEGRAM & HỆ TRI THỨC NÔNG NGHIỆP TOÀN DIỆN ----
TELEGRAM_TOKEN = "8943065384:AAG1PA8ZjJmBCrJkumgRdBYrsCVjTOVwszo"
TELEGRAM_CHAT_ID = "8449019890"

PEST_KNOWLEDGE = {
    'Sau_cuon_la_nho': {'vn': 'Sâu cuốn lá nhỏ', 'sci': 'Cnaphalocrocis medinalis', 'info': 'Cuốn bẹ lá lúa thành tổ và cắn phá mô lá, làm suy giảm nghiêm trọng khả năng quang hợp.', 'action': 'Sử dụng chế phẩm sinh học Bt hoặc bảo vệ ong ký sinh khống chế mật độ.'},
    'Ngai_buom_dem': {'vn': 'Ngài bướm đêm', 'sci': 'Cnaphalocrocis medinalis', 'info': 'Thể trưởng thành sinh sản của dịch hại bộ cánh vảy. Chúng di chuyển linh hoạt ban đêm, đẻ hàng ngàn ổ trứng trên lá lúa, tạo điều kiện bùng phát các ổ sâu đục thân, sâu cuốn lá tàn phá hệ thống đòng.', 'action': 'Kích hoạt hệ thống bẫy đèn ngắt chu kỳ sinh sản; phun hoạt chất nội hấp chọn lọc để triệt tiêu ổ trứng và sâu non mới nở khẩn cấp.'},
    'Sau_duc_than_2_cham': {'vn': 'Sâu đục thân 2 chấm', 'sci': 'Scirpophaga incertulas', 'info': 'Cắt đứt hoàn toàn đường vận chuyển dinh dưỡng nuôi đòng, làm bông lúa bị bạc, lép hạt.', 'action': 'Phun thuốc nội hấp lưu dẫn bảo vệ hệ thống lúc lúa bắt đầu ôm đòng.'},
    'Muoi_hanh': {'vn': 'Muỗi hành', 'sci': 'Orseolia oryzae', 'info': 'Ấu trùng chích hút kích thích bẹ lá phát triển thành ống tròn giống lá hành, lúa không trổ bông.', 'action': 'Tránh sạ mật độ quá dày; tăng cường bọ đuôi kìm và ong ký sinh tự nhiên.'},
    'Ray_nau': {'vn': 'Rầy nâu', 'sci': 'Nilaparvata lugens', 'info': 'Chích hút nhựa gốc thân gây cháy rầy sinh học, đồng thời truyền bệnh vàng lùn, lùn xoắn lá.', 'action': 'Dâng nước che gốc lúa để cô lập dịch; xử lý thuốc trừ rầy chọn lọc.'},
    'Ray_lung_trang': {'vn': 'Rầy lưng trắng', 'sci': 'Sogatella furcifera', 'info': 'Chích hút nhựa lúa giai đoạn đẻ nhánh mạnh, truyền virus lùn sọc đen rất nguy hiểm.', 'action': 'Vệ sinh cỏ bờ ruộng triệt để; can thiệp hóa học khi mật độ vượt ngưỡng.'},
    'Voi_voi_hai_lua': {'vn': 'Vòi voi hại lúa', 'sci': 'Echinocnemus squameus', 'info': 'Thành trùng gặm xước lá tạo vệt trắng dọc gân, ấu trùng tàn phá làm rễ thối đen.', 'action': 'Cày lật đất kỹ trước khi gieo sạ để diệt tận gốc ổ nhộng ẩn nấp dưới bùn.'},
    'Ray_xanh_hai_lua': {'vn': 'Rầy xanh hại lúa', 'sci': 'Nephotettix virescens', 'info': 'Chích hút nhựa bẹ lá mạ, truyền bệnh virus vàng lụi (Tungro) làm lúa lụi tàn.', 'action': 'Thả nhện ăn thịt khống chế tự nhiên; phun hoạt chất phổ rộng nếu bùng phát.'}
}

@st.cache_resource
def load_yolo_model():
    return YOLO("yolov8n_pest_model_v2_final.pt")

model = load_yolo_model()
CONF_THRESHOLD_FIXED = 0.25

# ---- KHỞI TẠO BIẾN TRẠNG THÁI (SESSION STATE) ----
if "live_pest_detected" not in st.session_state:
    st.session_state.live_pest_detected = {}
if "processed_videos" not in st.session_state:
    st.session_state.processed_videos = []
if "webcam_active" not in st.session_state:
    st.session_state.webcam_active = False

# HỆ THỐNG KHÓA ĐỘNG ĐỂ RESET FILE UPLOADER MÀ KHÔNG MẤT LỊCH SỬ
if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

# HÀM MỚI: GỬI BÁO CÁO TỔNG KẾT DUY NHẤT SAU KHI CHẠY XONG
def send_final_telegram_report(detected_pests):
    if not detected_pests:
        return

    message = "🏁 **BÁO CÁO TỔNG KẾT DỊCH HẠI** 🏁\n\n"
    for pest_name, conf in detected_pests.items():
        pest_data = PEST_KNOWLEDGE.get(pest_name, {'vn': pest_name, 'sci': 'N/A', 'info': '...', 'action': 'N/A'})
        message += (
            f"📍 **Chủng loài:** {pest_data['vn']}\n"
            f"🧬 **Tên khoa học:** _{pest_data['sci']}_\n"
            f"🎯 **Độ tin cậy đỉnh (Max):** {conf*100:.2f}%\n"
            f"🛠️ **Phác đồ xử lý:** {pest_data['action']}\n\n"
        )
    
    message += f"📅 **Thời gian chốt kết quả:** {time.strftime('%H:%M:%S — %d/%m/%Y')}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=3)
    except: pass

# ======================================================================
# BANNER ĐỊNH DANH THƯƠNG HIỆU HỆ THỐNG
# ======================================================================
st.markdown("""
    <div class="brand-banner-vi">
        <h1 style="color: #ffffff; margin: 0; font-size: 2.2rem; font-weight: 700; letter-spacing: 0.5px;">
            🌾 Hệ thống Giám sát Côn trùng gây hại cây lúa
        </h1>
        <p style="color: #10b981; margin: 4px 0 0 0; font-size: 1.05rem; font-weight: 500;">
            Hỗ trợ Quyết định Nông nghiệp & Khóa mục tiêu sinh học Đa nền tảng
        </p>
    </div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([1, 2.2])

# ----------------------------------------------------------------------
# KHU 1 (BÊN TRÁI): BỘ ĐIỀU KHIỂN CHỨC NĂNG CHUYÊN SÂU
# ----------------------------------------------------------------------
with col_left:
    st.subheader("🛠️ Phương thức thu thập")
    input_mode = st.radio("Chọn nguồn dữ liệu đầu vào:", ["📤 Tải ảnh/Nhiều ảnh lên", "📹 Tải video lên", "🎥 Bật Webcam trực tiếp"], label_visibility="collapsed")
    st.write(" ")
    
    source_images = None
    source_video = None
    cam_trigger = False

    if input_mode == "📤 Tải ảnh/Nhiều ảnh lên":
        # Áp dụng khóa động (Dynamic Key) vào File Uploader
        source_images = st.file_uploader("Chọn danh sách ảnh cần phân tích...", type=["jpg", "jpeg", "png", "webp", "bmp", "tiff"], accept_multiple_files=True, key=f"img_uploader_{st.session_state.file_uploader_key}")
        
        # Nút xóa ảnh thông minh (chỉ hiện khi có ảnh được chọn)
        if source_images:
            if st.button("❌ Xóa danh sách ảnh vừa chọn", use_container_width=True):
                st.session_state.file_uploader_key += 1 # Tăng key lên 1 sẽ ép Streamlit reset lại ô upload thành trống
                st.rerun()

    elif input_mode == "📹 Tải video lên":
        source_video = st.file_uploader("Chọn tệp video giám sát cánh đồng lúa...", type=["mp4", "avi", "mov"], key=f"vid_uploader_{st.session_state.file_uploader_key}")
        
        if source_video:
            if st.button("❌ Xóa video vừa chọn", use_container_width=True):
                st.session_state.file_uploader_key += 1
                st.rerun()
                
    elif input_mode == "🎥 Bật Webcam trực tiếp":
        cam_trigger = st.checkbox("🟢 KÍCH HOẠT CAMERA GIÁM SÁT", value=False)

    st.write("---")
    if st.button("🗑️ Làm mới bộ nhớ hệ thống", use_container_width=True):
        st.session_state.live_pest_detected = {} # Nút này mới là nút xóa lịch sử thực sự
        st.session_state.processed_videos = []
        st.session_state.webcam_active = False
        st.session_state.file_uploader_key += 1 # Reset cả ô upload luôn cho sạch
        st.rerun()

# ----------------------------------------------------------------------
# KHU 2 (BÊN PHẢI): LUỒNG ĐỒ HỌA MÀN HÌNH ĐỐI CHIẾU SONG SONG
# ----------------------------------------------------------------------
with col_right:
    st.subheader("🖥️ Luồng màn hình giám sát đối chiếu")
    preview_col, result_col = st.columns(2)

    # 🎬 KỊCH BẢN 1: ẢNH
    if input_mode == "📤 Tải ảnh/Nhiều ảnh lên" and source_images:
        progress_bar = st.progress(0)
        num_files = len(source_images)
        
        # Tạo cờ để tránh gửi báo cáo nhiều lần nếu Streamlit re-render
        batch_key = "img_batch_" + "_".join([img.name for img in source_images])
        
        for idx, single_image in enumerate(source_images):
            progress_bar.progress((idx + 1) / num_files)
            pil_img = PIL.Image.open(single_image)
            results = model.predict(pil_img, conf=CONF_THRESHOLD_FIXED)
            result = results[0]
            
            with st.expander(f"📂 Tệp: {single_image.name} (AI phát hiện {len(result.boxes)} đối tượng)", expanded=True):
                p_col, r_col = st.columns(2)
                with p_col: st.image(pil_img, use_container_width=True)
                with r_col: st.image(cv2.cvtColor(result.plot(), cv2.COLOR_BGR2RGB), use_container_width=True)
            
            for box in result.boxes:
                c_name = model.names[int(box.cls[0])]
                c_conf = float(box.conf[0])
                
                # Cập nhật trạng thái đỉnh vào UI. Sẽ KHÔNG XÓA DỮ LIỆU CŨ VÌ TỚ ĐÃ BỎ LỆNH XÓA Ở ĐẦU BLOCK
                if c_name not in st.session_state.live_pest_detected or c_conf > st.session_state.live_pest_detected[c_name]:
                    st.session_state.live_pest_detected[c_name] = c_conf
        
        # GỬI BÁO CÁO SAU KHI XỬ LÝ XONG TẤT CẢ ẢNH
        if batch_key not in st.session_state:
            send_final_telegram_report(st.session_state.live_pest_detected)
            st.session_state[batch_key] = True

    # 🎬 KỊCH BẢN 2: VIDEO
    elif input_mode == "📹 Tải video lên" and source_video is not None:
        if source_video.name not in st.session_state.processed_videos:
            t_file_path = "temp_video.mp4"
            with open(t_file_path, "wb") as f: f.write(source_video.read())
            cap = cv2.VideoCapture(t_file_path)
            
            st_preview = preview_col.empty()
            st_result = result_col.empty()
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                
                st_preview.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)
                v_results = model.track(frame, persist=True, conf=CONF_THRESHOLD_FIXED, tracker="botsort.yaml")
                v_res = v_results[0]
                
                for box in v_res.boxes:
                    if box.id is not None:
                        c_name = model.names[int(box.cls[0])]
                        c_conf = float(box.conf[0])
                        
                        # Chỉ cập nhật lên UI
                        if c_name not in st.session_state.live_pest_detected or c_conf > st.session_state.live_pest_detected[c_name]:
                            st.session_state.live_pest_detected[c_name] = c_conf
                
                st_result.image(cv2.cvtColor(v_res.plot(), cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)
                time.sleep(0.01)
            
            cap.release()
            os.remove(t_file_path)
            
            # GỬI BÁO CÁO SAU KHI CHẠY XONG VIDEO
            send_final_telegram_report(st.session_state.live_pest_detected)
            
            st.session_state.processed_videos.append(source_video.name)
            st.rerun()
        else:
            preview_col.info("⏸️ Video này đã được phân tích xong.")
            result_col.success("✅ Vui lòng xem kết quả tổng hợp bên dưới!")

    # 🎬 KỊCH BẢN 3: WEBCAM
    elif input_mode == "🎥 Bật Webcam trực tiếp":
        if cam_trigger:
            st.session_state.webcam_active = True
            cap = cv2.VideoCapture(0)
            st_preview = preview_col.empty()
            st_result = result_col.empty()
            
            while cam_trigger:
                ret, frame = cap.read()
                if not ret: break
                
                st_preview.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)
                w_results = model.track(frame, persist=True, conf=CONF_THRESHOLD_FIXED, tracker="botsort.yaml")
                w_res = w_results[0]
                
                for box in w_res.boxes:
                    if box.id is not None:
                        c_name = model.names[int(box.cls[0])]
                        c_conf = float(box.conf[0])
                        
                        # Chỉ cập nhật lên UI
                        if c_name not in st.session_state.live_pest_detected or c_conf > st.session_state.live_pest_detected[c_name]:
                            st.session_state.live_pest_detected[c_name] = c_conf
                
                st_result.image(cv2.cvtColor(w_res.plot(), cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)
            cap.release()
            cv2.destroyAllWindows()
            
        else:
            # GỬI BÁO CÁO NGAY KHI NGƯỜI DÙNG TẮT WEBCAM
            if st.session_state.webcam_active:
                send_final_telegram_report(st.session_state.live_pest_detected)
                st.session_state.webcam_active = False
                
            preview_col.warning("🔒 Luồng Camera đang ngắt kết nối an toàn.")
            result_col.info("💤 Trạng thái mô hình: Chờ tín hiệu từ Khu 1.")

# ----------------------------------------------------------------------
# TẦNG DƯỚI PANELS: BỘ ACCORDION THẺ GẬP ĐÓNG MỞ THÔNG MINH
# ----------------------------------------------------------------------
st.write("---")
st.subheader("📊 Kết quả mô hình rà soát dịch tễ học & Khuyến nghị phác đồ can thiệp")

if len(st.session_state.live_pest_detected) > 0:
    info_layout, chart_layout = st.columns([1.8, 1])
    
    txt_log = "BÁO CÁO NHẬT KÝ MÔ HÌNH THỜI GIAN THỰC - DANH MỤC CÔN TRÙNG GÂY HẠI CHI TIẾT\n"
    txt_log += "=========================================================================\n"
    txt_log += f"Thời gian lập báo cáo: {time.strftime('%d/%m/%Y — %H:%M:%S')}\n"
    txt_log += "-------------------------------------------------------------------------\n\n"
    
    chart_data = []

    with info_layout:
        st.write("### 📍 Danh mục đối tượng dịch hại:")
        for name, conf in st.session_state.live_pest_detected.items():
            pest = PEST_KNOWLEDGE.get(name, {'vn': name, 'sci': 'N/A', 'info': 'Chưa cập nhật dữ liệu.', 'action': 'N/A'})
            
            # --- RENDER THẺ GẬP BẰNG HTML NATIVE SIÊU MƯỢT ---
            st.markdown(f"""
            <details class="neon-accordion">
                <summary>
                    <div>🎯 MỤC TIÊU: <span style="color: #ef4444;">{pest['vn']}</span></div>
                    <div style="color: #10b981; display:flex; align-items:center; gap:10px;">
                        <span>🔥 {conf*100:.2f}%</span>
                        <span style="font-size:0.8rem; color:#64748b;">▼</span>
                    </div>
                </summary>
                <div class="neon-accordion-content">
                    <p style="margin-top:0;">🧬 <b>Tên khoa học:</b> <i>{pest['sci']}</i></p>
                    <p>📖 <b>Cơ chế phá hoại sinh học:</b> {pest['info']}</p>
                    <p style="margin-bottom:0; color:#fbbf24; font-weight:500;">🛠️ <b>Biện pháp can thiệp khẩn cấp:</b> {pest['action']}</p>
                </div>
            </details>
            """, unsafe_allow_html=True)
            
            txt_log += (
                f"+ Loài côn trùng: {pest['vn']}\n"
                f"  Tên khoa học: {pest['sci']}\n"
                f"  Độ tin cậy cao nhất: {conf*100:.2f}%\n"
                f"  Cơ chế phá hoại bãi ruộng: {pest['info']}\n"
                f"  Phác đồ điều trị khuyến nghị: {pest['action']}\n"
                f"-------------------------------------------------------------------------\n"
            )
            chart_data.append({"Chủng loài": pest['vn'], "Mật độ tự tin (%)": conf * 100})

    with chart_layout:
        st.write("### 📈 Biểu đồ rủi ro dịch tễ")
        df_chart = pd.DataFrame(chart_data)
        st.bar_chart(df_chart.set_index("Chủng loài"))
        
        st.write(" ")
        st.download_button(
            label="💾 Tải tệp Nhật ký báo cáo (.TXT)",
            data=txt_log,
            file_name=f"Bao_Cao_Mo_Hinh_Dich_Hai_Lua_{time.strftime('%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )
else:
    st.info("🛰️ Hệ thống phân tích nền đang mở vững chắc. Vui lòng nạp dữ liệu từ Khu 1 để khởi chạy ma trận quét đặc trưng.")