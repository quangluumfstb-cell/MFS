import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")

st.title("Tra cứu Thông tin Trạm")

# Đọc dữ liệu từ file Excel/CSV
@st.cache_data
def load_data():
    # Thay 'data.xlsx' bằng tên file dữ liệu của bạn trên GitHub nếu khác
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

    # Xử lý kết quả tìm kiếm
    result = pd.DataFrame()

    if query:
        # Tìm kiếm theo từ khóa trên tất cả các cột
        mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
        result = df[mask]

    elif uploaded_file:
        # Nếu có chức năng xử lý ảnh (OCR), đặt code xử lý ở đây.
        # Ví dụ tạm thời thông báo khi tải ảnh lên:
        st.info("Đã nhận file ảnh. Đang xử lý trích xuất dữ liệu...")

    # HIỂN THỊ KẾT QUẢ: Chỉ hiện bảng khi nhập từ khóa hoặc tải ảnh
    if query or uploaded_file:
        st.markdown("---")
        st.subheader("Kết quả tra cứu:")
        if not result.empty:
            st.write(f"Tìm thấy **{len(result)}** kết quả phù hợp:")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            if query:
                st.warning("Không tìm thấy kết quả nào phù hợp với từ khóa.")

except Exception as e:
    st.error(f"Lỗi tải dữ liệu: {e}")
