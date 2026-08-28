import os
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tra Cứu Trạm", layout="wide")
st.title("Chương trình Tra cứu Mã Trạm")


# Load dữ liệu từ file Excel
@st.cache_data
def load_data():
    return pd.read_excel("danh_sach_tram.xlsx")


df = load_data()

# Ô tìm kiếm
search_term = st.text_input("Nhập Mã trạm hoặc Tên trạm cần tìm:")

if search_term:
    # Lọc dữ liệu theo từ khóa
    filtered_df = df[
        df["Mã trạm"]
        .astype(str)
        .str.contains(search_term, case=False, na=False)
        | df["Tên trạm"]
        .astype(str)
        .str.contains(search_term, case=False, na=False)
    ]

    if not filtered_df.empty:
        st.write(f"Tìm thấy {len(filtered_df)} kết quả:")

        for idx, row in filtered_df.iterrows():
            st.subheader(f"Trạm: {row.get('Tên trạm', '')} ({row.get('Mã trạm', '')})")

            # Hiển thị thông tin chi tiết
            col1, col2 = st.columns([1, 1])

            with col1:
                st.write(f"**Địa chỉ:** {row.get('Địa chỉ', 'N/A')}")
                st.write(f"**Tọa độ:** {row.get('Tọa độ', 'N/A')}")
                # Thêm các cột thông tin khác tùy theo file Excel của bạn

            with col2:
                # Xử lý hiển thị hình ảnh từ URL hoặc đường dẫn đính kèm
                img_path = row.get("Hình ảnh", None)
                if pd.notna(img_path):
                    if str(img_path).startswith(("http://", "https://")):
                        st.image(
                            img_path,
                            caption=f"Hình ảnh trạm {row.get('Mã trạm', '')}",
                            use_column_width=True,
                        )
                    elif os.path.exists(str(img_path)):
                        st.image(
                            img_path,
                            caption=f"Hình ảnh trạm {row.get('Mã trạm', '')}",
                            use_column_width=True,
                        )
                    else:
                        st.warning("Không tìm thấy tệp hình ảnh theo đường dẫn.")
                else:
                    st.info("Chưa có hình ảnh cho trạm này.")
            st.divider()
    else:
        st.error("Không tìm thấy kết quả phù hợp!")
else:
        st.dataframe(df, use_container_width=True)
