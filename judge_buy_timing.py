import csv

input_filename = "best_by_model.csv"
output_filename = "buy_timing_result.csv"

products = []

with open(input_filename, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        value_score = float(row.get("value_score", 0))
        seller_count = int(row.get("seller_count", 0))
        mall_count = int(row.get("mall_count", 0))
        price_gap = int(row.get("price_gap_in_group", 0))

        if value_score >= 280 and mall_count >= 2:
            decision = "구매 추천"
            reason = "가성비 점수가 높고, 여러 판매처 비교가 가능한 상품입니다."
        elif value_score >= 240 and mall_count >= 2:
            decision = "구매 고려"
            reason = "가성비가 양호하고, 동일 모델의 판매처 비교가 가능합니다."
        elif value_score >= 240 and mall_count == 1:
            decision = "데이터 부족"
            reason = "가성비 점수는 높지만 동일 모델의 비교 판매처가 부족합니다."
        else:
            decision = "보류"
            reason = "현재 기준으로는 가성비 점수가 상대적으로 낮습니다."

        if price_gap >= 100000:
            reason += " 다만 판매처별 가격 차이가 커서 최저가 판매처 확인이 필요합니다."

        row["buy_decision"] = decision
        row["decision_reason"] = reason

        products.append(row)


print("=" * 70)
print("구매 적기 판단 TOP 10")
print("=" * 70)

for index, product in enumerate(products[:10], start=1):
    print()
    print(f"{index}위")
    print("-" * 70)
    print("모델키:", product["model_key"])
    print("상품명:", product["title"])
    print("가격:", f'{int(product["price"]):,}원')
    print("판매처:", product["mall"])
    print("가성비 점수:", product["value_score"])
    print("동일 모델 후보 수:", product["seller_count"])
    print("판매처 수:", product["mall_count"])
    print("가격 차이:", f'{int(product["price_gap_in_group"]):,}원')
    print("판단:", product["buy_decision"])
    print("이유:", product["decision_reason"])
    print("링크:", product["link"])


fieldnames = list(products[0].keys())

with open(output_filename, "w", newline="", encoding="utf-8-sig") as file:
    writer = csv.DictWriter(file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(products)

print()
print("구매 판단 CSV 저장 완료!")
print("저장 파일:", output_filename)