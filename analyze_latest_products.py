import csv

csv_filename = "refurb_laptop_prices.csv"
output_filename = "candidate_products.csv"

latest_products = {}

exclude_words = [
    "대여",
    "렌탈",
    "임대",
    "렌트",
    "리스",
    "단기",
    "월렌탈"
]

min_price = 300000


def ram_score(ram):
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


def ssd_score(ssd):
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


with open(csv_filename, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        product_id = row.get("product_id", "")
        title = row.get("title", "")
        price = int(row.get("price", 0))
        ram = row.get("ram", "")
        ssd = row.get("ssd", "")

        if not product_id:
            continue

        if any(word in title for word in exclude_words):
            continue

        if price < min_price:
            continue

        if ram_score(ram) < 16:
            continue

        if ssd_score(ssd) < 512:
            continue

        latest_products[product_id] = row


products = list(latest_products.values())
products.sort(key=lambda x: int(x["price"]))

print("=" * 60)
print("실사용 후보: RAM 16GB 이상 + SSD 512GB 이상")
print("=" * 60)

print("조건 만족 고유 상품 수:", len(products))

print("\n[추천 후보 최저가 TOP 20]")

for product in products[:20]:
    print("-" * 60)
    print("상품명:", product["title"])
    print("가격:", f'{int(product["price"]):,}원')
    print("판매처:", product["mall"])
    print("브랜드:", product["brand"])
    print("제조사:", product["maker"])
    print("RAM:", product["ram"])
    print("SSD:", product["ssd"])
    print("CPU:", product["cpu"])
    print("링크:", product["link"])


with open(output_filename, "w", newline="", encoding="utf-8-sig") as file:
    fieldnames = [
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
    ]

    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()

    for product in products:
        writer.writerow({
            "collected_at": product.get("collected_at", ""),
            "keyword": product.get("keyword", ""),
            "product_id": product.get("product_id", ""),
            "title": product.get("title", ""),
            "price": product.get("price", ""),
            "mall": product.get("mall", ""),
            "brand": product.get("brand", ""),
            "maker": product.get("maker", ""),
            "ram": product.get("ram", ""),
            "ssd": product.get("ssd", ""),
            "cpu": product.get("cpu", ""),
            "link": product.get("link", "")
        })

print("\n후보 상품 CSV 저장 완료!")
print("저장 파일:", output_filename)