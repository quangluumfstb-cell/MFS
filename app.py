import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("Tra cứu Thông tin Trạm")


# Đọc dữ liệu từ file Excel
@st.cache_data
def load_data():
    df = pd.read_excel("danh_sach_tram.xlsx")
    # Xóa khoảng trắng thừa ở tên cột
    df.columns = df.columns.astype(str).str.strip()
    return df


try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")

    # Tự động nhận diện cột Mã mới / Mã trạm
    col_ma_moi = None
    for col in df.columns:
        col_lower = col.lower()
        if "mã mới" in col_lower or "ma moi" in col_lower or "mã trạm" in col_lower or "ma tram" in col_lower:
            col_ma_moi = col
            break

    # Nếu không tìm thấy, lấy mặc định cột đầu tiên
    if not col_ma_moi and len(df.columns) > 0:
        col_ma_moi = df.columns[0]

    # 1. Nhập từ khóa / dán log
    st.header("1. Nhập Mã trạm (DCU02, DCU07, TNH06...):")
    query = st.text_input("Nhập từ khóa", key="search_query")

    # 2. Tìm kiếm bằng Hình Ảnh
    st.header("2. Tìm kiếm bằng Hình Ảnh:")
    uploaded_file = st.file_uploader(
        "Tải ảnh màn hình/tin nhắn chứa mã trạm lên đây:",
        type=["png", "jpg", "jpeg"],
    )

    result = pd.DataFrame()

    if query:
        # Trích xuất các chuỗi ký tự dạng mã trạm
        possible_codes = re.findall(r"\b[A-Za-z0-9_]{3,20}\b", query)

        ignore_words = {
            "CELL", "DOWN", "FAILURE", "ALARM", "RAN", "CLEAR", "CRITICAL", "AC"
        }

        cleaned_codes = set()
        for code in possible_codes:
            code_upper = code.upper()
            if code_upper not in ignore_words and not code_upper.isdigit():
                base_code = code_upper.split("_")[0]
                if len(base_code) >= 3:
                    cleaned_codes.add(base_code)

        if cleaned_codes and col_ma_moi:
            pattern = "|".join(re.escape(code) for code in cleaned_codes)
            # Ép kiểu chuỗi cho toàn bộ cột để tránh lỗi so sánh
            mask = df[col_ma_moi].fillna("").astype(str).str.contains(pattern, case=False, na=False)
            result = df[mask]

    # HIỂN THỊ KẾT QUẢ
    if query or uploaded_file:
        st.markdown("---")
        st.subheader("Kết quả tra cứu:")
        if not result.empty:
            st.write(f"Tìm thấy **{len(result)}** kết quả phù hợp:")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            if query:
                st.warning(f"Không tìm thấy kết quả phù hợp trong cột '{col_ma_moi}'.")

except Exception as e:
    st.error(f"Lỗi hệ thống khi tải/xử lý dữ liệu: {e}")
