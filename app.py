import io
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st
from docx import Document

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("Tra cứu Thông tin Trạm MFS")


@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_excel("danh_sach_tram.xlsx")
    except Exception:
        df = pd.read_excel("data.xlsx")

    df.columns = df.columns.astype(str).str.strip()
    return df


def extract_station_codes(text):
    """
    Bóc tách chính xác các mã trạm dạng DHG09, DHO02 từ ảnh OMC/Cảnh báo:
    - Loại bỏ tiền tố tỉnh (HYN, TBH...) và hậu tố (4G, 5G, CM3EA...)
    - Chuẩn hóa 2 chữ số cuối (đổi chữ O thành số 0)
    """
    if not text:
        return []

    raw_matches = re.findall(r"[A-Za-z0-9_]{5,20}", text)
    extracted = set()

    for item in raw_matches:
        item_upper = item.upper()

        if any(
            k in item_upper
            for k in [
                "UNAVAILABLE",
                "NODEB",
                "FUNCTION",
                "LABEL",
                "CELLID",
                "TRP",
            ]
        ):
            continue

        # Tìm mẫu 3 ký tự chữ + 2 ký tự số/O (Ví dụ: DHG09, DHO02)
        match = re.search(r"([A-Z]{3})([0-9O]{2})", item_upper)
        if match:
            letters = match.group(1)
            digits = match.group(2).replace("O", "0")
            code = f"{letters}{digits}"
            extracted.add(code)

    return list(extracted)


def filter_dataframe_by_codes(df, codes):
    """
    Hàm lọc chính xác trạm trong Excel:
    - Chỉ tìm trong các cột chứa Mã (Mã cũ, Mã mới, Trạm gốc)
    - Dùng REXEX Word Boundary (\b) để khớp chính xác mã, tránh lôi nhầm trạm khác
    """
    if not codes:
        return pd.DataFrame()

    # Xác định các cột chứa mã trạm để lọc
    code_columns = [
        col
        for col in df.columns
        if any(
            k in col.lower()
            for k in ["ma", "mã", "tram", "trạm", "bbu", "code", "stt"]
        )
    ]
    if not code_columns:
        code_columns = df.columns.tolist()

    combined_mask = pd.Series(False, index=df.index)

    for code in codes:
        # \b mã \b giúp tìm chính xác mã độc lập, không dính vào chuỗi khác
        pattern = r"\b" + re.escape(code) + r"\b"

        for col in code_columns:
            mask = df[col].astype(str).str.contains(pattern, case=False, na=False)
            combined_mask = combined_mask | mask

    return df[combined_mask]


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

    # 1. TRA CỨU BẰNG TIN NHẮN CHỮ
    if query and query.strip():
        keywords = [
            k.strip()
            for k in re.split(r"[,;\s\n]+", query)
            if len(k.strip()) >= 2
        ]

        if keywords:
            result = filter_dataframe_by_codes(df, keywords)

    # 2. TRA CỨU BẰNG HÌNH ẢNH
    elif uploaded_file:
        with st.spinner("Đang phân tích hình ảnh và trích xuất mã trạm..."):
            try:
                image = Image.open(uploaded_file)
                extracted_text = pytesseract.image_to_string(
                    image, lang="vie+eng"
                )

                codes_found = extract_station_codes(extracted_text)

                st.info("Kết quả phân tích từ ảnh:")
                if codes_found:
                    st.success(
                        f"🎯 Đã bóc tách được **{len(codes_found)}** mã trạm chuẩn: `{', '.join(codes_found)}`"
                    )
                else:
                    st.warning(
                        "Không phát hiện được mã trạm dạng chuẩn (như DHG09, DHO02) trong ảnh."
                    )

                with st.expander("Xem toàn bộ chữ đọc được từ OCR"):
                    st.code(extracted_text)

                # Nút tải file Word
                if extracted_text.strip():
                    doc = Document()
                    doc.add_heading("Kết quả trích xuất từ ảnh", level=1)
                    doc.add_paragraph(
                        f"Mã trạm phát hiện: {', '.join(codes_found)}\n\n"
                    )
                    doc.add_paragraph(extracted_text)

                    bio = io.BytesIO()
                    doc.save(bio)

                    st.download_button(
                        label="📥 Tải file Word kết quả OCR",
                        data=bio.getvalue(),
                        file_name="ket_qua_doc_anh.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )

                # Lọc chính xác danh sách kết quả
                if codes_found:
                    result = filter_dataframe_by_codes(df, codes_found)

            except Exception as ocr_err:
                st.error(f"Lỗi hệ thống khi đọc ảnh: {ocr_err}")

    # HIỂN THỊ KẾT QUẢ
    if query or uploaded_file:
        st.markdown("---")
        st.subheader("Kết quả tra cứu:")
        if not result.empty:
            st.write(f"Tìm thấy **{len(result)}** trạm phù hợp chính xác:")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            st.warning("Không tìm thấy dữ liệu khớp chính xác trong file Excel.")

except Exception as e:
    st.error(f"Lỗi hệ thống hoặc tải dữ liệu: {e}")
