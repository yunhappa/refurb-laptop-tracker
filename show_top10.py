import csv

filename = "scored_candidates.csv"

products = []

with open(filename, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        products.append(row)

products.sort(
    key=lambda x: float(x["value_score"]),
    reverse=True
)

print("=" * 70)
print("리퍼/중고 노트북 가성비 TOP 10")
print("=" * 70)

for index, product in enumerate(products[:10], start=1):
    print()
    print(f"{index}위")
    print("-" * 70)
    print("상품명:", product["title"])
    print("가격:", f'{int(product["price"]):,}원')
    print("판매처:", product["mall"])
    print("브랜드:", product["brand"])
    print("RAM:", product["ram"])
    print("SSD:", product["ssd"])
    print("CPU:", product["cpu"])
    print("사양 점수:", product["spec_score"])
    print("가성비 점수:", product["value_score"])
    print("링크:", product["link"])