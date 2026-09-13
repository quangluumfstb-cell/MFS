import io
import re
import pandas as pd
from PIL import Image, ImageEnhance, ImageOps
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


# 2. TIỀN XỬ LÝ ẢNH GIÚP READ DARK MODE VÀ TĂNG TỐC
def preprocess_image(image):
    gray = image.convert("L")
    stat = ImageOps.invert(gray)

    max_size = 1500
    if max(stat.size) > max_size:
        stat.thumbnail((max_size, max_size))

    enhancer = ImageEnhance.Contrast(stat)
    return enhancer.enhance(2.0)


# 3. HÀM CHUẨN HÓA NGUYÊN BẢN 1 MÃ TRẠM
def normalize_single_code(code: str) -> str:
    if not code:
        return ""

    # Quy tắc 1: Bỏ các hậu tố mạng ở cuối (-4G, _4G, 4G, -3G, _3G, 3G, -5G, _5G, 5G...)
    clean = re.sub(r"[-_]?[345][gG]$", "", code.strip())

    # Quy tắc 2: Chuyển chữ 'O' / 'o' ở 2 vị trí cuối thành số '0'
    chars = list(clean)
    length = len(chars)
    start_idx = max(0, length - 2)

    for i in range(start_idx, length):
        if chars[i] in ["O", "o"]:
            chars[i] = "0"

    return "".join(chars)


# 4. BÓC TÁCH VÀ CHUẨN HÓA MÃ TRẠM TỪ NỘI DUNG OCR
def extract_station_codes(text):
    if not text:
        return []

    # Tìm tất cả các từ dạng chuỗi có độ dài từ 4-15 ký tự (chấp nhận cả chữ, số, _, -)
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
    }

    codes = set()
    for t in tokens:
        u = t.upper()

        if u in ignore_set or u.isdigit():
            continue

        # 1. Trước hết chuẩn hóa hậu tố 4G/5G và chữ O ở 2 vị trí cuối
        cleaned_token = normalize_single_code(u)

        # 2. Nếu mã có chứa dạng HYN (VD: HYNTTE01, HYNTTEO1, HYNDHG09)
        if "HYN" in cleaned_token:
            # Lấy từ chữ HYN trở đi
            hyn_part = cleaned_token[cleaned_token.find("HYN") :]
            codes.add(hyn_part)

            # Tách thêm bản rút gọn bỏ chữ HYN (VD: TTE01, DHG09) để tra cứu phòng ngừa CSDL lưu tên ngắn
            short_part = hyn_part.replace("HYN", "")
            if len(short_part) >= 4:
                codes.add(short_part)
            continue

        # 3. Nếu là các mã thông thường chuẩn khác (độ dài >= 4)
        if len(cleaned_token) >= 4:
            codes.add(cleaned_token)

    return list(codes)


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
    # 1. TRA CỨU BẰNG CHỮ
    # --------------------------------------------------
    if query and query.strip():
        raw_keywords = [
            k.strip()
            for k in re.split(r"[,;\s\n]+", query)
            if len(k.strip()) >= 2
        ]

        # Áp dụng chuẩn hóa cho cả từ khóa nhập tay
        keywords = []
        for k in raw_keywords:
            norm_k = normalize_single_code(k.upper())
            if norm_k:
                keywords.append(norm_k)
                if norm_k.startswith("HYN"):
                    keywords.append(norm_k.replace("HYN", ""))

        if keywords:
            df_str = df.astype(str).apply(lambda x: x.str.lower())
            combined_mask = pd.Series(False, index=df.index)

            for k in set(keywords):
                k_lower = k.lower()
                mask = df_str.apply(
                    lambda col: col.str.contains(k_lower, regex=False)
                ).any(axis=1)
                combined_mask = combined_mask | mask

            result = df[combined_mask]

    # --------------------------------------------------
    # 2. TRA CỨU BẰNG ẢNH
    # --------------------------------------------------
    elif uploaded_file:
        with st.spinner("Đang tối ưu ảnh và trích xuất mã trạm..."):
            try:
                image = Image.open(uploaded_file)
                processed_img = preprocess_image(image)

                # Chạy OCR
                extracted_text = pytesseract.image_to_string(
                    processed_img, lang="vie+eng"
                )

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

                # Tìm kiếm linh hoạt trong dữ liệu Excel
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
