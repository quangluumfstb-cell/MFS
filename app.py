import io
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")


# 1. Load dữ liệu từ Excel
@st.cache_data
def load_data():
    return pd.read_excel("danh_sach_tram.xlsx")


try:
    df = load_data()
    total_stations = len(df)
    data_loaded = True
except Exception as e:
    st.error(f"Lỗi khi tải file danh_sach_tram.xlsx: {e}")
    df = pd.DataFrame()
    total_stations = 0
    data_loaded = False

# Tiêu đề giao diện
st.title("Tra cứu Thông tin Trạm")

if data_loaded:
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {total_stations} trạm.")

# --- MỤC 1: NHẬP MÃ TRẠM ---
st.markdown("### 1. Nhập Mã trạm (DCU02, DCU07, TNH06...):")
input_text = st.text_input("Nhập từ khóa", key="text_search")

# --- MỤC 2: TÌM KIẾM BẰNG HÌNH ẢNH ---
st.markdown("### 2. Tìm kiếm bằng Hình Ảnh:")
uploaded_file = st.file_uploader(
    "Tải ảnh màn hình/tin nhắn chứa mã trạm lên đây:",
    type=["png", "jpg", "jpeg"],
    key="img_search",
)

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ảnh đã tải lên", width=350)
    with st.spinner("Đang trích xuất mã trạm từ hình ảnh..."):
        try:
            ocr_text = pytesseract.image_to_string(image)
            if ocr_text.strip():
                input_text = ocr_text
                st.info("Đã bóc tách văn bản từ ảnh thành công!")
        except Exception as e:
            st.error(f"Lỗi OCR (Chưa cài đặt Tesseract trên máy/server): {e}")

# --- XỬ LÝ TRA CỨU VÀ HIỂN THỊ BẢNG KẾT QUẢ ---
if input_text:
    # 1. Trích xuất tất cả chuỗi từ 3 đến 20 ký tự (chứa chữ, số và dấu gạch dưới)
    possible_codes = re.findall(r"\b[A-Za-z0-9_]{3,20}\b", input_text)

    # Từ khóa hệ thống cần bỏ qua khi lọc
    ignore_words = {
        "CELL",
        "DOWN",
        "FAILURE",
        "ALARM",
        "RAN",
        "CLEAR",
        "CRITICAL",
        "AC",
    }

    cleaned_codes = set()
    for code in possible_codes:
        code_upper = code.upper()
        # Bỏ qua từ khóa hệ thống và các chuỗi thuần số
        if code_upper not in ignore_words and not code_upper.isdigit():
            # Tách lấy phần mã gốc đứng trước dấu gạch dưới (Ví dụ: HYNTHD10_4G -> HYNTHD10)
            base_code = code_upper.split("_")[0]
            if len(base_code) >= 3:
                cleaned_codes.add(base_code)

    if cleaned_codes and not df.empty:
        col_ma_cu = "Mã cũ" if "Mã cũ" in df.columns else df.columns[0]
        col_ma_moi = "Mã mới" if "Mã mới" in df.columns else df.columns[1]

        # 2. Tìm kiếm chứa (contains) để ghép tất cả các mã lọc được
        pattern = "|".join(re.escape(code) for code in cleaned_codes)
        mask = df[col_ma_cu].astype(str).str.contains(
            pattern, case=False, na=False
        ) | df[col_ma_moi].astype(str).str.contains(
            pattern, case=False, na=False
        )

        matched_df = df[mask]

        if not matched_df.empty:
            st.success(f"🎯 Tìm thấy {len(matched_df)} kết quả phù hợp:")

            display_cols = [
                c
                for c in [col_ma_cu, col_ma_moi, "Địa chỉ", "Hình ảnh"]
                if c in df.columns
            ]
            st.dataframe(
                matched_df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

            # Hiển thị hình ảnh trạm đính kèm nếu có
            if "Hình ảnh" in matched_df.columns:
                for idx, row in matched_df.iterrows():
                    img_path = row.get("Hình ảnh")
                    if pd.notna(img_path):
                        st.write(
                            f"**Hình ảnh trạm {row.get(col_ma_moi, '')}:**"
                        )
                        st.image(img_path, width=350)
        else:
            st.warning("Không tìm thấy dữ liệu trạm phù hợp.")
    else:
        st.warning("Không tìm thấy mã trạm hợp lệ từ nội dung nhập.")
else:
    # Mặc định hiển thị toàn bộ bảng khi chưa nhập thông tin tìm kiếm
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
