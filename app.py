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
    df = pd.read_excel("data.xlsx")
    return df


try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")
except Exception as e:
    st.error(f"Lỗi tải file dữ liệu data.xlsx: {e}")
    st.stop()

# 2. Ô nhập từ khóa
keyword = st.text_input(
    "1. Nhập Mã trạm (DCU02, DCU07, TNH06...):",
    placeholder="Nhập hpu06 tbh02 tbh09...",
)

# 3. Tải ảnh OCR
uploaded_file = st.file_uploader(
    "2. Tìm kiếm bằng Hình Ảnh:", type=["png", "jpg", "jpeg"]
)
ocr_text = ""

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ảnh đã tải lên", width=300)
    ocr_text = pytesseract.image_to_string(image, lang="vie")

# 4. Gom từ khóa và xử lý lọc nhiều mã trạm cùng lúc
combined_input = f"{keyword} {ocr_text}".strip()

if combined_input:
    # Tách chuỗi nhập vào thành danh sách các mã trạm riêng biệt
    raw_codes = re.split(r"[,;\s\n]+", combined_input)
    search_codes = [c.strip().lower() for c in raw_codes if len(c.strip()) >= 2]

    if search_codes:
        # Chuyển cột Mã trạm sang dạng chữ thường để so sánh
        df_lower = df["Mã trạm"].astype(str).str.lower()

        # Tạo điều kiện lọc: Trạm thỏa mãn nếu chứa BẤT KỲ mã nào trong danh sách
        condition = False
        for code in search_codes:
            condition = condition | df_lower.str.contains(
                re.escape(code), na=False
            )

        results = df[condition]

        st.subheader("Kết quả tra cứu:")
        if not results.empty:
            st.write(
                f"Tìm thấy **{len(results)}** kết quả phù hợp cho các mã: `{', '.join(set(search_codes))}`"
            )
            st.dataframe(results, use_container_width=True)
        else:
            st.warning("Không tìm thấy kết quả phù hợp trong dữ liệu.")
    else:
        st.info("Vui lòng nhập từ khóa từ 2 ký tự trở lên.")
