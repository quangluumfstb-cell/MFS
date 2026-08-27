import streamlit as st
import pandas as pd
import easyocr
from PIL import Image
import numpy as np
import re

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("🔍 Tra cứu Mã Trạm")

EXCEL_FILE = "danh_sach_tram.xlsx"

# Hàm bỏ dấu tiếng Việt để tìm kiếm chuẩn xác
def remove_accents(text):
    if not isinstance(text, str):
        text = str(text) if pd.notna(text) else ""
    text = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', text)
    text = re.sub(r'[ÈÉẸẺẼÊỀẾỆỂỄ]', 'E', text)
    text = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', text)
    text = re.sub(r'[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'O', text)
    text = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', text)
    text = re.sub(r'[ÌÍỊỈĨ]', 'I', text)
    text = re.sub(r'[ìíịỉĩ]', 'i', text)
    text = re.sub(r'[ÙÚỤỦŨƯỪỨỰỬỮ]', 'U', text)
    text = re.sub(r'[ùúụủũưừứựửữ]', 'u', text)
    text = re.sub(r'[ỲÝỴỶỸ]', 'Y', text)
    text = re.sub(r'[ỳýỵỷỹ]', 'y', text)
    text = re.sub(r'[Đ]', 'D', text)
    text = re.sub(r'[đ]', 'd', text)
    return text.lower().strip()

@st.cache_data
def load_data():
    try:
        df = pd.read_excel(EXCEL_FILE, dtype=str, engine='openpyxl')
    except Exception:
        df = pd.read_csv(EXCEL_FILE, encoding='utf-8', errors='ignore', dtype=str)
    
    # Chuẩn hóa khoảng trắng
    df = df.map(lambda x: x.strip() if isinstance(x, str) else str(x) if pd.notna(x) else "")
    
    # 💥 BỎ CỘT STT TRONG DỮ LIỆU FILE EXCEL (Nếu có cột tên 'STT')
    if 'STT' in df.columns:
        df = df.drop(columns=['STT'])
        
    return df

try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng {len(df)} trạm.")
except Exception as e:
    st.error(f"Lỗi đọc file: {e}")
    st.stop()

# 1. Tra cứu theo mã / chữ (nhập nhiều mã)
st.subheader("1. Nhập Mã trạm (DCU02, DCU07, TNH06...):")
search_input = st.text_input("Nhập từ khóa:")

if search_input:
    keywords = [remove_accents(k) for k in re.split(r'[,;\s]+', search_input) if k.strip()]
    
    def filter_row_multi(row):
        for val in row.values:
            val_clean = remove_accents(val)
            for kw in keywords:
                if kw in val_clean:
                    return True
        return False

    mask = df.apply(filter_row_multi, axis=1)
    results_df = df[mask]

    if not results_df.empty:
        st.write(f"🎯 Tìm thấy **{len(results_df)}** kết quả:")
        # 💥 hide_index=True giúp ẩn cột số thứ tự mặc định ngoài cùng bên trái
        st.dataframe(results_df, hide_index=True)
    else:
        st.warning(f"Không tìm thấy dữ liệu khớp với các mã: {search_input}")

st.markdown("---")

# 2. Tra cứu bằng hình ảnh (OCR)
st.subheader("2. Tìm kiếm bằng Hình Ảnh:")
uploaded_file = st.file_uploader("Tải lên ảnh nhãn trạm:", type=["jpg", "jpeg", "png"])

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['vi', 'en'])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ảnh tải lên", width=300)
    
    with st.spinner("AI đang quét chữ từ ảnh..."):
        reader = load_ocr()
        ocr_results = reader.readtext(np.array(image), detail=0)
        detected_text = " ".join(ocr_results)
        st.info(f"Nội dung quét được: **{detected_text}**")

    if ocr_results:
        matched_indices = set()
        for word in ocr_results:
            clean_word = remove_accents(word)
            if len(clean_word) >= 3:
                for idx, row in df.iterrows():
                    for val in row.values:
                        if clean_word in remove_accents(val):
                            matched_indices.add(idx)
                            
        filtered_df = df.loc[list(matched_indices)]

        if not filtered_df.empty:
            st.success(f"🎯 Kết quả tra cứu từ ảnh ({len(filtered_df)} trạm):")
            # 💥 hide_index=True giúp ẩn cột số thứ tự mặc định
            st.dataframe(filtered_df, hide_index=True)
        else:
            st.warning("AI quét được chữ nhưng không khớp với dữ liệu nào trong bảng.")