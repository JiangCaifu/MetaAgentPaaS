import requests
import requests
from bs4 import BeautifulSoup
import html
import json
import os

# 配置项：更换为【携程旅游热门景点页面】（稳定无反爬，结构清晰）
TARGET_URL = "https://www.mafengwo.cn/jd/10065/gonglve.html"  # 新数据源：携程国内热门景点
SAVE_PATH = "../db/data/scenic_spots.json"  # 保持你现有路径不变
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://you.ctrip.com/"  # 补充referer，降低反爬概率
}

def create_dir_if_not_exists(file_path: str):
    """创建文件所在目录（若不存在）"""
    dir_path = os.path.dirname(file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"目录 {dir_path} 创建成功")

def crawl_scenic_data() -> list:
    """爬取文旅景点数据（名称+开放时间）"""
    scenic_list = []
    try:
        # 1. 发送HTTP请求
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=15)
        response.raise_for_status()
        response.encoding = "utf-8"  # 强制指定utf-8编码，避免中文乱码

        # 2. 解码HTML实体（核心：处理\u003c/\u003e等转义字符）
        html_content = html.unescape(response.text)
        soup = BeautifulSoup(html_content, "html.parser")
        #print(soup)
        # 定位景点列表（携程页面核心景点列表标签，结构稳定）
        scenic_items = soup.find_all("div", class_="item clearfix")
        print(scenic_items)

        if not scenic_items:
            print("未抓取到景点数据，使用模拟文旅数据兜底")
            return generate_mock_scenic_data()

        # 3. 提取景点名称和开放时间（适配携程页面结构）
        for item in scenic_items[:15]:  # 取前15个景点，数据更丰富
            # 提取景点名称
            name_tag = item.find("a", class_="sight_name")
            name = name_tag.get_text(strip=True) if name_tag else None

            # 提取开放时间（携程页面中开放时间标签固定，容错处理）
            open_time = "未公开"
            info_div = item.find("div", class_="sight_info")
            if info_div:
                info_spans = info_div.find_all("span")
                for span in info_spans:
                    text = span.get_text(strip=True)
                    if "开放时间" in text or "开园时间" in text:
                        open_time = text.replace("开放时间：", "").replace("开园时间：", "").strip()
                        break

            # 4. 过滤有效数据，添加到列表
            if name:
                scenic_list.append({
                    "name": name,
                    "open_time": open_time,
                    "source": "携程旅游爬取"
                })

        print(f"爬取成功，共获取 {len(scenic_list)} 个景点数据")
        return scenic_list

    except Exception as e:
        print(f"爬取失败：{str(e)}，使用模拟文旅数据兜底")
        return generate_mock_scenic_data()

def generate_mock_scenic_data() -> list:
    """生成模拟文旅数据（兜底方案，确保JSON文件有效）"""
    return [
        {
            "name": "故宫博物院",
            "open_time": "8:30-17:00（周一闭馆，法定节假日除外）",
            "location": "北京东城区"
        },
        {
            "name": "秦始皇兵马俑博物馆",
            "open_time": "8:30-18:00（夏季）；8:30-17:30（冬季）",
            "location": "陕西西安临潼区"
        },
        {
            "name": "颐和园",
            "open_time": "6:30-18:00（夏季）；7:00-17:00（冬季）",
            "location": "北京海淀区"
        },
        {
            "name": "黄山风景区",
            "open_time": "6:00-18:00（夏季）；7:00-17:00（冬季）",
            "location": "安徽黄山市"
        },
        {
            "name": "桂林漓江风景名胜区",
            "open_time": "8:00-17:30（全年开放，游船班次以当日公告为准）",
            "location": "广西桂林市"
        }
    ]

def save_scenic_data_to_json(data: list, file_path: str):
    """将景点数据保存为JSON文件"""
    create_dir_if_not_exists(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"数据已成功保存到 {file_path}")

if __name__ == "__main__":
    # 执行爬取→保存流程
    scenic_data = crawl_scenic_data()
    save_scenic_data_to_json(scenic_data, SAVE_PATH)