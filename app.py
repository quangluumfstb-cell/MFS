from functools import reduce
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("Tra cứu Thông tin Trạm")


# Đọc dữ liệu từ file Excel
@st.cache_data
def load_data():
    df = pd.read_excel("danh_sach_tram.xlsx")
    df.columns = df.columns.astype(str).str.strip()
    return df


def fix_station_code(code_str):
    """Quy tắc: 2 ký tự cuối của mã trạm gốc luôn là SỐ (sửa O -> 0 ở 2 vị trí cuối)"""
    code = code_str.upper().strip()

    # Nếu mã có đuôi công nghệ (VD: HYNTHI09_4G), tách lấy phần gốc
    base = code.split("_")[0]

    # Nếu mã gốc dài từ 5 đến 10 ký tự (thường là 8 ký tự như HYNTHI04)
    if len(base) >= 5:
        prefix = base[:-2]  # Phần chữ đầu (VD: HYNTHI)
        suffix = base[-2:]  # 2 ký tự cuối (VD: O4 hoặc OO)

        # Ép buộc 2 ký tự cuối chuyển chữ O thành số 0
        suffix_fixed = suffix.replace("O", "0")
        return prefix + suffix_fixed

    return base


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

    # 1. Nhập từ khóa / tin nhắn
    st.header("1. Nhập Mã trạm (DCU02, DCU07, TNH06...):")
    query = st.text_area(
        "Dán danh sách mã trạm/tin nhắn vào đây:",
        height=120,
        key="search_query",
    )

    # 2. Tìm kiếm bằng Hình Ảnh (OCR)
    st.header("2. Tìm kiếm bằng Hình Ảnh:")
    uploaded_file = st.file_uploader(
        "Tải ảnh màn hình/danh sách mã trạm lên đây:",
        type=["png", "jpg", "jpeg"],
    )

    ocr_text = ""
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Ảnh đã tải lên", width=300)
        with st.spinner("Đang bóc tách chữ từ hình ảnh..."):
            try:
                ocr_text = pytesseract.image_to_string(image, config="--psm 6")
                if ocr_text.strip():
                    st.info("Đã bóc tách văn bản từ ảnh thành công!")
            except Exception as e:
                st.error(f"Chưa cấu hình Tesseract OCR trên server: {e}")

    # Gộp dữ liệu nhập tay và dữ liệu đọc từ ảnh
    combined_input = (query + "\n" + ocr_text).strip()

    result = pd.DataFrame()

    if combined_input:
        # Bóc tách các từ dạng chữ/số/dấu gạch dưới
        raw_tokens = re.findall(r"[A-Za-z0-9_]+", combined_input)

        ignore_words = {
            "CELL",
            "DOWN",
            "FAILURE",
            "ALARM",
            "RAN",
            "CLEAR",
            "CRITICAL",
            "AC",
            "3G",
            "4G",
            "5G",
        }

        search_codes = set()
        for token in raw_tokens:
            token_clean = token.strip().upper()
            if (
                len(token_clean) >= 3
                and not token_clean.isdigit()
                and token_clean not in ignore_words
            ):
                # Áp dụng hàm sửa mã trạm chuẩn: 2 ký tự cuối luôn là SỐ
                fixed_code = fix_station_code(token_clean)
                search_codes.add(fixed_code)

        if search_codes and col_ma_moi:
            # Chuẩn hóa cột Mã mới trong Excel theo đúng quy tắc 2 số cuối
            df["_code_clean"] = df[col_ma_moi].apply(
                lambda x: fix_station_code(str(x)) if pd.notna(x) else ""
            )

            # Tạo danh sách mặt nạ lọc khớp chứa (contains)
            masks = [
                df["_code_clean"].str.contains(
                    re.escape(code), case=False, na=False
                )
                for code in search_codes
                if code
            ]

            if masks:
                final_mask = reduce(lambda x, y: x | y, masks)
                result = df[final_mask].drop(columns=["_code_clean"])

    # HIỂN THỊ KẾT QUẢ
    if combined_input:
        st.markdown("---")
        st.subheader("Kết quả tra cứu:")
        if not result.empty:
            st.write(f"Tìm thấy **{len(result)}** kết quả phù hợp:")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            st.warning(
                f"Không tìm thấy kết quả phù hợp trong cột '{col_ma_moi}'."
            )

except Exception as e:
    st.error(f"Lỗi hệ thống: {e}")
