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


def extract_pure_station_codes(text):
    """
    Bóc tách chính xác các mã trạm dạng 8 ký tự (VD: HYNTHI04, HYNDTI01, HYNTHN03...)
    Tự động xử lý nhầm lẫn:
    - 2 ký tự cuối ép thành SỐ (O/o/I/l/L/S -> 0/1/5)
    - Loại bỏ đuôi _4G, _3G, _5G và ghi chú trong ngoặc
    """
    # 1. Loại bỏ ghi chú trong ngoặc như (RAN_4G), (3G)...
    text_clean = re.sub(r"\([^)]*\)", " ", text.upper())

    # 2. Thay thế các dấu phân cách bằng khoảng trắng
    text_clean = re.sub(r"[^A-Z0-9]", " ", text_clean)

    tokens = text_clean.split()
    codes = set()

    for tok in tokens:
        # Bỏ đuôi công nghệ nếu dính liền (VD: HYNTHI094G -> HYNTHI09)
        tok = re.sub(r"(4G|3G|5G|RAN)$", "", tok)

        # Lấy các chuỗi ký tự có độ dài từ 6 đến 12 (đặc trưng của mã trạm)
        if len(tok) >= 6 and not tok.isdigit():
            # Tách phần prefix và phần suffix 2 ký tự cuối
            prefix = tok[:-2]
            suffix = tok[-2:]

            # Sửa 2 ký tự cuối về chuẩn SỐ
            suffix_fixed = (
                suffix.replace("O", "0")
                .replace("I", "1")
                .replace("L", "1")
                .replace("S", "5")
            )

            # Sửa chữ O ở phần prefix nếu lỡ bị đọc nhầm gần cuối
            fixed_code = prefix + suffix_fixed

            # Chỉ lấy 8 ký tự chuẩn của mã trạm gốc (nếu dài hơn)
            base_8 = fixed_code[:8]
            if len(base_8) >= 6:
                codes.add(base_8)
                codes.add(fixed_code)

    return codes


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

    # Gộp dữ liệu nhập
    combined_input = (query + "\n" + ocr_text).strip()

    result = pd.DataFrame()

    if combined_input:
        # Trích xuất chính xác tập hợp các mã trạm 8 ký tự
        search_codes = extract_pure_station_codes(combined_input)

        if search_codes and col_ma_moi:
            # Chuẩn hóa cột Mã mới trong Excel (Quy đổi O -> 0 để so sánh đồng bộ)
            excel_series = (
                df[col_ma_moi]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .str.replace("O", "0")
            )

            # Lọc kết quả: Khớp chứa mã gốc 8 ký tự
            masks = [
                excel_series.str.contains(
                    re.escape(code.replace("O", "0")), case=False, na=False
                )
                for code in search_codes
                if code
            ]

            if masks:
                final_mask = reduce(lambda x, y: x | y, masks)
                result = df[final_mask]

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
