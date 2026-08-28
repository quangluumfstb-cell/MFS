import pandas as pd
import streamlit as st
import easyocr
from PIL import Image
import numpy as np

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")

st.title("Tra cứu Thông tin Trạm")

# Khởi tạo mô hình EasyOCR (hỗ trợ tiếng Việt và tiếng Anh)
@st.cache_resource
def load_ocr():
    return easyocr.Reader(['vi', 'en'])

reader = load_ocr()

# Đọc dữ liệu từ file Excel/CSV
@st.cache_data
def load_data():
    df = pd.read_excel("data.xlsx")
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")

    # 1. Nhập từ khóa tìm kiếm
    st.header("1. Nhập Mã trạm (DCU02, DCU07, TNH06...):")
    query = st.text_input("Nhập từ khóa", key="search_query")

    # 2. Tìm kiếm bằng Hình Ảnh
    st.header("2. Tìm kiếm bằng Hình Ảnh:")
    uploaded_file = st.file_uploader("Tải ảnh màn hình/tin nhắn chứa mã trạm lên đây:", type=["png", "jpg", "jpeg"])

    result = pd.DataFrame()
    extracted_text = ""

    if query:
        # Tìm kiếm theo từ khóa nhập tay
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
        result = df[mask]

    elif uploaded_file:
        # Xử lý đọc chữ từ ảnh (OCR)
        with st.spinner("Đang trích xuất dữ liệu từ ảnh..."):
            image = Image.open(uploaded_file)
            image_np = np.array(image)
            
            # Trích xuất toàn bộ văn bản có trong ảnh
            ocr_results = reader.readtext(image_np, detail=0)
            extracted_text = " ".join(ocr_results)
            
            st.info(f"Chữ trích xuất từ ảnh: **{extracted_text}**")

            # Tìm kiếm các mã trạm xuất hiện trong đoạn chữ đọc được
            if extracted_text:
                masks = []
                for word in ocr_results:
                    if len(word) >= 3: # Lọc các từ/mã có độ dài từ 3 ký tự trở lên
                        masks.append(df.astype(str).apply(lambda x: x.str.contains(word, case=False, na=False)).any(axis=1))
                
                if masks:
                    combined_mask = pd.concat(masks, axis=1).any(axis=1)
                    result = df[combined_mask]

    # Hiển thị kết quả
    if query or uploaded_file:
        st.markdown("---")
        st.subheader("Kết quả tra cứu:")
        if not result.empty:
            st.write(f"Tìm thấy **{len(result)}** kết quả phù hợp:")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            st.warning("Không tìm thấy kết quả phù hợp trong dữ liệu.")

except Exception as e:
    st.error(f"Lỗi hệ thống hoặc tải dữ liệu: {e}")
