import pandas as pd
import streamlit as st
from PIL import Image
import pytesseract
import re
import io

st.set_page_config(page_title="Tra cứu Thông tin Trạm MFS", layout="wide")
st.title("Tra cứu Thông tin Trạm")

# --- 1. HÀM TẢI DỮ LIỆU ---
@st.cache_data
def load_data():
    # Sử dụng cache để không phải tải lại file mỗi khi app chạy lại
    df = pd.read_excel("data.xlsx")
    df.columns = df.columns.str.strip()  # Xóa khoảng trắng tên cột
    return df

try:
    df = load_data()
    st.success(f"🟢 Đã tải dữ liệu từ `data.xlsx`. Tổng cộng: {len(df)} trạm.")

    # --- 2. GIAO DIỆN CHÍNH ---
    st.markdown("---")
    
    # Tạo 2 cột cho giao diện nhập liệu
    col1, col2 = st.columns(2)

    with col1:
        st.header("1. Nhập từ khóa:")
        # Thêm hướng dẫn nhập nhiều mã
        query = st.text_input(
            "Nhập mã trạm (DCU02, TNH06...) hoặc tên trạm (ví dụ: Ngoc Lan)",
            placeholder="DCU02, TNH06, Ngoc Lan",
            key="search_query"
        )
        st.info("💡 Bạn có thể nhập nhiều mã trạm, phân tách nhau bằng **dấu phẩy (,)** hoặc **khoảng trắng**.")

    with col2:
        st.header("2. Quét từ Hình Ảnh:")
        uploaded_file = st.file_uploader(
            "Tải ảnh màn hình/tin nhắn lên đây:", 
            type=["png", "jpg", "jpeg"]
        )

    # --- 3. XỬ LÝ OCR (ĐỌC CHỮ TỪ ẢNH) ---
    extracted_text = ""
    # CHỈ CHẠY OCR KHI BẤM NÚT VÀ CÓ ẢNH ĐỂ KHÔNG LÀM APP CHẬM
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Ảnh đã tải lên", width=200)
        
        # Thêm nút bấm để bắt đầu đọc OCR
        if st.button("🔍 Bắt đầu quét chữ từ ảnh"):
            with st.spinner("Đang trích xuất dữ liệu từ ảnh..."):
                try:
                    # Chuyển sang ảnh xám để OCR tốt hơn
                    gray_image = image.convert('L')
                    # Đọc OCR kết hợp tiếng Việt và Anh
                    extracted_text = pytesseract.image_to_string(gray_image, lang='vie+eng')
                    
                    if extracted_text.strip():
                        st.subheader("📝 Kết quả trích xuất từ ảnh:")
                        # Hiển thị chữ quét được trong ô code để bạn dễ copy
                        st.code(extracted_text)
                    else:
                        st.warning("⚠️ Không đọc được chữ nào từ ảnh này. Vui lòng thử lại với ảnh rõ nét hơn.")
                        st.stop()
                except Exception as e:
                    st.error(f"❌ Lỗi khi đọc OCR: {e}")
                    st.stop()

    # --- 4. HÀM TÁCH VÀ CHUẨN HÓA MÃ TRẠM ---
    def process_and_filter_codes(text):
        if not text:
            return pd.DataFrame()
            
        # Tách chuỗi nhập vào theo: dấu phẩy (,), khoảng trắng (\s), dấu chấm phẩy (;), xuống dòng (\n)
        # Bỏ qua các chuỗi rỗng và mã trạm quá ngắn (< 3 ký tự)
        raw_codes = re.split(r'[,;\s\n]+', text.strip())
        search_codes = [c.strip() for c in raw_codes if len(c.strip()) >= 3]
        
        if not search_codes:
            return pd.DataFrame()

        st.write(f"🔍 Đang tra cứu cho **{len(search_codes)}** từ khóa: `{', '.join(search_codes)}`")
        
        # Chuyển toàn bộ dataframe sang dạng chữ thường để so sánh
        df_lower = df.astype(str).apply(lambda x: x.str.lower())
        
        # Tạo mask lọc: nếu chứa BẤT KỲ từ khóa nào trong danh sách
        mask = pd.Series(False, index=df.index)
        for code in search_codes:
            # So sánh case-insensitive (không phân biệt hoa thường)
            current_mask = df_lower.apply(
                lambda x: x.str.contains(re.escape(code.lower()), na=False)
            ).any(axis=1)
            mask = mask | current_mask
            
        return df[mask]

    # --- 5. XỬ LÝ TRA CỨU VÀ HIỂN THỊ KẾT QUẢ ---
    result_df = pd.DataFrame()

    # Nếu người dùng nhập vào ô tìm kiếm, ưu tiên xử lý trước
    if query:
        result_df = process_and_filter_codes(query)
        
    # Nếu người dùng quét ảnh, xử lý chữ từ ảnh
    elif extracted_text:
        result_df = process_and_filter_codes(extracted_text)

    # Hiển thị kết quả tra cứu
    if query or extracted_text:
        st.markdown("---")
        st.subheader("📊 Kết quả tra cứu:")
        
        if not result_df.empty:
            st.success(f"✅ Tìm thấy **{len(result_df)}** kết quả phù hợp:")
            st.dataframe(
                result_df, 
                use_container_width=True, 
                hide_index=True # Ẩn cột STT mặc định của dataframe
            )
        else:
            # Chỉ hiển thị warning khi đã nhập từ khóa hợp lệ mà không tìm thấy
            if (query and process_and_filter_codes(query).empty) or \
               (extracted_text and process_and_filter_codes(extracted_text).empty):
                st.warning("❌ Không tìm thấy kết quả phù hợp trong dữ liệu.")
            else:
                # Trường hợp từ khóa quá ngắn, chỉ hiển thị info
                st.info("💡 Vui lòng nhập từ khóa có độ dài từ 3 ký tự trở lên.")

except Exception as e:
    st.error(f"❌ Lỗi hệ thống: {e}")
