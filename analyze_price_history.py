import csv
import re
from collections import defaultdict
from datetime import datetime

input_filename = "refurb_laptop_prices.csv"
output_filename = "price_history_summary.csv"

# 목적:
# product_id 기준이 아니라 "모델/사양 그룹" 기준으로 가격 이력을 묶는다.
# 같은 모델이 여러 판매처에 중복 등록되어도 TOP 8에 반복 노출되지 않게 한다.
#
# 이번 버전의 핵심:
# 평균 대비 할인율 + 최근 최저가 여부 + 관측 수 + 판매처 수를 종합해
# "구매 적기 점수"를 계산한다.

rental_keywords = [
    "대여", "렌탈", "임대", "렌트", "리스", "단기", "월렌탈", "노트북렌탈"
]


def safe_int(value):
    try:
        return int(str(value).replace(",", ""))
    except Exception:
        return 0


def parse_date(value):
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def fix_name(text):
    if not text:
        return ""

    replacements = {
        "겔럭시북": "갤럭시북",
        "겔럭시 북": "갤럭시북",
        "겔럭시": "갤럭시",
        "갤러시북": "갤럭시북",
        "갤러시 북": "갤럭시북",
        "LG그램": "LG 그램",
        "맥 북": "맥북",
        "Think Pad": "ThinkPad",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def normalize_text(text):
    text = fix_name(str(text)).upper()
    remove_words = [
        " ", "-", "_", "/", "[", "]", "(", ")", ".", ",",
        "리퍼", "중고", "노트북", "윈도우11", "윈도우10",
        "WIN11", "WIN10", "WINDOWS11", "WINDOWS10",
        "사무용", "인강용", "가정용", "터치스크린",
    ]

    for word in remove_words:
        text = text.replace(word, "")

    return text


def normalize_brand(brand, title):
    text = (str(brand) + " " + str(title)).upper()

    if "삼성" in text or "갤럭시북" in text or "GALAXY" in text:
        return "삼성전자"

    if "LG" in text or "그램" in text:
        return "LG전자"

    if "레노버" in text or "LENOVO" in text or "THINKPAD" in text:
        return "레노버"

    if "APPLE" in text or "맥북" in text or "MACBOOK" in text:
        return "Apple"

    if brand:
        return str(brand).strip()

    return "브랜드미상"


def correct_cpu_from_title(title, cpu):
    """
    예전 CSV에 잘못 저장된 CPU 값을 보정한다.

    대표 오류:
    RAM32GB 안에 들어 있는 M3 문자열 때문에
    라이젠5 모델이 Apple M3로 잘못 분류된 적이 있음.
    """

    title_upper = str(title).upper().replace(" ", "")
    cpu = str(cpu).strip()

    # AMD Ryzen은 Apple M보다 먼저 판정한다.
    if "RYZEN7" in title_upper or "라이젠7" in title_upper:
        return "Ryzen 7"

    if "RYZEN5" in title_upper or "라이젠5" in title_upper:
        return "Ryzen 5"

    if "RYZEN3" in title_upper or "라이젠3" in title_upper:
        return "Ryzen 3"

    # Intel
    if "I9" in title_upper:
        return "i9"

    if "I7" in title_upper:
        return "i7"

    if "I5" in title_upper:
        return "i5"

    if "I3" in title_upper:
        return "i3"

    # Apple Silicon은 반드시 맥북/Apple 문맥이 있을 때만 인정한다.
    is_apple_product = (
        "맥북" in title
        or "MACBOOK" in title_upper
        or "APPLE" in title_upper
    )

    if is_apple_product:
        if "M4" in title_upper:
            return "Apple M4"
        if "M3" in title_upper:
            return "Apple M3"
        if "M2" in title_upper:
            return "Apple M2"
        if "M1" in title_upper:
            return "Apple M1"

    # 기존 CPU 값이 Apple M인데 제목이 Apple 제품이 아니면 빈 값으로 처리한다.
    if cpu.startswith("Apple") and not is_apple_product:
        return ""

    return cpu


def ram_size(ram):
    ram = str(ram).upper().replace(" ", "")

    if ram == "64GB":
        return 64
    if ram == "32GB":
        return 32
    if ram == "24GB":
        return 24
    if ram == "16GB":
        return 16
    if ram == "8GB":
        return 8
    if ram == "4GB":
        return 4

    return 0


def ssd_size(ssd):
    ssd = str(ssd).upper().replace(" ", "")

    if ssd == "2TB":
        return 2048
    if ssd == "1TB":
        return 1024
    if ssd == "512GB":
        return 512
    if ssd == "256GB":
        return 256
    if ssd == "128GB":
        return 128

    return 0


def extract_model_name(title):
    compact = normalize_text(title)

    patterns = [
        r"NT[0-9A-Z]{5,12}",
        r"[0-9]{2}Z[0-9A-Z]{3,12}",
        r"[0-9]{2}U[0-9A-Z]{3,12}",
        r"X13GEN[0-9]",
        r"X13",
        r"X390",
        r"T14S",
        r"T14",
        r"T490",
        r"T480",
        r"MACBOOKPRO[0-9]{4}",
        r"MACBOOKAIR[0-9]{4}",
        r"MACBOOKPRO",
        r"MACBOOKAIR",
    ]

    for pattern in patterns:
        match = re.search(pattern, compact)
        if match:
            return match.group(0)

    return compact[:32]


def make_group_key(row):
    title = row.get("title", "")
    brand = normalize_brand(row.get("brand", ""), title)
    model = extract_model_name(title)
    cpu = correct_cpu_from_title(title, row.get("cpu", ""))
    ram = row.get("ram", "").strip()
    ssd = row.get("ssd", "").strip()

    return f"{brand}|{model}|{cpu}|{ram}|{ssd}"


def is_practical_candidate(row):
    title = row.get("title", "")
    price = safe_int(row.get("price", 0))
    ram = row.get("ram", "")
    ssd = row.get("ssd", "")

    if any(word in title for word in rental_keywords):
        return False

    if price < 300000:
        return False

    if ram_size(ram) < 16:
        return False

    if ssd_size(ssd) < 512:
        return False

    return True


def calculate_buy_timing_score(avg_discount_rate, is_latest_min, observed_count, mall_count):
    """
    구매 적기 점수 = 100점 만점

    1. 평균 대비 할인율 점수: 최대 45점
       - 평균가보다 얼마나 저렴한가를 반영한다.
       - 예: 평균 대비 -10% 이하면 45점 만점.

    2. 최근 최저가 보너스: 최대 25점
       - 현재가가 관측 기간 최저가이면 강한 보너스를 준다.

    3. 관측 수 신뢰도: 최대 15점
       - 가격 관측 횟수가 많을수록 평균가 판단의 신뢰도가 높다.

    4. 판매처 수 신뢰도: 최대 15점
       - 여러 판매처에서 관측된 모델일수록 비교 신뢰도가 높다.
    """

    # 평균 대비 할인율 점수
    # avg_discount_rate는 음수일수록 평균보다 저렴하다는 뜻이다.
    if avg_discount_rate < 0:
        discount_score = min(abs(avg_discount_rate) * 4.5, 45)
    else:
        discount_score = 0

    # 최근 최저가 보너스
    lowest_score = 25 if is_latest_min else 0

    # 관측 수 신뢰도
    if observed_count >= 100:
        observation_score = 15
    elif observed_count >= 50:
        observation_score = 12
    elif observed_count >= 20:
        observation_score = 8
    elif observed_count >= 10:
        observation_score = 5
    else:
        observation_score = 2

    # 판매처 수 신뢰도
    if mall_count >= 4:
        mall_score = 15
    elif mall_count == 3:
        mall_score = 12
    elif mall_count == 2:
        mall_score = 8
    elif mall_count == 1:
        mall_score = 4
    else:
        mall_score = 0

    total_score = discount_score + lowest_score + observation_score + mall_score

    return round(min(total_score, 100), 1)


def make_timing_signal(buy_timing_score, is_latest_min, avg_discount_rate):
    if buy_timing_score >= 80:
        return "구매 적기"

    if buy_timing_score >= 65:
        return "구매 유리"

    if is_latest_min:
        return "최근 최저가"

    if avg_discount_rate <= -5:
        return "평균 대비 저렴"

    return "가격 관찰"


history = defaultdict(list)

with open(input_filename, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        product_id = row.get("product_id", "")
        title = fix_name(row.get("title", ""))
        price = safe_int(row.get("price", 0))
        collected_at = row.get("collected_at", "")
        date = parse_date(collected_at)

        if not product_id or price <= 0 or date is None:
            continue

        if not is_practical_candidate(row):
            continue

        corrected_cpu = correct_cpu_from_title(title, row.get("cpu", ""))

        row["title"] = title
        row["cpu"] = corrected_cpu

        group_key = make_group_key(row)

        history[group_key].append({
            "date": str(date),
            "product_id": product_id,
            "group_key": group_key,
            "title": title,
            "price": price,
            "mall": row.get("mall", ""),
            "brand": normalize_brand(row.get("brand", ""), title),
            "ram": row.get("ram", ""),
            "ssd": row.get("ssd", ""),
            "cpu": corrected_cpu,
            "link": row.get("link", ""),
        })


summary_rows = []

for group_key, rows in history.items():
    rows.sort(key=lambda x: (x["date"], x["price"]))

    prices = [row["price"] for row in rows]
    unique_prices = sorted(set(prices))

    first_date = rows[0]["date"]
    latest_date = rows[-1]["date"]

    first_rows = [row for row in rows if row["date"] == first_date]
    latest_rows = [row for row in rows if row["date"] == latest_date]

    first_price = min(row["price"] for row in first_rows)
    latest_row = min(latest_rows, key=lambda x: x["price"])
    latest_price = latest_row["price"]

    min_price = min(prices)
    max_price = max(prices)
    avg_price = round(sum(prices) / len(prices))

    if first_price > 0:
        period_change_rate = round((latest_price - first_price) / first_price * 100, 2)
    else:
        period_change_rate = 0

    if avg_price > 0:
        avg_discount_rate = round((latest_price - avg_price) / avg_price * 100, 2)
    else:
        avg_discount_rate = 0

    mall_count = len(set(row["mall"] for row in rows if row["mall"]))
    seller_count = len(set(row["product_id"] for row in rows if row["product_id"]))

    is_latest_min = latest_price == min_price and len(unique_prices) >= 2
    buy_timing_score = calculate_buy_timing_score(
        avg_discount_rate=avg_discount_rate,
        is_latest_min=is_latest_min,
        observed_count=len(rows),
        mall_count=mall_count,
    )
    timing_signal = make_timing_signal(
        buy_timing_score=buy_timing_score,
        is_latest_min=is_latest_min,
        avg_discount_rate=avg_discount_rate,
    )

    summary_rows.append({
        "group_key": group_key,
        "product_id": latest_row["product_id"],
        "title": latest_row["title"],
        "brand": latest_row["brand"],
        "ram": latest_row["ram"],
        "ssd": latest_row["ssd"],
        "cpu": latest_row["cpu"],
        "mall": latest_row["mall"],
        "first_price": first_price,
        "latest_price": latest_price,
        "min_price": min_price,
        "max_price": max_price,
        "avg_price": avg_price,
        "change_rate": avg_discount_rate,
        "period_change_rate": period_change_rate,
        "observed_count": len(rows),
        "seller_count": seller_count,
        "mall_count": mall_count,
        "is_latest_min": "Y" if is_latest_min else "N",
        "buy_timing_score": buy_timing_score,
        "first_date": first_date,
        "latest_date": latest_date,
        "timing_signal": timing_signal,
        "link": latest_row["link"],
    })


def summary_sort_key(row):
    return (
        -float(row["buy_timing_score"]),  # 구매 적기 점수 높은 순
        row["change_rate"],              # 평균 대비 더 저렴한 순
        -row["observed_count"],          # 관측 수 많은 순
        row["latest_price"],             # 현재가 낮은 순
    )


summary_rows.sort(key=summary_sort_key)

fieldnames = [
    "group_key",
    "product_id",
    "title",
    "brand",
    "ram",
    "ssd",
    "cpu",
    "mall",
    "first_price",
    "latest_price",
    "min_price",
    "max_price",
    "avg_price",
    "change_rate",
    "period_change_rate",
    "observed_count",
    "seller_count",
    "mall_count",
    "is_latest_min",
    "buy_timing_score",
    "first_date",
    "latest_date",
    "timing_signal",
    "link",
]

with open(output_filename, "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(summary_rows)


print("=" * 70)
print("가격 이력 분석 완료")
print("=" * 70)
print("모델/사양 그룹 수:", len(summary_rows))
print("저장 파일:", output_filename)

print()
print("[구매 적기 점수 TOP 10]")
for row in summary_rows[:10]:
    print("-" * 70)
    print("그룹키:", row["group_key"])
    print("상품명:", row["title"])
    print("구매 적기 점수:", row["buy_timing_score"])
    print("현재가:", f'{row["latest_price"]:,}원')
    print("최저가:", f'{row["min_price"]:,}원')
    print("평균가:", f'{row["avg_price"]:,}원')
    print("평균 대비:", str(row["change_rate"]) + "%")
    print("기간 변동률:", str(row["period_change_rate"]) + "%")
    print("관측 수:", row["observed_count"])
    print("판매처 수:", row["mall_count"])
    print("판단:", row["timing_signal"])
