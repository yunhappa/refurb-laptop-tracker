import csv

input_filename = "buy_timing_result.csv"


def normalize_text(text):
    return text.lower().replace(" ", "")


def normalize_ram(text):
    text = text.strip().upper().replace(" ", "")

    if not text:
        return ""

    text = text.replace("기가", "GB")
    text = text.replace("GBB", "GB")

    # 숫자만 입력한 경우: 16 -> 16GB
    if text.isdigit():
        return text + "GB"

    # 16G -> 16GB
    if text.endswith("G") and not text.endswith("GB"):
        text = text[:-1] + "GB"

    return text


def normalize_ssd(text):
    text = text.strip().upper().replace(" ", "")

    if not text:
        return ""

    text = text.replace("기가", "GB")
    text = text.replace("테라", "TB")
    text = text.replace("GBB", "GB")
    text = text.replace("TBB", "TB")

    # 숫자만 입력한 경우
    if text.isdigit():
        number = int(text)

        # SSD에서 1, 2는 보통 1TB, 2TB 의미로 처리
        if number in [1, 2, 4]:
            return str(number) + "TB"

        # 128, 256, 512, 1024는 GB로 처리
        return str(number) + "GB"

    # 512G -> 512GB
    if text.endswith("G") and not text.endswith("GB"):
        text = text[:-1] + "GB"

    # 1T -> 1TB
    if text.endswith("T") and not text.endswith("TB"):
        text = text[:-1] + "TB"

    # 1024GB -> 1TB
    if text == "1024GB":
        text = "1TB"

    # 2048GB -> 2TB
    if text == "2048GB":
        text = "2TB"

    return text


def normalize_cpu(text):
    text = text.strip().lower().replace(" ", "")

    if not text:
        return ""

    # 숫자만 입력한 경우: 5 -> i5, 7 -> i7
    if text == "3":
        return "i3"
    if text == "5":
        return "i5"
    if text == "7":
        return "i7"
    if text == "9":
        return "i9"

    return text


def decision_priority(decision):
    if decision == "구매 추천":
        return 4
    if decision == "구매 고려":
        return 3
    if decision == "데이터 부족":
        return 2
    if decision == "보류":
        return 1
    return 0


def product_sort_key(product):
    return (
        decision_priority(product.get("buy_decision", "")),
        float(product.get("value_score", 0))
    )


def is_match(row, keyword, ram_filter, ssd_filter, cpu_filter, max_price):
    title = row.get("title", "")
    model_key = row.get("model_key", "")
    brand = row.get("brand", "")
    ram = row.get("ram", "")
    ssd = row.get("ssd", "")
    cpu = row.get("cpu", "")
    price = int(row.get("price", 0))

    search_text = normalize_text(title + " " + model_key + " " + brand)

    if keyword and keyword not in search_text:
        return False

    if ram_filter and normalize_ram(ram) != normalize_ram(ram_filter):
        return False

    if ssd_filter and normalize_ssd(ssd) != normalize_ssd(ssd_filter):
        return False

    if cpu_filter and normalize_cpu(cpu) != normalize_cpu(cpu_filter):
        return False

    if max_price is not None and price > max_price:
        return False

    return True


