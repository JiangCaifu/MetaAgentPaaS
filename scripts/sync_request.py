import requests
import time

def sync_request():
    start = time.time()
    # 连续发3个请求（同步会逐个等待）
    urls = ["https://httpbin.org/ip", "https://httpbin.org/user-agent", "https://httpbin.org/delay/1"]
    for url in urls:
        response = requests.get(url)
        print(f"URL: {url}, 状态码: {response.status_code}")
    end = time.time()
    print(f"同步执行耗时: {end - start:.2f}秒")

if __name__ == "__main__":
    sync_request()