import io
import re
import pandas as pd
from PIL import Image
import pytesseract
import streamlit as st

st.set_page_config(page_title="Tra cứu Mã Trạm", layout="wide")


# 1. Load dữ liệu từ Excel
@st.cache_data
def load_data():
    return pd.read_excel("danh_sach_tram.xlsx")


try:
    df = load_data()
except Exception as e:
    st.error(f"Lỗi khi tải file danh_sach_tram.xlsx: {e}")
    df = pd.DataFrame()

# 2. Chọn phương thức tra cứu
st.title("Chương trình Tra cứu Mã Trạm")
tab1, tab2 = st.tabs(
    ["📝 Tra cứu qua Văn bản / Log", "🖼️ Tra cứu qua Hình ảnh"]
)

input_text = ""

# --- TAB 1: NHẬP VĂN BẢN ---
with tab1:
    input_text = st.text_area(
        label="Dán nội dung tin nhắn/log vào đây:",
        placeholder="Ví dụ: 27/08/2026 17:00:51 CELL_DOWN HYNTLY02(3G)(1/3)...",
        height=150,
    )

# --- TAB 2: TẢI ẢNH LÊN (OCR) ---
with tab2:
    uploaded_file = st.file_uploader(
        "Tải ảnh chứa thông tin mã trạm (ảnh màn hình, ảnh tin nhắn...):",
        type=["png", "jpg", "jpeg"],
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Ảnh đã tải lên", width=400)

        with st.spinner("Đang bóc tách chữ từ hình ảnh..."):
            try:
                # Sử dụng Tesseract OCR để đọc văn bản trong ảnh
                extracted_ocr_text = pytesseract.image_to_string(image)
                input_text = extracted_ocr_text
                st.success("Đã trích xuất xong văn bản từ ảnh!")
            except Exception as e:
                st.error(
                    f"Lỗi OCR (Cần cài đặt pytesseract trên máy/server): {e}"
                )

# 3. XỬ LÝ BÓC TÁCH MÃ TRẠM VÀ HIỂN THỊ KẾT QUẢ
if input_text:
    # Bóc tách và làm sạch mã trạm từ văn bản đầu vào
    raw_words = re.findall(r"[A-Za-z0-9_()/-]+", input_text)
    cleaned_codes = set()

    for word in raw_words:
        # Loại bỏ các thông tin đính kèm trong ngoặc như (3G), (1/3), (4G)...
        clean_code = re.sub(r"\(.*?\)", "", word).strip()
        # Lọc các chuỗi mã trạm có độ dài hợp lệ (từ 4 đến 20 ký tự)
        if re.match(r"^[A-Z0-9_]{4,20}$", clean_code):
            cleaned_codes.add(clean_code)

    extracted_codes = cleaned_codes

    if extracted_codes and not df.empty:
        col_ma_cu = "Mã cũ" if "Mã cũ" in df.columns else df.columns[0]
        col_ma_moi = "Mã mới" if "Mã mới" in df.columns else df.columns[1]

        # Lọc danh sách khớp mã (hỗ trợ tìm kiếm chứa từ khóa/contains)
        pattern = "|".join(re.escape(code) for code in extracted_codes)
        mask = df[col_ma_cu].astype(str).str.contains(
            pattern, case=False, na=False
        ) | df[col_ma_moi].astype(str).str.contains(
            pattern, case=False, na=False
        )

        matched_df = df[mask]

        found_list = ", ".join(extracted_codes)
        st.info(f"📌 **Mã trạm bóc tách được:** {found_list}")

        if not matched_df.empty:
            st.success(f"🎯 **Tìm thấy {len(matched_df)} trạm khớp dữ liệu:**")

            display_cols = [
                c
                for c in [col_ma_cu, col_ma_moi, "Địa chỉ", "Hình ảnh"]
                if c in df.columns
            ]
            st.dataframe(
                matched_df[display_cols],
                use_container_width=True,
                hide_index=True,
            )

            # Hiển thị ảnh trạm nếu có đường dẫn/URL trong cột "Hình ảnh"
            if "Hình ảnh" in matched_df.columns:
                for idx, row in matched_df.iterrows():
                    img_path = row.get("Hình ảnh")
                    if pd.notna(img_path):
                        st.write(
                            f"**Hình ảnh trạm {row.get(col_ma_moi, '')}:**"
                        )
                        st.image(img_path, width=350)
        else:
            st.warning("Không tìm thấy mã trạm tương ứng trong file Excel.")
    else:
        st.warning("Không trích xuất được mã trạm nào từ dữ liệu đầu vào.")
else:
    # Mặc định hiển thị toàn bộ bảng dữ liệu khi chưa nhập thông tin
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
