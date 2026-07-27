import time
import urllib.parse
import json
import requests

API_KEY = "pk.e792503785b6b6cebd3c6c52b40b8d45"

# 侧边栏填入的所有测试地址
all_locations = [
    "Kuching Waterfront, Sarawak, Malaysia",
    "Vivacity Megamall, Kuching, Sarawak",
    "Swinburne University Kuching, Sarawak",
    "The Spring Shopping Mall, Kuching",
    "Plaza Merdeka, Kuching, Sarawak",
    "AEON Mall Kuching Central, Sarawak"
]

def test_geocode_single(address):
    url = f"https://us1.locationiq.com/v1/search?key={API_KEY}&q={urllib.parse.quote(address)}&format=json&countrycodes=my"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                lng = float(data[0]["lon"])
                lat = float(data[0]["lat"])
                display_name = data[0].get("display_name", address)
                return [lng, lat], display_name, "OK"
            else:
                return None, None, f"数据格式不符/返回空列表: {data}"
        else:
            return None, None, f"HTTP Error Status {res.status_code}: {res.text}"
    except Exception as e:
        return None, None, f"Exception捕获: {str(e)}"

print("==========================================")
print("🚀 开始模拟 Streamlit 全流程地址解析...")
print("==========================================\n")

coords = []
valid_locations = []
failed_locations = []

for idx, loc in enumerate(all_locations, 1):
    print(f"[{idx}/{len(all_locations)}] 正在解析: {loc}")
    c, name, log = test_geocode_single(loc)
    
    if c:
        print(f"  └─ 🟢 成功: 坐标 = {c}")
        coords.append(c)
        valid_locations.append(loc)
    else:
        print(f"  └─ 🔴 失败原因: {log}")
        failed_locations.append(loc)
        
    time.sleep(0.5)

print("\n==========================================")
print("📊 测试汇总结果:")
print(f"  - 成功解析数: {len(coords)}/{len(all_locations)}")
print(f"  - 失败解析数: {len(failed_locations)}/{len(all_locations)}")
if failed_locations:
    print(f"  - 失败列表: {failed_locations}")
print("==========================================")