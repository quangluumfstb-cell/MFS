import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("Tra cứu Thông tin Trạm")


# Đọc dữ liệu từ file Excel
@st.cache_data
def load_data():
    df = pd.read_excel("danh_sach_tram.xlsx")
    # Làm sạch tên cột
    df.columns = df.columns.astype(str).str.strip()
    return df


try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")

    # Tìm cột Mã mới
    col_ma_moi = None
    for col in df.columns:
        col_lower = col.lower()
        if (
            "mã mới" in col_lower
            or "ma moi" in col_lower
            or "mã trạm" in col_lower
            or "ma tram" in col_lower
        ):
            col_ma_moi = col
            break

    if not col_ma_moi and len(df.columns) > 0:
        col_ma_moi = df.columns[0]

    # 1. Nhập từ khóa
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
        # Bóc tách các từ trong đoạn tin nhắn (giữ lại cả dấu gạch dưới nếu có)
        raw_words = re.findall(r"[A-Za-z0-9_]{3,25}", query)

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

        search_terms = set()
        for word in raw_words:
            w_upper = word.upper()
            if w_upper not in ignore_words and not w_upper.isdigit():
                # 1. Thêm từ gốc (VD: HYNTHI04_4G)
                search_terms.add(w_upper.replace("O", "0"))
                # 2. Thêm từ đã cắt đuôi công nghệ (VD: HYNTHI04)
                base = w_upper.split("_")[0]
                if len(base) >= 3:
                    search_terms.add(base.replace("O", "0"))

        if search_terms and col_ma_moi:
            # Chuẩn hóa cột Excel: Xóa khoảng trắng, hoa toàn bộ và chuyển O -> 0
            excel_series = (
                df[col_ma_moi]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .str.replace("O", "0")
            )

            # Tìm kiếm: Mã trong Excel nằm trong Từ khóa NHẬP VÀO HOẶC Từ khóa nằm trong Mã Excel
            masks = []
            for term in search_terms:
                # Trường hợp 1: Từ khóa tìm kiếm có trong Excel
                m1 = excel_series.str.contains(
                    re.escape(term), case=False, na=False
                )
                # Trường hợp 2: Mã trong Excel nằm trong từ khóa tìm kiếm
                m2 = excel_series.apply(
                    lambda cell: cell != "" and cell in term
                )
                masks.append(m1 | m2)

            if masks:
                final_mask = masks[0]
                for m in masks[1:]:
                    final_mask = final_mask | m
                result = df[final_mask]

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
                    f"Không tìm thấy kết quả phù hợp trong cột '{col_ma_moi}'."
                )

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
