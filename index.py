# Công cụ gửi tin nhắn hàng loạt qua Zalo, Messenger, TikTok
# Yêu cầu: Python 3.8+, ADB, thiết bị Android đã bật USB Debugging
# Cài đặt: pip install pure-python-adb colorama

import os
import sys
import time
import threading
from colorama import Fore, Style, init
from ppadb.client import Client as AdbClient

init(autoreset=True)

# Cấu hình ADB
ADB_HOST = "127.0.0.1"
ADB_PORT = 5037
DEVICE_SERIAL = None  # None = tự động chọn thiết bị đầu tiên

# Tọa độ nút gửi và ô nhập tin nhắn theo từng ứng dụng (tùy chỉnh theo độ phân giải)
APP_CONFIG = {
    "zalo": {
        "package": "com.zing.zalo",
        "input_box": (540, 2100),
        "send_btn": (1000, 2100),
        "open_chat_delay": 2.0,
        "send_delay": 1.5
    },
    "messenger": {
        "package": "com.facebook.orca",
        "input_box": (540, 2100),
        "send_btn": (1000, 2100),
        "open_chat_delay": 2.0,
        "send_delay": 1.5
    },
    "tiktok": {
        "package": "com.zhiliaoapp.musically",
        "input_box": (540, 2100),
        "send_btn": (1000, 2100),
        "open_chat_delay": 2.5,
        "send_delay": 2.0
    }
}

# Trạng thái chạy nền
running_flags = {}

def ket_noi_thiet_bi():
    # Kết nối ADB và trả về đối tượng device
    client = AdbClient(host=ADB_HOST, port=ADB_PORT)
    devices = client.devices()
    if not devices:
        print(Fore.RED + "[LỖI] Không tìm thấy thiết bị Android nào qua ADB.")
        sys.exit(1)
    if DEVICE_SERIAL:
        for d in devices:
            if d.serial == DEVICE_SERIAL:
                return d
        print(Fore.RED + f"[LỖI] Không tìm thấy thiết bị serial {DEVICE_SERIAL}")
        sys.exit(1)
    return devices[0]

def mo_ung_dung(device, package):
    # Mở ứng dụng bằng monkey
    device.shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1")
    time.sleep(1.5)

def dong_ung_dung(device, package):
    # Đóng ứng dụng
    device.shell(f"am force-stop {package}")

def nhap_van_ban(device, text):
    # Nhập văn bản có escape ký tự đặc biệt
    escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
    device.shell(f'input text "{escaped}"')

def gui_tin_nhan(device, app_key, danh_sach_nguoi_nhan, noi_dung, so_lan):
    # Vòng lặp gửi tin nhắn cho từng người, lặp số_lan lần
    cfg = APP_CONFIG[app_key]
    running_flags[app_key] = True
    dem = 0
    for lan in range(so_lan):
        if not running_flags.get(app_key, False):
            break
        for nguoi in danh_sach_nguoi_nhan:
            if not running_flags.get(app_key, False):
                break
            try:
                # Mở chat với người nhận (dùng deep link nếu có, hoặc tìm kiếm)
                # Với Zalo: mở tab tin nhắn
                if app_key == "zalo":
                    device.shell(f"am start -a android.intent.action.VIEW -d 'zalo://conversation?phone={nguoi}'")
                elif app_key == "messenger":
                    device.shell(f"am start -a android.intent.action.VIEW -d 'fb-messenger://user-thread/{nguoi}'")
                elif app_key == "tiktok":
                    device.shell(f"am start -a android.intent.action.VIEW -d 'snssdk1233://im/chat?uid={nguoi}'")
                time.sleep(cfg["open_chat_delay"])
                # Nhấn vào ô nhập
                device.shell(f"input tap {cfg['input_box'][0]} {cfg['input_box'][1]}")
                time.sleep(0.5)
                # Nhập nội dung
                nhap_van_ban(device, noi_dung)
                time.sleep(0.5)
                # Nhấn gửi
                device.shell(f"input tap {cfg['send_btn'][0]} {cfg['send_btn'][1]}")
                dem += 1
                print(Fore.GREEN + f"[{app_key}] Đã gửi tới {nguoi} lần {lan+1}/{so_lan} | Tổng: {dem}")
                time.sleep(cfg["send_delay"])
            except Exception as e:
                print(Fore.RED + f"[LỖI] {nguoi}: {e}")
    running_flags[app_key] = False

def chay_nen(device, app_key, ds, nd, sl):
    # Chạy luồng nền cho ứng dụng
    t = threading.Thread(target=gui_tin_nhan, args=(device, app_key, ds, nd, sl), daemon=True)
    t.start()
    return t

def dung_ung_dung(app_key):
    # Dừng vòng lặp gửi của ứng dụng
    running_flags[app_key] = False

def menu():
    # Menu chính
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print(Fore.CYAN + "="*50)
        print(Fore.CYAN + "     TOOL SPAM TIN NHẮN ZALO / MESS / TIKTOK")
        print(Fore.CYAN + "="*50)
        print("1. Spam Zalo")
        print("2. Spam Messenger")
        print("3. Spam TikTok")
        print("4. Dừng tất cả")
        print("5. Thoát")
        print(Fore.CYAN + "="*50)
        chon = input("Chọn: ").strip()
        if chon == "5":
            print(Fore.YELLOW + "Thoát tool.")
            sys.exit(0)
        if chon == "4":
            for k in running_flags:
                running_flags[k] = False
            print(Fore.YELLOW + "Đã gửi lệnh dừng tất cả tiến trình.")
            time.sleep(1.5)
            continue
        if chon in ("1", "2", "3"):
            app_key = {"1": "zalo", "2": "messenger", "3": "tiktok"}[chon]
            ds_raw = input("Nhập danh sách ID/SĐT người nhận (cách nhau dấu phẩy): ").strip()
            ds = [x.strip() for x in ds_raw.split(",") if x.strip()]
            if not ds:
                print(Fore.RED + "Danh sách trống.")
                time.sleep(1.5)
                continue
            nd = input("Nhập nội dung tin nhắn: ")
            try:
                sl = int(input("Số lần lặp: ").strip())
            except ValueError:
                sl = 1
            device = ket_noi_thiet_bi()
            mo_ung_dung(device, APP_CONFIG[app_key]["package"])
            chay_nen(device, app_key, ds, nd, sl)
            print(Fore.GREEN + f"Đã khởi chạy tiến trình nền cho {app_key}.")
            time.sleep(2)
        else:
            print(Fore.RED + "Lựa chọn không hợp lệ.")
            time.sleep(1)

if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nĐã dừng bằng Ctrl+C.")
        sys.exit(0)
