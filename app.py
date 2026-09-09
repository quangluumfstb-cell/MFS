import io
import os
import re
import pandas as pd
import pytesseract
from PIL import Image
import streamlit as st

st.set_page_config(page_title="Tra cứu Mã Trạm MFS", layout="wide")
st.title("Hệ thống Tra cứu Mã Trạm MFS")


# 1. Tải dữ liệu Excel (Tự động nhận diện tên file)
@st.cache_data
def load_data():
    file_name = (
        "danh_sach_tram.xlsx"
        if os.path.exists("danh_sach_tram.xlsx")
        else "data.xlsx"
    )
    df = pd.read_excel(file_name)
    df.columns = df.columns.str.strip()
    return df, file_name


try:
    df, file_used = load_data()
    st.success(f"Đã tải thành công file `{file_used}` ({len(df)} trạm).")
except Exception as e:
    st.error(f"Lỗi tải dữ liệu Excel: {e}")
    st.stop()

# 2. Giao diện nhập liệu
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.header("1. Nhập Mã / Dán Tin Nhắn")
    query = st.text_area(
        "Nhập mã trạm hoặc dán toàn bộ tin nhắn vào đây:",
        placeholder="Ví dụ: hpu06 tbh02 tbh09 hoặc dán đoạn tin nhắn Zalo...",
        height=150,
    )

with col2:
    st.header("2. Quét từ Ảnh (OCR)")
    uploaded_file = st.file_uploader(
        "Tải ảnh màn hình tin nhắn:", type=["png", "jpg", "jpeg"]
    )


# 3. Hàm lọc mã trạm chuẩn (ví dụ: HPU06, TBH02, DCU07...)
def extract_codes(text):
    if not text:
        return []
    # Tìm tất cả chuỗi gồm chữ và số có độ dài từ 3 đến 12 ký tự
    raw_matches = re.findall(r"\b[A-Za-z0-9_]{3,12}\b", text)
    # Loại bỏ các từ tiếng Anh/Việt hệ thống thông thường
    ignore_words = {
        "tram",
        "tin",
        "nhan",
        "ngay",
        "chuyen",
        "name",
        "code",
        "view",
        "page",
        "mfs",
        "file",
        "png",
        "jpg",
    }
    codes = [m.upper() for m in raw_matches if m.lower() not in ignore_words]
    return list(dict.fromkeys(codes))  # Giữ thứ tự và bỏ trùng


# 4. Xử lý OCR nếu có tải ảnh
ocr_text = ""
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ảnh đã tải lên", width=250)
    try:
        gray_img = image.convert("L")
        ocr_text = pytesseract.image_to_string(gray_img, lang="vie+eng")
        if ocr_text.strip():
            st.info(f"Nội dung nhận diện từ ảnh: `{ocr_text.strip()}`")
    except Exception as e:
        st.warning(f"Chưa đọc được OCR: {e}")

# 5. Tiến hành tra cứu
combined_input = f"{query} {ocr_text}".strip()

if combined_input:
    search_codes = extract_codes(combined_input)

    if search_codes:
        st.markdown("---")
        st.subheader("Kết quả tra cứu:")
        st.write(
            f"🔍 Đang lọc theo **{len(search_codes)}** mã: `{', '.join(search_codes)}`"
        )

        # Chuyển dữ liệu sang text để tìm kiếm không phân biệt hoa thường
        df_str = df.astype(str)

        # Tạo điều kiện tìm kiếm: Chứa BẤT KỲ mã nào trong danh sách
        pattern = "|".join([re.escape(c) for c in search_codes])
        mask = df_str.apply(
            lambda row: row.str.contains(pattern, case=False, na=False)
        ).any(axis=1)

        results = df[mask]

        if not results.empty:
            st.success(f"Tìm thấy **{len(results)}** kết quả phù hợp:")
            st.dataframe(results, use_container_width=True, hide_index=True)
        else:
            st.warning("Không tìm thấy mã trạm nào khớp trong danh sách Excel.")
    else:
        st.info("Chưa nhận diện được mã trạm hợp lệ (cần từ 3 ký tự trở lên).")
