import io
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st
from docx import Document

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("Tra cứu Thông tin Trạm MFS")


# Xóa cache hoàn toàn để luôn tải dữ liệu mới nhất
@st.cache_data(ttl=3600)
def load_data():
    try:
        df = pd.read_excel("danh_sach_tram.xlsx")
    except Exception:
        df = pd.read_excel("data.xlsx")

    # Chuẩn hóa tên cột
    df.columns = df.columns.astype(str).str.strip()
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

    # 1. XỬ LÝ NHẬP CHỮ
    if query and query.strip():
        # Tách các từ khóa nhập vào
        keywords = [
            k.strip()
            for k in re.split(r"[,;\s\n]+", query)
            if len(k.strip()) >= 2
        ]

        if keywords:
            # Chuyển toàn bộ dữ liệu bảng thành chuỗi chữ thường để tìm kiếm chính xác
            df_str = df.astype(str).apply(lambda x: x.str.lower())

            # Tạo bộ lọc: tìm tất cả các dòng chứa ít nhất 1 từ khóa
            combined_mask = pd.Series(False, index=df.index)
            for k in keywords:
                k_lower = k.lower()
                mask = df_str.apply(
                    lambda col: col.str.contains(k_lower, regex=False)
                ).any(axis=1)
                combined_mask = combined_mask | mask

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

                words = [
                    w.strip()
                    for w in re.split(r"[,;\s\n]+", extracted_text)
                    if len(w.strip()) >= 3
                ]
                if words:
                    df_str = df.astype(str).apply(lambda x: x.str.lower())
                    combined_mask = pd.Series(False, index=df.index)
                    for w in words:
                        w_lower = w.lower()
                        mask = df_str.apply(
                            lambda col: col.str.contains(w_lower, regex=False)
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
