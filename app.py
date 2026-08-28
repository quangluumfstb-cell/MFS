if query:
        # 1. Bóc tách tất cả từ chứa chữ, số, dấu gạch dưới (loại bỏ hoàn toàn ngoặc ngoặc, dấu hai chấm, ngày tháng...)
        raw_tokens = re.findall(r"[A-Za-z0-9_]+", query)

        # Các từ khóa hệ thống/ngày giờ cần bỏ qua
        ignore_words = {
            "CELL",
            "DOWN",
            "FAILURE",
            "ALARM",
            "RAN",
            "CLEAR",
            "CRITICAL",
            "AC",
            "3G",
            "4G",
            "5G",
        }

        search_codes = set()
        for token in raw_tokens:
            token_clean = token.strip().upper()
            # Bỏ qua từ ngắn, thuần số (ngày/giờ 28, 08, 2026, 18...) và từ khóa hệ thống
            if (
                len(token_clean) >= 3
                and not token_clean.isdigit()
                and token_clean not in ignore_words
            ):
                # Standardize O -> 0
                code_norm = token_clean.replace("O", "0")
                search_codes.add(code_norm)

                # Lấy phần mã gốc nếu có chứa đuôi _4G / _3G (VD: HYNTHD10_4G -> HYNTHD10)
                base_code = code_norm.split("_")[0]
                if len(base_code) >= 3 and base_code not in ignore_words:
                    search_codes.add(base_code)

        if search_codes and col_ma_moi:
            # Chuẩn hóa cột Mã mới trong Excel
            excel_series = (
                df[col_ma_moi]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
                .str.replace("O", "0")
            )

            # Lọc kết quả khớp 2 chiều linh hoạt
            masks = []
            for code in search_codes:
                if code:
                    m = excel_series.apply(
                        lambda cell: cell != ""
                        and (code in cell or cell in code)
                    )
                    masks.append(m)

            if masks:
                final_mask = reduce(lambda x, y: x | y, masks)
                result = df[final_mask]
