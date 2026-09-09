import io
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st
from docx import Document

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")

st.title("Tra cứu Thông tin Trạm MFS")


@st.cache_data
def load_data():
    # Tự động đọc file danh_sach_tram.xlsx hoặc data.xlsx
    try:
        df = pd.read_excel("danh_sach_tram.xlsx")
    except Exception:
        df = pd.read_excel("data.xlsx")

    df.columns = df.columns.str.strip()
    return df


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

    # 1. XỬ LÝ NHẬP CHỮ / DÁN TIN NHẮN
    if query and query.strip():
        # Tách các từ khóa nhập vào theo khoảng trắng, dấu phẩy, dấu chấm phẩy, xuống dòng
        keywords = [
            k.strip()
            for k in re.split(r"[,;\s\n]+", query)
            if len(k.strip()) >= 2
        ]

        if keywords:
            masks = [
                df.astype(str)
                .apply(lambda x: x.str.contains(k, case=False, na=False))
                .any(axis=1)
                for k in keywords
            ]
            combined_mask = pd.concat(masks, axis=1).any(axis=1)
            result = df[combined_mask]

    # 2. XỬ LÝ TẢI Ảnh (OCR)
    elif uploaded_file:
        with st.spinner("Đang trích xuất dữ liệu từ ảnh..."):
            try:
                image = Image.open(uploaded_file)
                extracted_text = pytesseract.image_to_string(
                    image, lang="vie+eng"
                )

                st.info("Chữ trích xuất từ ảnh:")
                st.code(
                    extracted_text
                    if extracted_text.strip()
                    else "Không đọc được chữ nào từ ảnh."
                )

                # Tạo file Word chứa kết quả đọc từ ảnh
                doc = Document()
                doc.add_heading("Kết quả trích xuất từ ảnh", level=1)
                doc.add_paragraph(extracted_text)

                bio = io.BytesIO()
                doc.save(bio)

                st.download_button(
                    label="📥 Tải file Word kết quả OCR",
                    data=bio.getvalue(),
                    file_name="ket_qua_doc_anh.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )

                # Tra cứu các từ trích xuất từ ảnh
                words = [
                    w.strip()
                    for w in re.split(r"[,;\s\n]+", extracted_text)
                    if len(w.strip()) >= 3
                ]
                if words:
                    masks = [
                        df.astype(str)
                        .apply(
                            lambda x: x.str.contains(w, case=False, na=False)
                        )
                        .any(axis=1)
                        for w in words
                    ]
                    combined_mask = pd.concat(masks, axis=1).any(axis=1)
                    result = df[combined_mask]
            except Exception as ocr_err:
                st.error(
                    f"Lỗi đọc ảnh OCR (Cần kiểm tra file packages.txt): {ocr_err}"
                )

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
