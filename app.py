import io
import re
import pandas as pd
import pytesseract
from PIL import Image
import streamlit as st

st.set_page_config(page_title="Tra cứu Mã Trạm", layout="wide")
st.title("Hệ thống Tra cứu Mã Trạm MFS")


# 1. Tải dữ liệu Excel
@st.cache_data
def load_data():
    # Tải file Excel trong repo
    df = pd.read_excel("data.xlsx")
    return df


try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")
except Exception as e:
    st.error(f"Lỗi tải file dữ liệu data.xlsx: {e}")
    st.stop()

# 2. Nhập từ khóa tìm kiếm (Cho phép nhập nhiều mã phân tách bằng dấu phẩy, khoảng trắng)
keyword = st.text_input(
    "1. Nhập Mã trạm (DCU02, DCU07, TNH06...):",
    placeholder="Nhập hpu06, tbh09...",
)

# 3. Tìm kiếm bằng hình ảnh (OCR)
uploaded_file = st.file_uploader(
    "2. Tìm kiếm bằng Hình Ảnh:", type=["png", "jpg", "jpeg"]
)
ocr_text = ""

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ảnh đã tải lên", width=300)
    # Trích xuất chữ từ ảnh bằng Tesseract OCR
    ocr_text = pytesseract.image_to_string(image, lang="vie")

# 4. Xử lý gom tất cả mã trạm từ cả Ô nhập liệu + Ảnh OCR
combined_input = f"{keyword} {ocr_text}".strip()

if combined_input:
    # Tách chuỗi thành danh sách các từ khóa riêng biệt dựa trên dấu phẩy, dấu cách, xuống dòng
    search_codes = [
        code.strip().lower()
        for code in re.split(r"[,;\s\n]+", combined_input)
        if len(code.strip()) >= 2  # Bỏ qua các ký tự rác quá ngắn
    ]

    if search_codes:
        # Biểu thức chính quy để lọc tất cả các trạm chứa 1 trong các từ khóa
        pattern = "|".join(map(re.escape, search_codes))
        results = df[
            df["Mã trạm"]
            .astype(str)
            .str.lower()
            .str.contains(pattern, na=False, regex=True)
        ]

        st.subheader("Kết quả tra cứu:")
        st.write(
            f"Tìm thấy **{len(results)}** kết quả cho các từ khóa: `{', '.join(set(search_codes))}`"
        )
        st.dataframe(results, use_container_width=True)
    else:
        st.info("Không nhận diện được mã trạm hợp lệ.")
