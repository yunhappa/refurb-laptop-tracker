import os
import re
import csv
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

client_id = CLIENT_ID
client_secret = CLIENT_SECRET

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("네이버 API 키가 없습니다. .env 파일을 확인하세요.")

url = "https://openapi.naver.com/v1/search/shop.json"

headers = {
    "X-Naver-Client-Id": CLIENT_ID,
    "X-Naver-Client-Secret": CLIENT_SECRET
}

keywords = [
    "리퍼 노트북",
    "중고 노트북",
    "리퍼 맥북",
    "중고 맥북",
    "리퍼 LG그램",
    "중고 LG그램",
    "리퍼 갤럭시북",
    "중고 갤럭시북",
    "리퍼 ThinkPad",
    "중고 ThinkPad"
]

csv_filename = "refurb_laptop_prices.csv"


def clean_title(title):
    return title.replace("<b>", "").replace("</b>", "")


def extract_ram(title):
    text = title.upper().replace(" ", "")

    if re.search(r"32GB|32G|32기가", text):
        return "32GB"
    if re.search(r"24GB|24G|24기가", text):
        return "24GB"
    if re.search(r"16GB|16G|16기가", text):
        return "16GB"
    if re.search(r"8GB|8G|8기가", text):
        return "8GB"
    if re.search(r"4GB|4G|4기가", text):
        return "4GB"

    return ""


def extract_ssd(title):
    text = title.upper().replace(" ", "")

    if re.search(r"2TB|2테라", text):
        return "2TB"
    if re.search(r"1TB|1테라|1024GB|1024G", text):
        return "1TB"
    if re.search(r"512GB|512G", text):
        return "512GB"
    if re.search(r"256GB|256G", text):
        return "256GB"
    if re.search(r"128GB|128G", text):
        return "128GB"

    return ""


def extract_cpu(title):
    text = title.upper().replace(" ", "")

    # 라이젠 계열을 먼저 확인
    if "RYZEN7" in text or "라이젠7" in text:
        return "Ryzen 7"
    if "RYZEN5" in text or "라이젠5" in text:
        return "Ryzen 5"
    if "RYZEN3" in text or "라이젠3" in text:
        return "Ryzen 3"

    # 인텔 계열
    if "I9" in text:
        return "i9"
    if "I7" in text:
        return "i7"
    if "I5" in text:
        return "i5"
    if "I3" in text:
        return "i3"

    # 애플 실리콘은 '맥북', 'MACBOOK', 'APPLE' 등이 있을 때만 판단
    if "맥북" in title or "MACBOOK" in text or "APPLE" in text:
        if "M4" in text:
            return "Apple M4"
        if "M3" in text:
            return "Apple M3"
        if "M2" in text:
            return "Apple M2"
        if "M1" in text:
            return "Apple M1"

    return ""


def collect_prices():
    file_exists = os.path.exists(csv_filename)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []

    for keyword in keywords:
        params = {
            "query": keyword,
            "display": 20,
            "start": 1,
            "sort": "sim"
        }

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            print(f"API 오류: {keyword}")
            continue

        data = response.json()

        for item in data["items"]:
            title = clean_title(item["title"])
            price = int(item["lprice"])

            rows.append([
                now,
                keyword,
                item.get("productId", ""),
                title,
                price,
                item["mallName"],
                item.get("brand", ""),
                item.get("maker", ""),
                extract_ram(title),
                extract_ssd(title),
                extract_cpu(title),
                item["link"]
            ])

    with open(csv_filename, "a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "collected_at",
                "keyword",
                "product_id",
                "title",
                "price",
                "mall",
                "brand",
                "maker",
                "ram",
                "ssd",
                "cpu",
                "link"
            ])

        writer.writerows(rows)

    print("CSV 누적 저장 완료!")
    print(f"이번 수집 건수: {len(rows)}")
    print(f"저장 파일: {csv_filename}")


collect_prices()