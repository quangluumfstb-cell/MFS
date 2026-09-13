import io
import re
import pandas as pd
from PIL import Image, ImageEnhance
import pytesseract
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm MFS", layout="wide")
st.title("Tra cứu Thông tin Trạm MFS")


# 1. TẢI VÀ CACHE DỮ LIỆU EXCEL (ÉP KIỂU STR ĐỂ TRÁNH LỖI PYARROW VỚI LAT/LONG)
@st.cache_data(ttl=3600)
def load_data():
    try:
        # Ép tất cả các cột về dạng chuỗi (dtype=str) ngay từ lúc đọc file
        df = pd.read_excel("danh_sach_tram.xlsx", dtype=str)
    except Exception:
        df = pd.read_excel("data.xlsx", dtype=str)

    df.columns = df.columns.astype(str).str.strip()
    return df.fillna("")


# 2. HÀM NÉN ẢNH ĐỂ XỬ LÝ SIÊU NHẸ TRÊN RENDER (TRÁNH OUT OF MEMORY)
def resize_image_for_ocr(image):
    gray = image.convert("L")
    w, h = gray.size
    if max(w, h) > 1000:
        gray.thumbnail((1000, 1000))
    enhancer = ImageEnhance.Contrast(gray)
    return enhancer.enhance(1.5)


# 3. CHUẨN HÓA MÃ TRẠM (Bỏ _4G/-4G/3G... & chuyển O -> 0 ở 2 vị trí cuối)
def normalize_single_code(code: str) -> str:
    if not code:
        return ""

    # Bỏ hậu tố mạng ở cuối (ví dụ: _4G, -4G, 4G, _3G, -3G, 3G, _5G...)
    clean = re.sub(r"[-_]?[345][gG]$", "", code.strip())

    # Chuyển chữ 'O' hoặc 'o' ở 2 vị trí cuối cùng thành số '0'
    chars = list(clean)
    length = len(chars)
    start_idx = max(0, length - 2)

    for i in range(start_idx, length):
        if chars[i] in ["O", "o"]:
            chars[i] = "0"

    return "".join(chars)


# 4. BÓC TÁCH MÃ TRẠM (LỌC BỎ NGÀY GIỜ VÀ TỪ NHIỄU LOG MẠNG)
def extract_station_codes(text):
    if not text:
        return []

    # Bóc tách các chuỗi từ 4 đến 15 ký tự (chứa chữ, số, _, -)
    tokens = re.findall(r"[A-Za-z0-9_-]{4,15}", text)

    ignore_set = {
        "UNAVAILABLE",
        "CURRENT",
        "ALARMS",
        "NODEB",
        "FILTER",
        "HOME",
        "NAME",
        "AVAILABLE",
        "FAILED",
        "FAILURE",
        "SOURCE",
        "ALARM",
        "RAN_4G",
        "RAN_3G",
        "RAN_5G",
    }

    codes = set()
    for t in tokens:
        u = t.upper()

        # Bỏ qua từ nhiễu, từ toàn số (ngày/giờ/năm)
        if u in ignore_set or u.isdigit():
            continue

        cleaned_token = normalize_single_code(u)

        # Xử lý mã có tiền tố HYN (VD: HYNTLY10_4G -> HYNTLY10 và TLY10)
        if "HYN" in cleaned_token:
            hyn_part = cleaned_token[cleaned_token.find("HYN") :]
            codes.add(hyn_part)

            short_part = hyn_part.replace("HYN", "")
            if len(short_part) >= 4:
                codes.add(short_part)
            continue

        # Mã thông thường khác từ 4 ký tự trở lên
        if len(cleaned_token) >= 4:
            codes.add(cleaned_token)

    return list(codes)


# --- LUỒNG XỬ LÝ GIAO DIỆN STREAMLIT ---
try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")

    st.header("1. Nhập Mã trạm (DCU02, DCU07, TNH06...):")
    query = st.text_area(
        "Nhập hoặc dán đoạn tin nhắn chứa mã trạm vào đây:",
        key="search_query",
        height=120,
    )

    st.header("2. Tìm kiếm bằng Hình Ảnh:")
    uploaded_file = st.file_uploader(
        "Tải ảnh màn hình/tin nhắn chứa mã trạm lên đây:",
        type=["png", "jpg", "jpeg"],
    )

    result = pd.DataFrame()

    # --------------------------------------------------
    # 1. TRA CỨU BẰNG CHỮ (LOG TIN NHẮN)
    # --------------------------------------------------
    if query and query.strip():
        codes_found = extract_station_codes(query)

        if codes_found:
            st.info(
                f"🎯 Mã trạm nhận diện từ tin nhắn: `{', '.join(codes_found)}`"
            )

            df_str = df.astype(str).apply(lambda x: x.str.lower())
            combined_mask = pd.Series(False, index=df.index)

            for code in codes_found:
                code_lower = code.lower()
                mask = df_str.apply(
                    lambda col: col.str.contains(code_lower, regex=False)
                ).any(axis=1)
                combined_mask = combined_mask | mask

            result = df[combined_mask]

    # --------------------------------------------------
    # 2. TRA CỨU BẰNG ẢNH (OCR)
    # --------------------------------------------------
    elif uploaded_file:
        with st.spinner("Đang xử lý ảnh và bóc tách mã..."):
            try:
                image = Image.open(uploaded_file)
                processed_img = resize_image_for_ocr(image)

                try:
                    extracted_text = pytesseract.image_to_string(
                        processed_img, lang="eng"
                    )
                except Exception:
                    extracted_text = pytesseract.image_to_string(processed_img)

                codes_found = extract_station_codes(extracted_text)

                st.info("Kết quả bóc tách mã trạm từ ảnh:")
                if codes_found:
                    st.success(
                        f"🎯 Phát hiện các mã: `{', '.join(codes_found)}`"
                    )
                else:
                    st.warning("Chưa bóc tách được mã trạm nào từ ảnh này.")

                with st.expander("Xem toàn bộ nội dung OCR đọc được"):
                    st.code(
                        extracted_text
                        if extracted_text.strip()
                        else "Không đọc được chữ."
                    )

                if codes_found:
                    df_str = df.astype(str).apply(lambda x: x.str.lower())
                    combined_mask = pd.Series(False, index=df.index)

                    for code in codes_found:
                        code_lower = code.lower()
                        mask = df_str.apply(
                            lambda col: col.str.contains(
                                code_lower, regex=False
                            )
                        ).any(axis=1)
                        combined_mask = combined_mask | mask

                    result = df[combined_mask]

            except Exception as ocr_err:
                st.error(f"Lỗi đọc ảnh OCR: {ocr_err}")

    # --------------------------------------------------
    # HIỂN THỊ BẢNG KẾT QUẢ
    # --------------------------------------------------
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
