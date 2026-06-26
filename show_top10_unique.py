import csv
import re

input_filename = "scored_candidates.csv"
output_filename = "best_by_model.csv"


def extract_model_key(row):
    title = row.get("title", "")
    brand = row.get("brand", "")
    maker = row.get("maker", "")
    ram = row.get("ram", "")
    ssd = row.get("ssd", "")
    cpu = row.get("cpu", "")

    text = title.upper().replace(" ", "")

    model = ""

    # 브랜드 정규화
    base_brand = brand or maker or ""

    if "삼성" in base_brand:
        base_brand = "삼성전자"
    elif "LG" in base_brand.upper():
        base_brand = "LG전자"
    elif "레노버" in base_brand or "LENOVO" in base_brand.upper():
        base_brand = "레노버"
    elif "APPLE" in base_brand.upper() or "애플" in base_brand:
        base_brand = "Apple"

    # 제목에 맥북이 있으면 브랜드를 Apple로 보정
    if "MACBOOK" in text or "맥북" in title:
        base_brand = "Apple"

    # 제목에 레노버/ThinkPad가 있으면 브랜드를 레노버로 보정
    if "THINKPAD" in text or "씽크패드" in title or "LENOVO" in text or "레노버" in title:
        base_brand = "레노버"

    # ThinkPad 계열
    thinkpad_match = re.search(
        r"(X13|X390|T14S|T14|T580|E450|T430U|L410)",
        text
    )

    if "THINKPAD" in text or "씽크패드" in title:
        if thinkpad_match:
            model = "ThinkPad " + thinkpad_match.group(1)
        else:
            model = "ThinkPad"

    # 삼성 NT 모델 코드
    if not model:
        samsung_match = re.search(r"(NT[A-Z0-9]{5,})", text)
        if samsung_match:
            model = samsung_match.group(1)

    # LG 모델 코드
    # LG 브랜드/제목일 때만 LG 모델명을 찾음
    if not model and ("LG" in text or "그램" in title):
        lg_match = re.search(r"(\d{2}U\d{2,3}[A-Z]?)", text)
        if lg_match:
            model = lg_match.group(1)

    # 맥북 계열
    if not model:
        if "MACBOOKPRO" in text or "맥북프로" in title:
            year_match = re.search(r"(201[0-9]|202[0-9])", text)
            if year_match:
                model = "MacBook Pro " + year_match.group(1)
            else:
                model = "MacBook Pro"

        elif "MACBOOKAIR" in text or "맥북에어" in title:
            year_match = re.search(r"(201[0-9]|202[0-9])", text)
            if year_match:
                model = "MacBook Air " + year_match.group(1)
            else:
                model = "MacBook Air"

    # 모델을 못 찾으면 제목 일부를 사용
    if not model:
        model = re.sub(r"[^A-Z0-9가-힣]", "", title.upper())[:30]

    return f"{base_brand}|{model}|{cpu}|{ram}|{ssd}"


products = []

with open(input_filename, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        row["model_key"] = extract_model_key(row)
        products.append(row)


groups = {}

for product in products:
    key = product["model_key"]
    price = int(product["price"])

    if key not in groups:
        groups[key] = {
            "best_product": product,
            "seller_count": 1,
            "all_malls": {product.get("mall", "")},
            "all_prices": [price],
        }
    else:
        groups[key]["seller_count"] += 1
        groups[key]["all_malls"].add(product.get("mall", ""))
        groups[key]["all_prices"].append(price)

        current_best_price = int(groups[key]["best_product"]["price"])

        if price < current_best_price:
            groups[key]["best_product"] = product


best_products = []

for key, group in groups.items():
    product = group["best_product"]

    product["seller_count"] = group["seller_count"]
    product["mall_count"] = len(group["all_malls"])
    product["min_price_in_group"] = min(group["all_prices"])
    product["max_price_in_group"] = max(group["all_prices"])
    product["price_gap_in_group"] = (
        max(group["all_prices"]) - min(group["all_prices"])
    )

    best_products.append(product)


best_products.sort(key=lambda x: float(x["value_score"]), reverse=True)

print("=" * 70)
print("모델/사양 기준 가성비 TOP 10")
print("=" * 70)

for index, product in enumerate(best_products[:10], start=1):
    print()
    print(f"{index}위")
    print("-" * 70)
    print("모델키:", product["model_key"])
    print("상품명:", product["title"])
    print("가격:", f'{int(product["price"]):,}원')
    print("판매처:", product["mall"])
    print("브랜드:", product["brand"])
    print("RAM:", product["ram"])
    print("SSD:", product["ssd"])
    print("CPU:", product["cpu"])
    print("가성비 점수:", product["value_score"])
    print("동일 모델 후보 수:", product["seller_count"])
    print("판매처 수:", product["mall_count"])
    print("그룹 내 최저가:", f'{int(product["min_price_in_group"]):,}원')
    print("그룹 내 최고가:", f'{int(product["max_price_in_group"]):,}원')
    print("가격 차이:", f'{int(product["price_gap_in_group"]):,}원')
    print("링크:", product["link"])


fieldnames = list(best_products[0].keys())

with open(output_filename, "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(best_products)

print()
print("모델별 최저가 CSV 저장 완료!")
print("저장 파일:", output_filename)
print("모델/사양 그룹 수:", len(best_products))