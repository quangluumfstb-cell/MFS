import io
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm MFS", layout="wide")
st.title("Tra cứu Thông tin Trạm MFS")


# 1. TẢI VÀ CACHE DỮ LIỆU EXCEL
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_excel("danh_sach_tram.xlsx")
    except Exception:
        df = pd.read_excel("data.xlsx")

    df.columns = df.columns.astype(str).str.strip()
    return df


# 2. TỐI ƯU ẢNH TĂNG TỐC ĐỘ QUÉT OCR
def preprocess_image(image):
    gray = image.convert("L")
    max_size = 1200
    if max(gray.size) > max_size:
        gray.thumbnail((max_size, max_size))
    return gray


# 3. LỌC CHÍNH XÁC CHỈ LẤY MÃ DẠNG HYN... (VD: HYNPHN09, HYNDHG09)
def extract_hyn_codes(text):
    if not text:
        return []

    # Tìm chính xác các chuỗi bắt đầu bằng HYN (Ví dụ: HYNPHN09, HYNDHG09, HYNDHO02)
    # Bắt từ HYN + 3-6 chữ cái + 2 số/O
    raw_matches = re.findall(r"HYN[A-Za-z0-9_]{4,12}", text, re.IGNORECASE)

    extracted_codes = set()

    for item in raw_matches:
        item_upper = item.upper()

        # Cắt bỏ hậu tố mạng nếu dính trong ảnh (_4G, _5G, CM3EA, _LN...)
        clean_code = re.sub(
            r"(_4G|_5G|_3G|_LN|CM[0-9A-Z]+).*$", "", item_upper
        )

        # Chuẩn hóa chữ O thành số 0 ở 2 ký tự số cuối
        clean_code = re.sub(
            r"(HYN[A-Z]{3})([0-9O]{2})",
            lambda m: m.group(1) + m.group(2).replace("O", "0"),
            clean_code,
        )

        if len(clean_code) >= 7:
            extracted_codes.add(clean_code)

            # Đồng thời tạo thêm mã gốc bỏ HYN (VD: PHN09, DHG09) để khớp cả với cột Mã cũ/Trạm gốc trong Excel
            short_code = clean_code.replace("HYN", "")
            extracted_codes.add(short_code)

    return list(extracted_codes)


try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")

    st.header("1. Nhập Mã trạm (DCU02, DCU07, TNH06...):")
    query = st.text_area(
        "Nhập hoặc dán đoạn tin nhắn chứa mã trạm vào đây:",
        key="search_query",
        height=100,
    )

    st.header("2. Tìm kiếm bằng Hình Ảnh:")
    uploaded_file = st.file_uploader(
        "Tải ảnh màn hình/tin nhắn chứa mã trạm lên đây:",
        type=["png", "jpg", "jpeg"],
    )

    result = pd.DataFrame()

    # --------------------------------------------------
    # 1. TRA CỨU BẰNG TIN NHẮN CHỮ
    # --------------------------------------------------
    if query and query.strip():
        keywords = [
            k.strip()
            for k in re.split(r"[,;\s\n]+", query)
            if len(k.strip()) >= 2
        ]

        if keywords:
            df_str = df.astype(str).apply(lambda x: x.str.lower())
            combined_mask = pd.Series(False, index=df.index)

            for k in keywords:
                k_lower = k.lower()
                mask = df_str.apply(
                    lambda col: col.str.contains(k_lower, regex=False)
                ).any(axis=1)
                combined_mask = combined_mask | mask

            result = df[combined_mask]

    # --------------------------------------------------
    # 2. TRA CỨU BẰNG ẢNH (CHỈ BẮT MÃ HYN...)
    # --------------------------------------------------
    elif uploaded_file:
        with st.spinner("Đang quét các mã trạm HYN..."):
            try:
                image = Image.open(uploaded_file)
                processed_img = preprocess_image(image)

                # Quét nhanh với Tesseract
                extracted_text = pytesseract.image_to_string(
                    processed_img, lang="vie+eng", config="--psm 6"
                )

                codes_found = extract_hyn_codes(extracted_text)

                st.info("Kết quả bóc tách mã trạm từ ảnh:")
                if codes_found:
                    # Lọc hiển thị riêng các mã chuẩn dạng HYN... ra giao diện
                    hyn_only = [c for c in codes_found if c.startswith("HYN")]
                    st.success(f"🎯 Phát hiện mã: `{', '.join(hyn_only)}`")
                else:
                    st.warning(
                        "Không tìm thấy mã trạm nào bắt đầu bằng 'HYN' trong ảnh."
                    )

                with st.expander("Xem toàn bộ nội dung OCR đọc được"):
                    st.code(
                        extracted_text
                        if extracted_text.strip()
                        else "Không đọc được chữ."
                    )

                # Tìm chính xác trong Excel
                if codes_found:
                    df_str = df.astype(str).apply(lambda x: x.str.lower())
                    combined_mask = pd.Series(False, index=df.index)

                    for code in codes_found:
                        code_lower = code.lower()
                        # Dùng regex \b để khớp đúng mã trạm, không bị nhầm lẫn
                        pattern = r"\b" + re.escape(code_lower) + r"\b"
                        mask = df_str.apply(
                            lambda col: col.str.contains(pattern, regex=True)
                        ).any(axis=1)
                        combined_mask = combined_mask | mask

                    result = df[combined_mask]

            except Exception as ocr_err:
                st.error(f"Lỗi đọc ảnh OCR: {ocr_err}")

    # HIỂN THỊ KẾT QUẢ
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
