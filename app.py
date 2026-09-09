import io
import re
import pandas as pd
import pytesseract
from PIL import Image
import streamlit as st

st.set_page_config(page_title="Tra cứu Mã Trạm MFS", layout="wide")
st.title("Hệ thống Tra cứu Mã Trạm MFS")


# 1. Tải dữ liệu Excel
@st.cache_data
def load_data():
    # Tải đúng tên file danh_sach_tram.xlsx trong repo
    df = pd.read_excel("danh_sach_tram.xlsx")
    # Chuẩn hóa tên cột: tìm cột chứa chữ 'mã' hoặc 'trạm' để làm cột chính
    for col in df.columns:
        if "mã" in str(col).lower() or "trạm" in str(col).lower():
            df.rename(columns={col: "Mã trạm"}, inplace=True)
            break
    return df


try:
    df = load_data()
    st.success(f"Đã tải thành công dữ liệu! Tổng cộng: {len(df)} trạm.")
except Exception as e:
    st.error(f"Lỗi đọc file danh_sach_tram.xlsx: {e}")
    st.stop()

# 2. Ô nhập từ khóa (Tách mã tự động)
keyword = st.text_input(
    "1. Nhập Mã trạm (DCU02, DCU07, TNH06...):",
    placeholder="Nhập hpu06 tbh02 tbh09...",
)

# 3. Tải ảnh OCR
uploaded_file = st.file_uploader(
    "2. Tìm kiếm bằng Hình Ảnh:", type=["png", "jpg", "jpeg"]
)
ocr_text = ""

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ảnh đã tải lên", width=300)

    # Chuyển ảnh sang dạng trắng đen để Tesseract OCR nhận diện nét chữ tốt hơn
    gray_image = image.convert("L")

    # Cấu hình Tesseract ưu tiên nhận diện chữ và số (PSM 6)
    custom_config = r"--oem 3 --psm 6"
    try:
        ocr_text = pytesseract.image_to_string(
            gray_image, lang="vie", config=custom_config
        )
    except Exception:
        # Nếu lỗi thư viện eng/vie thì dùng mặc định
        ocr_text = pytesseract.image_to_string(gray_image)

    st.info(f"Chữ trích xuất từ ảnh: `{ocr_text.strip()}`")

# 4. Gom từ khóa và xử lý tra cứu
combined_input = f"{keyword} {ocr_text}".strip()

if combined_input:
    # Tách tất cả các chuỗi nhập vào/OCR ra thành danh sách từ khóa riêng
    raw_codes = re.split(r"[,;\s\n]+", combined_input)
    search_codes = [c.strip().lower() for c in raw_codes if len(c.strip()) >= 2]

    if search_codes:
        # Lấy danh sách cột cần lọc (nếu không có cột 'Mã trạm' thì lọc trên toàn bộ cột)
        col_target = "Mã trạm" if "Mã trạm" in df.columns else df.columns[0]

        df_lower = df[col_target].astype(str).str.lower()

        # Tạo điều kiện lọc: Chứa BẤT KỲ mã nào trong danh sách
        condition = False
        for code in search_codes:
            condition = condition | df_lower.str.contains(
                re.escape(code), na=False
            )

        results = df[condition]

        st.subheader("Kết quả tra cứu:")
        if not results.empty:
            st.write(
                f"Tìm thấy **{len(results)}** kết quả cho các từ khóa: `{', '.join(set(search_codes))}`"
            )
            st.dataframe(results, use_container_width=True)
        else:
            st.warning("Không tìm thấy kết quả phù hợp trong dữ liệu.")
    else:
        st.info("Vui lòng nhập từ khóa từ 2 ký tự trở lên.")
