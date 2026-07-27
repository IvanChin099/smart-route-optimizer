import requests
import urllib.parse
import json

# 1. 你的 LocationIQ Key
API_KEY = "pk.e792503785b6b6cebd3c6c52b40b8d45"

# 2. 测试地址
test_address = "Kuching Waterfront, Sarawak, Malaysia"

# 3. 构造请求 URL (针对欧洲/美洲节点多重测试)
urls = [
    f"https://us1.locationiq.com/v1/search?key={API_KEY}&q={urllib.parse.quote(test_address)}&format=json",
    f"https://eu1.locationiq.com/v1/search?key={API_KEY}&q={urllib.parse.quote(test_address)}&format=json"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

print("==========================================")
print("🔍 正在测试 LocationIQ API 节点...")
print("==========================================\n")

for i, url in enumerate(urls, 1):
    print(f"--- [测试节点 {i}] ---")
    print(f"🔗 请求 URL: {url}\n")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"📡 Status Code (状态码): {response.status_code}")
        print("📄 Raw Response (原始返回内容):")
        
        try:
            # 格式化打印 JSON
            json_data = response.json()
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
        except Exception:
            print(response.text)
            
    except Exception as e:
        print(f"❌ 网络请求异常: {e}")
    print("\n" + "="*42 + "\n")