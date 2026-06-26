import csv
from collections import Counter

csv_filename = "refurb_laptop_prices.csv"

total_rows = 0
product_ids = set()

keyword_counter = Counter()
ram_counter = Counter()
ssd_counter = Counter()
cpu_counter = Counter()
mall_counter = Counter()

with open(csv_filename, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        total_rows += 1

        product_id = row.get("product_id", "")
        keyword = row.get("keyword", "")
        ram = row.get("ram", "")
        ssd = row.get("ssd", "")
        cpu = row.get("cpu", "")
        mall = row.get("mall", "")

        if product_id:
            product_ids.add(product_id)

        keyword_counter[keyword] += 1
        mall_counter[mall] += 1

        if ram:
            ram_counter[ram] += 1
        else:
            ram_counter["미확인"] += 1

        if ssd:
            ssd_counter[ssd] += 1
        else:
            ssd_counter["미확인"] += 1

        if cpu:
            cpu_counter[cpu] += 1
        else:
            cpu_counter["미확인"] += 1


print("=" * 60)
print("리퍼/중고 노트북 가격 데이터 기본 현황")
print("=" * 60)

print("전체 수집 기록 수:", total_rows)
print("고유 product_id 수:", len(product_ids))

print("\n[검색어별 수집 건수]")
for keyword, count in keyword_counter.most_common():
    print(keyword, ":", count)

print("\n[RAM 분포]")
for ram, count in ram_counter.most_common():
    print(ram, ":", count)

print("\n[SSD 분포]")
for ssd, count in ssd_counter.most_common():
    print(ssd, ":", count)

print("\n[CPU 분포]")
for cpu, count in cpu_counter.most_common():
    print(cpu, ":", count)

print("\n[판매처 TOP 10]")
for mall, count in mall_counter.most_common(10):
    print(mall, ":", count)