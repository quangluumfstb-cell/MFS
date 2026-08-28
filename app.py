import re


def fix_station_code(code: str) -> str:
    code = code.strip().upper()
    if not code:
        return code

    # 1. Tách đuôi mở rộng dạng _4G, _3G, _5G... nếu có
    suffix = ""
    match_suffix = re.search(r"(_\d+G)$", code, re.IGNORECASE)
    if match_suffix:
        suffix = match_suffix.group(1).upper()
        base_code = code[: -len(suffix)]
    else:
        base_code = code

    # 2. Quy tắc sửa lỗi OCR cho phần mã chính (base_code):
    # Trạm thường có dạng: [Tên tỉnh][Tên huyện/khu vực][Số] (Ví dụ: HYN + THI + 04)
    # Phần số thường nằm ở 2-3 ký tự cuối cùng của base_code.

    # Sửa chữ 'S' ở cuối thành '5' (ví dụ HYNLLIOS -> HYNLLI05)
    if base_code.endswith("S"):
        base_code = base_code[:-1] + "5"

    # Sửa chữ 'O' / 'o' ở các vị trí số (2 đến 3 ký tự cuối của base_code)
    # Tìm và thay thế tất cả chữ 'O' xuất hiện trong 3 ký tự cuối thành số '0'
    if len(base_code) >= 3:
        prefix = base_code[:-3]
        tail = base_code[-3:]
        tail_fixed = tail.replace("O", "0").replace("S", "5")
        base_code = prefix + tail_fixed
    elif len(base_code) >= 2:
        prefix = base_code[:-2]
        tail = base_code[-2:]
        tail_fixed = tail.replace("O", "0").replace("S", "5")
        base_code = prefix + tail_fixed

    return base_code + suffix
