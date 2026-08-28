import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("Tra cứu Thông tin Trạm")


# Đọc dữ liệu từ file Excel
@st.cache_data
def load_data():
    df = pd.read_excel("danh_sach_tram.xlsx")
    # Làm sạch tên cột (bỏ khoảng trắng thừa)
    df.columns = df.columns.str.strip()
    return df


try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")

    # Xác định chính xác tên cột "Mã mới" trong file Excel
    col_ma_moi = None
    for col in df.columns:
        if "mã mới" in col.lower() or "ma moi" in col.lower():
            col_ma_moi = col
            break

    # Nếu không tìm thấy cột tên "Mã mới", mặc định lấy cột thứ 2 (hoặc cột 0)
    if not col_ma_moi:
        col_ma_moi = df.columns[1] if len(df.columns) > 1 else df.columns[0]

    # 1. Nhập từ khóa / dán đoạn log cảnh báo
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
        # Bóc tách tất cả mã trạm dạng chữ/số/dấu gạch dưới từ đoạn log
        possible_codes = re.findall(r"\b[A-Za-z0-9_]{3,20}\b", query)

        # Loại bỏ từ khóa hệ thống/ngày giờ thường gặp
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
            if code_upper not in ignore_words and not code_upper.isdigit():
                # Lấy phần mã gốc trước dấu gạch dưới (VD: HYNTHD10_4G -> HYNTHD10)
                base_code = code_upper.split("_")[0]
                if len(base_code) >= 3:
                    cleaned_codes.add(base_code)

        if cleaned_codes:
            # Tạo Regex khớp các mã trạm đã lọc
            pattern = "|".join(re.escape(code) for code in cleaned_codes)

            # LỌC CHÍNH XÁC VÀO CỘT MÃ MỚI
            mask = df[col_ma_moi].astype(str).str.contains(
                pattern, case=False, na=False
            )
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
                st.warning(
                    f"Không tìm thấy mã trạm phù hợp trong cột '{col_ma_moi}'."
                )

except Exception as e:
    st.error(f"Lỗi tải dữ liệu: {e}")
