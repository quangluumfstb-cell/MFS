import pandas as pd
import streamlit as st
from PIL import Image
import pytesseract

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")

st.title("Tra cứu Thông tin Trạm")

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

    if query:
        # Tìm kiếm theo từ khóa nhập tay
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
        result = df[mask]

    elif uploaded_file:
        # Xử lý đọc chữ từ ảnh dùng pytesseract
        with st.spinner("Đang trích xuất dữ liệu từ ảnh..."):
            image = Image.open(uploaded_file)
            extracted_text = pytesseract.image_to_string(image)
            
            st.info(f"Chữ trích xuất từ ảnh:\n```\n{extracted_text.strip()}\n```")

            # Tìm kiếm các từ trích xuất được trong file Excel
            words = [word.strip() for word in extracted_text.split() if len(word.strip()) >= 3]
            if words:
                masks = [df.astype(str).apply(lambda x: x.str.contains(w, case=False, na=False)).any(axis=1) for w in words]
                combined_mask = pd.concat(masks, axis=1).any(axis=1)
                result = df[combined_mask]

    # Hiển thị kết quả (Chỉ hiển thị khi có query hoặc ảnh)
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
