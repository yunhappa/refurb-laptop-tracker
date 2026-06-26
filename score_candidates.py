import csv

input_filename = "candidate_products.csv"
output_filename = "scored_candidates.csv"


def ram_score(ram):
    if ram == "32GB":
        return 32
    if ram == "24GB":
        return 24
    if ram == "16GB":
        return 16
    if ram == "8GB":
        return 8
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
    return 0


def fix_cpu_from_title(title, cpu):
    text = title.upper().replace(" ", "")

    if "RYZEN7" in text or "라이젠7" in text:
        return "Ryzen 7"
    if "RYZEN5" in text or "라이젠5" in text:
        return "Ryzen 5"
    if "RYZEN3" in text or "라이젠3" in text:
        return "Ryzen 3"

    return cpu


def cpu_score(cpu):
    if cpu == "i9":
        return 90
    if cpu == "i7":
        return 70
    if cpu == "i5":
        return 50
    if cpu == "i3":
        return 30
    if cpu == "Apple M4":
        return 90
    if cpu == "Apple M3":
        return 80
    if cpu == "Apple M2":
        return 70
    if cpu == "Apple M1":
        return 60
    if cpu == "Ryzen 7":
        return 70
    if cpu == "Ryzen 5":
        return 50
    if cpu == "Ryzen 3":
        return 30
    return 0


products = []

with open(input_filename, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        price = int(row["price"])
        ram = row.get("ram", "")
        ssd = row.get("ssd", "")
        cpu = row.get("cpu", "")

        cpu = fix_cpu_from_title(row.get("title", ""), cpu)
        row["cpu"] = cpu

        spec_score = (
            ram_score(ram) * 3
            + ssd_score(ssd) * 0.05
            + cpu_score(cpu)
        )

        if spec_score == 0:
            value_score = 0
        else:
            value_score = spec_score / (price / 1000000)

        row["spec_score"] = round(spec_score, 2)
        row["value_score"] = round(value_score, 2)

        products.append(row)


products.sort(key=lambda x: float(x["value_score"]), reverse=True)

print("=" * 60)
print("가성비 후보 TOP 20")
print("=" * 60)

for product in products[:20]:
    print("-" * 60)
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


fieldnames = list(products[0].keys())

with open(output_filename, "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(products)

print("\n가성비 점수 CSV 저장 완료!")
print("저장 파일:", output_filename)