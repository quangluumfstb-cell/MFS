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


# 2. HÀM TỐI ƯU ẢNH GIÚP OCR QUÉT CỰC NHANH VÀ CHÍNH XÁC
def preprocess_image(image):
    # Chuyển ảnh về ảnh xám (Grayscale)
    gray = image.convert("L")
    # Resize nếu ảnh quá to để tăng tốc độ quét của Tesseract
    max_size = 1200
    if max(gray.size) > max_size:
        gray.thumbnail((max_size, max_size))
    return gray


# 3. THUẬT TOÁN BÓC TÁCH MÃ TRẠM DỄ THỞ & NHẠY HƠN
def extract_station_codes(text):
    if not text:
        return []

    # Tìm tất cả các chuỗi chữ + số có độ dài từ 3 đến 12 ký tự
    raw_tokens = re.findall(r"[A-Za-z0-9_]{3,12}", text)

    # Danh sách từ rác hệ thống OMC / Tesseract hay đọc nhầm
    ignore_words = {
        "UNAVAILABLE",
        "NODEB",
        "FUNCTION",
        "LABEL",
        "CELLID",
        "TRP",
        "CELL",
        "LOCAL",
        "NAME",
        "VIEW",
        "PAGE",
        "DATE",
        "TIME",
    }

    codes = set()
    for token in raw_tokens:
        token_upper = token.upper()

        # Bỏ qua từ rác
        if token_upper in ignore_words or token_upper.isdigit():
            continue

        # Tự động loại bỏ tiền tố tỉnh nếu dính (HYNDHG09 -> DHG09, HYNDCU02 -> DCU02)
        clean_code = re.sub(r"^(HYN|TBH|HPU)", "", token_upper)
        # Loại bỏ các hậu tố mạng (_4G, _5G, _LN)
        clean_code = re.sub(r"(_4G|_5G|_3G|_LN)$", "", clean_code)

        # Sửa lỗi OCR nhầm chữ O thành số 0 ở đuôi mã
        clean_code = re.sub(
            r"([A-Z]{2,4})([0-9O]{1,3})$",
            lambda m: m.group(1) + m.group(2).replace("O", "0"),
            clean_code,
        )

        if len(clean_code) >= 3:
            codes.add(clean_code)
            codes.add(token_upper)  # Giữ cả mã gốc phòng trường hợp Excel lưu mã đầy đủ

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
    # 2. TRA CỨU BẰNG ẢNH (ĐÃ TỐI ƯU TỐC ĐỘ & ĐỘ NHẠY)
    # --------------------------------------------------
    elif uploaded_file:
        with st.spinner("Đang tối ưu ảnh và trích xuất mã trạm..."):
            try:
                image = Image.open(uploaded_file)
                processed_img = preprocess_image(image)

                # Chạy OCR nhanh trên ảnh đã tối ưu
                extracted_text = pytesseract.image_to_string(
                    processed_img, lang="vie+eng", config="--psm 6"
                )

                codes_found = extract_station_codes(extracted_text)

                st.info("Nội dung nhận diện từ ảnh:")
                if codes_found:
                    st.success(
                        f"🎯 Phát hiện các mã: `{', '.join(codes_found)}`"
                    )
                else:
                    st.warning("Chưa bóc tách được mã trạm rõ ràng từ ảnh này.")

                with st.expander("Xem toàn bộ chữ OCR đọc được"):
                    st.code(
                        extracted_text
                        if extracted_text.strip()
                        else "Không đọc được chữ."
                    )

                # Tra cứu linh hoạt trong file Excel
                if codes_found:
                    df_str = df.astype(str).apply(lambda x: x.str.lower())
                    combined_mask = pd.Series(False, index=df.index)

                    for code in codes_found:
                        code_lower = code.lower()
                        mask = df_str.apply(
                            lambda col: col.str.contains(code_lower, regex=False)
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
