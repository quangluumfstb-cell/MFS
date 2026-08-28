import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("Tra cứu Thông tin Trạm")


# Đọc dữ liệu từ file Excel
@st.cache_data
def load_data():
    df = pd.read_excel("danh_sach_tram.xlsx")
    df.columns = df.columns.str.strip()
    return df


try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")

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
        # Bóc tách tất cả mã trạm dạng chữ/số/dấu gạch dưới từ đoạn log nhập vào
        possible_codes = re.findall(r"\b[A-Za-z0-9_]{3,20}\b", query)

        # Loại bỏ các từ khóa hệ thống/ngày giờ thường xuất hiện trong log
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
            # Tạo chuỗi regex tìm kiếm khớp chứa (contains)
            pattern = "|".join(re.escape(code) for code in cleaned_codes)

            # Tìm kiếm trên tất cả các cột kiểu chuỗi của file Excel
            mask = (
                df.astype(str)
                .apply(
                    lambda x: x.str.contains(pattern, case=False, na=False)
                )
                .any(axis=1)
            )
            result = df[mask]

    # HIỂN THỊ KẾT QUẢ: Hiển thị đầy đủ tất cả các cột
    if query or uploaded_file:
        st.markdown("---")
        st.subheader("Kết quả tra cứu:")
        if not result.empty:
            st.write(f"Tìm thấy **{len(result)}** kết quả phù hợp:")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            if query:
                st.warning(
                    "Không tìm thấy kết quả nào phù hợp với dữ liệu nhập."
                )

except Exception as e:
    st.error(f"Lỗi tải dữ liệu: {e}")
