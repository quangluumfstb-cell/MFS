import streamlit as st
import pandas as pd
import easyocr
from PIL import Image
import numpy as np
import re

st.set_page_config(page_title="Tra cứu Thông tin Trạm", layout="wide")
st.title("🔍 Tra cứu Mã Trạm (Hỗ trợ tin nhắn cảnh báo & Ảnh)")

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

# Hàm lọc tự động trích xuất mã trạm từ tin nhắn
def extract_station_codes(text):
    # Tìm các chuỗi chữ + số có độ dài từ 4 ký tự trở lên (ví dụ: HYNTLY02, DCU07, TNH06...)
    raw_tokens = re.findall(r'[A-Za-z0-9_]+', text)
    codes = []
    
    # Loại bỏ các từ rác phổ biến trong tin nhắn cảnh báo/ngày tháng
    ignore_words = {'ac', 'failure', 'ran', '4g', '3g', '2g', 'indoor', 'outdoor'}
    
    for token in raw_tokens:
        # Bỏ qua ngày tháng / thời gian (chỉ toàn số)
        if token.isdigit():
            continue
        
        # Bỏ qua đuôi công nghệ trong ngoặc như _4G
        clean_token = re.sub(r'_(4g|3g|2g|ran_4g)$', '', token, flags=re.IGNORECASE)
        
        if clean_token.lower() not in ignore_words and len(clean_token) >= 4:
            codes.append(clean_token)
            
    return list(set(codes)) # Bỏ trùng lặp

@st.cache_data
def load_data():
    try:
        df = pd.read_excel(EXCEL_FILE, dtype=str, engine='openpyxl')
    except Exception:
        df = pd.read_csv(EXCEL_FILE, encoding='utf-8', errors='ignore', dtype=str)
    
    df = df.map(lambda x: x.strip() if isinstance(x, str) else str(x) if pd.notna(x) else "")
    
    if 'STT' in df.columns:
        df = df.drop(columns=['STT'])
        
    return df

try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng {len(df)} trạm.")
except Exception as e:
    st.error(f"Lỗi đọc file: {e}")
    st.stop()

# 1. Tra cứu theo Mã / Tin nhắn cảnh báo
st.subheader("1. Dán tin nhắn cảnh báo hoặc nhập danh sách mã trạm:")
search_input = st.text_area("Dán toàn bộ tin nhắn vào đây (ví dụ: 27/08/2026 16:00:58: AC FAILURE...):", height=150)

if search_input:
    # Trích xuất mã trạm từ tin nhắn
    extracted_codes = extract_station_codes(search_input)
    keywords = [remove_accents(k) for k in extracted_codes]
    
    if keywords:
        st.info(f"📌 Mã trạm hệ thống bóc tách được từ tin nhắn: **{', '.join(extracted_codes)}**")
        
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
            st.write(f"🎯 Tìm thấy **{len(results_df)}** trạm khớp dữ liệu:")
            st.dataframe(results_df, hide_index=True)
        else:
            st.warning("Đã lọc được mã trạm nhưng không khớp với dữ liệu nào trong file Excel.")
    else:
        st.warning("Không tìm thấy mã trạm hợp lệ trong nội dung vừa nhập.")

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
            st.dataframe(filtered_df, hide_index=True)
        else:
            st.warning("AI quét được chữ nhưng không khớp với dữ liệu nào trong bảng.")
