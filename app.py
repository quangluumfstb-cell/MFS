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
    Hàm chuyên dụng bóc tách mã trạm từ ảnh chụp màn hình OMC/Cảnh báo:
    - Nhận diện các mẫu như HYNDHG09, HYNDHO02, DHG09, DHO02...
    - Chuẩn hóa: Bỏ tiền tố tỉnh (HYN, TBH...), bỏ hậu tố (4G, 5G, CM3EA...)
    - Sửa lỗi OCR hay nhầm giữa chữ O và số 0 ở định dạng ABC00
    """
    if not text:
        return []

    # 1. Tìm các chuỗi dạng mã trạm (Ví dụ: HYNDHG09, HYNDHO02, DHG09...)
    # Tìm các từ có 3 chữ cái + 2 số (Ví dụ: DHG09, DHO02) hoặc tiền tố tỉnh + 3 chữ cái + 2 số
    raw_matches = re.findall(r"[A-Za-z0-9_]{5,15}", text)

    extracted = set()

    for item in raw_matches:
        item_upper = item.upper()

        # Loại bỏ các từ khóa hệ thống không phải mã trạm
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

        # Tìm mẫu gốc gồm 3 ký tự chữ + 2 ký tự số ở cuối (VD: DHG09, DHO02, DHO02_4G)
        # Bỏ qua tiền tố như HYN phía trước nếu có
        match = re.search(r"([A-Z]{3})([0-9O]{2})", item_upper)
        if match:
            letters = match.group(1)
            digits = match.group(2)

            # Sửa lỗi OCR nhận diện nhầm chữ O thành số 0 hoặc ngược lại ở 2 chữ số cuối
            digits = digits.replace("O", "0")

            code = f"{letters}{digits}"
            extracted.add(code)

    return list(extracted)


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
            df_str = df.astype(str).apply(lambda x: x.str.lower())
            combined_mask = pd.Series(False, index=df.index)
            for k in keywords:
                k_lower = k.lower()
                mask = df_str.apply(
                    lambda col: col.str.contains(k_lower, regex=False)
                ).any(axis=1)
                combined_mask = combined_mask | mask

            result = df[combined_mask]

    # 2. TRA CỨU BẰNG HÌNH ẢNH (BÓC TÁCH MÃ TRẠM CHUẨN)
    elif uploaded_file:
        with st.spinner("Đang phân tích hình ảnh và trích xuất mã trạm..."):
            try:
                image = Image.open(uploaded_file)
                extracted_text = pytesseract.image_to_string(
                    image, lang="vie+eng"
                )

                # Trích xuất mã trạm bằng thuật toán riêng
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

                # Tra cứu mã trạm bóc tách được vào danh sách Excel
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
                st.error(f"Lỗi hệ thống khi đọc ảnh: {ocr_err}")

    # HIỂN THỊ KẾT QUẢ
    if query or uploaded_file:
        st.markdown("---")
        st.subheader("Kết quả tra cứu:")
        if not result.empty:
            st.write(f"Tìm thấy **{len(result)}** trạm phù hợp trong Excel:")
            st.dataframe(result, use_container_width=True, hide_index=True)
        else:
            st.warning("Không tìm thấy dữ liệu khớp trong file Excel.")

except Exception as e:
    st.error(f"Lỗi hệ thống hoặc tải dữ liệu: {e}")