def print_products(products, title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    if not products:
        print("표시할 상품이 없습니다.")
        return

    print(f"상품 수: {len(products)}개")

    for index, product in enumerate(products[:10], start=1):
        print()
        print(f"{index}위")
        print("-" * 70)
        print("판단:", product.get("buy_decision", ""))
        print("이유:", product.get("decision_reason", ""))
        print("모델키:", product.get("model_key", ""))
        print("상품명:", product.get("title", ""))
        print("가격:", f'{int(product.get("price", 0)):,}원')
        print("판매처:", product.get("mall", ""))
        print("브랜드:", product.get("brand", ""))
        print("RAM:", product.get("ram", ""))
        print("SSD:", product.get("ssd", ""))
        print("CPU:", product.get("cpu", ""))
        print("가성비 점수:", product.get("value_score", ""))
        print("동일 모델 후보 수:", product.get("seller_count", ""))
        print("판매처 수:", product.get("mall_count", ""))
        print("가격 차이:", f'{int(product.get("price_gap_in_group", 0)):,}원')
        print("링크:", product.get("link", ""))


print("=" * 70)
print("리퍼/중고 노트북 구매 판단 검색기")
print("=" * 70)

print("\n찾고 싶은 조건을 입력하세요.")
print("그냥 Enter를 누르면 해당 조건은 건너뜁니다.")
print("RAM은 16, 16GB처럼 입력할 수 있습니다.")
print("SSD는 512, 512GB, 1TB처럼 입력할 수 있습니다.\n")

keyword_input = input("모델/브랜드/상품명 키워드 예: ThinkPad, 맥북, LG그램, 삼성: ")
ram_input = input("RAM 예: 16, 16GB, 32GB: ")
ssd_input = input("SSD 예: 512, 512GB, 1TB: ")
cpu_input = input("CPU 예: i5, i7, Ryzen 5: ")
max_price_input = input("최대 가격 예: 700000: ")

keyword = normalize_text(keyword_input)
ram_filter = normalize_ram(ram_input)
ssd_filter = normalize_ssd(ssd_input)
cpu_filter = normalize_cpu(cpu_input)

if max_price_input.strip():
    max_price = int(max_price_input.replace(",", ""))
else:
    max_price = None


print()
print("=" * 70)
print("입력한 검색 조건")
print("=" * 70)
print("키워드:", keyword_input if keyword_input else "전체")
print("RAM:", ram_filter if ram_filter else "전체")
print("SSD:", ssd_filter if ssd_filter else "전체")
print("CPU:", cpu_filter if cpu_filter else "전체")
print("최대 가격:", f"{max_price:,}원" if max_price is not None else "제한 없음")


all_products = []

with open(input_filename, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        all_products.append(row)


exact_products = []

for row in all_products:
    if is_match(row, keyword, ram_filter, ssd_filter, cpu_filter, max_price):
        exact_products.append(row)

exact_products.sort(key=product_sort_key, reverse=True)


if exact_products:
    print_products(exact_products, "정확히 일치하는 검색 결과")
else:
    print()
    print("=" * 70)
    print("정확히 일치하는 상품이 없습니다.")
    print("=" * 70)
    print("대신 조건을 조금 완화한 유사 상품을 찾아봅니다.")

    # 1차 완화: CPU 조건 제거
    relaxed_cpu_products = []

    for row in all_products:
        if is_match(row, keyword, ram_filter, ssd_filter, "", max_price):
            relaxed_cpu_products.append(row)

    relaxed_cpu_products.sort(key=product_sort_key, reverse=True)

    if relaxed_cpu_products:
        print_products(
            relaxed_cpu_products,
            "유사 상품 추천: CPU 조건을 제외한 결과"
        )
    else:
        # 2차 완화: CPU 조건 + 최대 가격 조건 제거
        relaxed_price_products = []

        for row in all_products:
            if is_match(row, keyword, ram_filter, ssd_filter, "", None):
                relaxed_price_products.append(row)

        relaxed_price_products.sort(key=product_sort_key, reverse=True)

        if relaxed_price_products:
            print_products(
                relaxed_price_products,
                "유사 상품 추천: CPU와 최대 가격 조건을 제외한 결과"
            )
        else:
            # 3차 완화: 키워드만 적용
            keyword_only_products = []

            for row in all_products:
                if is_match(row, keyword, "", "", "", None):
                    keyword_only_products.append(row)

            keyword_only_products.sort(key=product_sort_key, reverse=True)

            if keyword_only_products:
                print_products(
                    keyword_only_products,
                    "유사 상품 추천: 키워드만 적용한 결과"
                )
            else:
                print()
                print("키워드 기준으로도 유사 상품을 찾지 못했습니다.")


print()
print("검색 종료")