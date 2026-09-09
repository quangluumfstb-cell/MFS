import io
import re
import pandas as pd
import pytesseract
from PIL import Image
import streamlit as st

st.set_page_config(page_title="Tra cứu Thông tin Trạm MFS", layout="wide")
st.title("Tra cứu Thông tin Trạm MFS")


# --- 1. TẢI DỮ LIỆU ---
@st.cache_data
def load_data():
    df = pd.read_excel("data.xlsx")
    df.columns = df.columns.str.strip()
    return df


try:
    df = load_data()
    st.success(f"🟢 Đã tải dữ liệu từ `data.xlsx`. Tổng cộng: {len(df)} trạm.")
except Exception as e:
    st.error(f"❌ Lỗi tải dữ liệu data.xlsx: {e}")
    st.stop()

st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.header("1. Nhập từ khóa / Tin nhắn:")
    query = st.text_area(
        "Dán đoạn tin nhắn hoặc danh sách mã trạm vào đây:",
        placeholder="Ví dụ: Cần xử lý trạm DCU02, TNH06 và HYNNLM04 gấp nhé...",
        height=150,
    )

with col2:
    st.header("2. Quét từ Hình Ảnh (OCR):")
    uploaded_file = st.file_uploader(
        "Tải ảnh màn hình tin nhắn:", type=["png", "jpg", "jpeg"]
    )


# --- 2. HÀM TÁCH MÃ TRẠM CHUẨN TỪ TIN NHẮN / OCR ---
def extract_station_codes(text):
    if not text:
        return []
    # Tìm tất cả các từ có dạng mã trạm (chứa cả chữ và số, hoặc các mã dài từ 3-15 ký tự)
    # Loại bỏ các dấu câu, ký tự đặc biệt
    words = re.findall(r"\b[A-Za-z0-9_]{3,15}\b", text)

    # Danh sách các từ tiếng Việt phổ biến dính vào cần loại bỏ
    stop_words = {
        "tram",
        "tin",
        "nhan",
        "ngay",
        "chuyen",
        "name",
        "tram",
        "code",
        "view",
        "page",
    }

    cleaned_codes = []
    for w in words:
        w_lower = w.lower()
        # Chỉ giữ lại mã có cả chữ lẫn số HOẶC mã viết hoa đặc trưng, không nằm trong stop_words
        if w_lower not in stop_words:
            # Ưu tiên lấy mã có chứa chữ + số (ví dụ: DCU02, HYNNLM04, TBH09)
            cleaned_codes.append(w)

    return list(set(cleaned_codes))  # Lọc trùng lặp


# --- 3. XỬ LÝ ĐỌC OCR ---
extracted_text = ""
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ảnh đã tải lên", width=250)

    if st.button("🔍 Bắt đầu quét chữ từ ảnh"):
        with st.spinner("Đang trích xuất mã từ ảnh..."):
            try:
                gray_image = image.convert("L")
                extracted_text = pytesseract.image_to_string(
                    gray_image, lang="vie+eng"
                )
                if extracted_text.strip():
                    st.code(extracted_text)
                else:
                    st.warning("⚠️ Không đọc được chữ từ ảnh này.")
            except Exception as e:
                st.error(f"❌ Lỗi OCR: {e}")

# --- 4. TRA CỨU DỮ LIỆU ---
input_content = query if query.strip() else extracted_text

if input_content.strip():
    codes = extract_station_codes(input_content)

    if codes:
        st.markdown("---")
        st.subheader("📊 Kết quả tra cứu:")
        st.write(
            f"🎯 Trích xuất được **{len(codes)}** mã trạm khả thi: `{', '.join(codes)}`"
        )

        # Chuyển dataframe sang string để tìm kiếm
        df_str = df.astype(str)

        # Tạo điều kiện tìm kiếm chứa BẤT KỲ mã nào
        pattern = "|".join([re.escape(c) for c in codes])
        mask = df_str.apply(
            lambda row: row.str.contains(pattern, case=False, na=False)
        ).any(axis=1)

        result_df = df[mask]

        if not result_df.empty:
            st.success(f"✅ Tìm thấy **{len(result_df)}** kết quả phù hợp:")
            st.dataframe(result_df, use_container_width=True, hide_index=True)
        else:
            st.warning(
                "❌ Không tìm thấy mã trạm nào khớp trong file data.xlsx."
            )
    else:
        st.info("💡 Không trích xuất được mã trạm hợp lệ nào từ đoạn văn bản.")
