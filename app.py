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
    # Chuyển ảnh xám
    gray = image.convert("L")

    # Đảo màu nếu là ảnh nền tối (Dark mode)
    # Tesseract đọc tốt nhất trên nền trắng chữ đen
    stat = ImageOps.invert(gray)

    # Resize để tăng tốc độ xử lý
    max_size = 1500
    if max(stat.size) > max_size:
        stat.thumbnail((max_size, max_size))

    # Tăng độ tương phản
    enhancer = ImageEnhance.Contrast(stat)
    return enhancer.enhance(2.0)


# 3. BÓC TÁCH MÃ TRẠM DẠNG HYN... HOẶC DẠNG RÓT LẠI (VD: DHG09, DHO02)
def extract_station_codes(text):
    if not text:
        return []

    # Tìm tất cả các từ có độ dài từ 4 đến 15 ký tự gồm chữ và số
    tokens = re.findall(r"[A-Za-z0-9_]{4,15}", text)

    ignore_set = {
        "UNAVAILABLE",
        "CURRENT",
        "ALARMS",
        "NODEB",
        "FILTER",
        "HOME",
        "NAME",
        "AVAILABLE",
    }

    codes = set()
    for t in tokens:
        u = t.upper()

        if u in ignore_set or u.isdigit():
            continue

        # Tìm mã dạng HYN... (Ví dụ: HYNDHG09, HYNDHO02, HYNPHN09)
        hyn_match = re.search(r"HYN[A-Z]{3}[0-9O]{2}", u)
        if hyn_match:
            raw_code = hyn_match.group(0)
            # Sửa lỗi O thành 0 ở 2 chữ số cuối
            clean_code = raw_code[:6] + raw_code[6:].replace("O", "0")
            codes.add(clean_code)
            # Thêm mã gốc bỏ HYN (VD: DHG09)
            codes.add(clean_code.replace("HYN", ""))
            continue

        # Tìm mã trạm chuẩn 3 chữ + 2 số (Ví dụ: DHG09, DHO02, PHN09)
        std_match = re.search(r"([A-Z]{3})([0-9O]{2})", u)
        if std_match:
            letters = std_match.group(1)
            digits = std_match.group(2).replace("O", "0")
            codes.add(f"{letters}{digits}")

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
    # 2. TRA CỨU BẰNG ẢNH
    # --------------------------------------------------
    elif uploaded_file:
        with st.spinner("Đang tối ưu ảnh và trích xuất mã trạm..."):
            try:
                image = Image.open(uploaded_file)
                processed_img = preprocess_image(image)

                # Chạy OCR ở chế độ tiêu chuẩn (loại bỏ --psm 6)
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
                        # Tìm khớp chuỗi linh hoạt không dùng regex \b cứng nhắc
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
