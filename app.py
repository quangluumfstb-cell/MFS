import pandas as pd
import streamlit as st
from PIL import Image
import pytesseract
import gc

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")

st.title("Tra cứu Thông tin Trạm")

# Đọc dữ liệu từ file Excel
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
    uploaded_file = st.file_uploader("Tải ảnh màn hình/tin nhắn chứa mã trạm lên đây:", type=["png", "jpg", "jpeg"], key="image_uploader")

    result = pd.DataFrame()

    if query:
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
        result = df[mask]

    elif uploaded_file is not None:
        with st.spinner("Đang xử lý & trích xuất dữ liệu từ ảnh..."):
            # Mở và nén kích thước ảnh để tránh tràn RAM
            image = Image.open(uploaded_file)
            image.thumbnail((1024, 1024)) # Thắt nhỏ ảnh xuống tối đa 1024px
            
            # Đọc chữ từ ảnh
            extracted_text = pytesseract.image_to_string(image, lang='vie+eng')
            
            # Giải phóng biến ảnh khỏi bộ nhớ RAM ngay lập tức
            del image
            gc.collect()

            st.info("Chữ trích xuất từ ảnh:")
            st.code(extracted_text if extracted_text.strip() else "Không đọc được chữ nào từ ảnh.")

            # Tìm kiếm các từ khớp với file Excel
            words = [w.strip() for w in extracted_text.split() if len(w.strip()) >= 3]
            if words:
                masks = [df.astype(str).apply(lambda x: x.str.contains(w, case=False, na=False)).any(axis=1) for w in words]
                combined_mask = pd.concat(masks, axis=1).any(axis=1)
                result = df[combined_mask]

        # Nút xóa ảnh chủ động để làm sạch giao diện và giải phóng tài nguyên
        if st.button("🗑️ Xóa ảnh này & Tra cứu mới"):
            st.cache_data.clear()
            st.rerun()

    # Hiển thị kết quả tra cứu
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
