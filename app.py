from functools import reduce
import re
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("Tra cứu Thông tin Trạm")


# Đọc dữ liệu từ file Excel
@st.cache_data
def load_data():
    df = pd.read_excel("danh_sach_tram.xlsx")
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
    query = st.text_area(
        "Dán danh sách mã trạm/tin nhắn vào đây:", height=150, key="search_query"
    )

    # 2. Tìm kiếm bằng Hình Ảnh
    st.header("2. Tìm kiếm bằng Hình Ảnh:")
    uploaded_file = st.file_uploader(
        "Tải ảnh màn hình/tin nhắn chứa mã trạm lên đây:",
        type=["png", "jpg", "jpeg"],
    )

    result = pd.DataFrame()

    if query:
        # Tách từng từ/mã trạm trong ô nhập
        raw_tokens = re.split(r"[\s,\n]+", query)

        search_codes = set()
        for token in raw_tokens:
            token_clean = token.strip().upper()
            if len(token_clean) >= 3:
                # 1. Chuẩn hóa O -> 0
                code_norm = token_clean.replace("O", "0")
                search_codes.add(code_norm)

                # 2. Bỏ đuôi công nghệ _4G / _3G nếu có
                base_code = code_norm.split("_")[0]
                if len(base_code) >= 3:
                    search_codes.add(base_code)

        if search_codes and col_ma_moi:
            # Chuẩn hóa cột Mã mới trong Excel
            excel_series = (
                df[col_ma_moi]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .str.replace("O", "0")
            )

            # Tạo danh sách các mặt nạ lọc (mask)
            masks = [
                excel_series.str.contains(re.escape(code), case=False, na=False)
                for code in search_codes
                if code
            ]

            if masks:
                # Gộp tất cả điều kiện OR bằng reduce
                final_mask = reduce(lambda x, y: x | y, masks)
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
