import csv
import html
from collections import Counter
from urllib.parse import urlencode
import os
from flask import Flask, request, Response

INPUT_FILENAME = "buy_timing_result.csv"


PURPOSE_PRESETS = {
    "student": {
        "label": "대학생용",
        "keyword": "",
        "ram": "16GB",
        "ssd": "512GB",
        "cpu": "",
        "max_price": "700000",
        "sort": "recommend",
        "desc": "과제, 문서작업, 온라인 강의용으로 무난한 조건"
    },
    "office": {
        "label": "사무용",
        "keyword": "ThinkPad",
        "ram": "16GB",
        "ssd": "512GB",
        "cpu": "",
        "max_price": "700000",
        "sort": "recommend",
        "desc": "문서작업과 업무용으로 안정적인 비즈니스 노트북 중심"
    },
    "portable": {
        "label": "휴대용",
        "keyword": "LG그램",
        "ram": "16GB",
        "ssd": "512GB",
        "cpu": "",
        "max_price": "",
        "sort": "price_asc",
        "desc": "가벼운 휴대성을 우선해 LG그램 계열 중심"
    },
    "developer": {
        "label": "개발용",
        "keyword": "",
        "ram": "32GB",
        "ssd": "1TB",
        "cpu": "",
        "max_price": "1000000",
        "sort": "value_desc",
        "desc": "멀티태스킹과 개발 환경을 고려한 32GB RAM / 1TB SSD 조건"
    },
    "power": {
        "label": "고성능",
        "keyword": "",
        "ram": "32GB",
        "ssd": "1TB",
        "cpu": "i7",
        "max_price": "",
        "sort": "value_desc",
        "desc": "고성능 CPU와 넉넉한 메모리·저장공간 중심"
    },
    "budget": {
        "label": "가성비",
        "keyword": "",
        "ram": "16GB",
        "ssd": "512GB",
        "cpu": "",
        "max_price": "500000",
        "sort": "value_desc",
        "desc": "50만원 이하에서 실사용 가능한 가성비 후보 중심"
    },
}

SORT_OPTIONS = {
    "recommend": "추천순",
    "price_asc": "낮은 가격순",
    "value_desc": "가성비 점수순",
    "seller_desc": "판매처 많은 순",
    "gap_desc": "가격 차이 큰 순",
}



def esc(value):
    return html.escape(str(value))


def fix_product_name(text):
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


def safe_int(value):
    try:
        return int(str(value).replace(",", ""))
    except Exception:
        return 0


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def read_csv_rows(filename):
    try:
        with open(filename, "r", encoding="utf-8-sig") as file:
            return list(csv.DictReader(file))
    except FileNotFoundError:
        return []


def normalize_text(text):
    return text.lower().replace(" ", "")


def normalize_ram(text):
    text = text.strip().upper().replace(" ", "")
    if not text:
        return ""
    text = text.replace("기가", "GB").replace("GBB", "GB")
    if text.isdigit():
        return text + "GB"
    if text.endswith("G") and not text.endswith("GB"):
        return text[:-1] + "GB"
    return text


def normalize_ssd(text):
    text = text.strip().upper().replace(" ", "")
    if not text:
        return ""
    text = (
        text.replace("기가", "GB")
        .replace("테라", "TB")
        .replace("GBB", "GB")
        .replace("TBB", "TB")
    )
    if text.isdigit():
        number = int(text)
        if number in [1, 2, 4]:
            return f"{number}TB"
        return f"{number}GB"
    if text.endswith("G") and not text.endswith("GB"):
        text = text[:-1] + "GB"
    if text.endswith("T") and not text.endswith("TB"):
        text = text[:-1] + "TB"
    if text == "1024GB":
        return "1TB"
    if text == "2048GB":
        return "2TB"
    return text


def normalize_cpu(text):
    text = text.strip().lower().replace(" ", "")
    if not text:
        return ""
    if text == "3":
        return "i3"
    if text == "5":
        return "i5"
    if text == "7":
        return "i7"
    if text == "9":
        return "i9"
    return text


def parse_max_price(text):
    text = text.strip()
    if not text:
        return None
    try:
        return int(text.replace(",", ""))
    except ValueError:
        return None


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



def normalize_sort_key(sort_key):
    if sort_key in SORT_OPTIONS:
        return sort_key
    return "recommend"


def get_sort_label(sort_key):
    return SORT_OPTIONS.get(normalize_sort_key(sort_key), "추천순")


def get_purpose_label(purpose):
    if purpose in PURPOSE_PRESETS:
        return PURPOSE_PRESETS[purpose]["label"]
    return "직접 검색"


def apply_purpose_defaults(purpose, keyword, ram, ssd, cpu, max_price, sort_key):
    preset = PURPOSE_PRESETS.get(purpose)

    if not preset:
        return keyword, ram, ssd, cpu, max_price, normalize_sort_key(sort_key)

    if not keyword:
        keyword = preset.get("keyword", "")
    if not ram:
        ram = preset.get("ram", "")
    if not ssd:
        ssd = preset.get("ssd", "")
    if not cpu:
        cpu = preset.get("cpu", "")
    if not max_price:
        max_price = preset.get("max_price", "")
    if not sort_key or sort_key == "recommend":
        sort_key = preset.get("sort", "recommend")

    return keyword, ram, ssd, cpu, max_price, normalize_sort_key(sort_key)


def sort_products(products, sort_key):
    sort_key = normalize_sort_key(sort_key)

    if sort_key == "price_asc":
        return sorted(
            products,
            key=lambda row: (
                safe_int(row.get("price", 0)) if safe_int(row.get("price", 0)) > 0 else 10**12,
                -safe_float(row.get("value_score", 0)),
            )
        )

    if sort_key == "value_desc":
        return sorted(
            products,
            key=lambda row: (
                safe_float(row.get("value_score", 0)),
                decision_priority(row.get("buy_decision", "")),
                max(safe_int(row.get("mall_count", 0)), safe_int(row.get("seller_count", 0))),
            ),
            reverse=True
        )

    if sort_key == "seller_desc":
        return sorted(
            products,
            key=lambda row: (
                max(safe_int(row.get("mall_count", 0)), safe_int(row.get("seller_count", 0))),
                safe_float(row.get("value_score", 0)),
                decision_priority(row.get("buy_decision", "")),
            ),
            reverse=True
        )

    if sort_key == "gap_desc":
        return sorted(
            products,
            key=lambda row: (
                safe_int(row.get("price_gap_in_group", 0)),
                safe_float(row.get("value_score", 0)),
            ),
            reverse=True
        )

    return sorted(products, key=product_sort_key, reverse=True)


def build_result_url(result, sort_key):
    params = {}

    purpose = result.get("purpose", "")
    if purpose:
        params["purpose"] = purpose

    for key in ["keyword", "ram", "ssd", "cpu"]:
        value = result.get(key, "")
        if value:
            params[key] = value

    max_price = result.get("max_price")
    if max_price is not None:
        params["max_price"] = str(max_price)

    params["sort"] = normalize_sort_key(sort_key)

    return "/?" + urlencode(params) + "#results"


def render_sort_controls(result):
    current_sort = normalize_sort_key(result.get("sort", "recommend"))
    links = []

    for sort_key, label in SORT_OPTIONS.items():
        active_class = "active" if sort_key == current_sort else ""
        url = build_result_url(result, sort_key)
        links.append(f'<a class="{active_class}" href="{esc(url)}">{esc(label)}</a>')

    return f"""
    <div class="result-toolbar">
        <div>
            <b>정렬 바꾸기</b>
            <span>가격을 먼저 볼지, 가성비를 먼저 볼지, 판매처가 많은 상품을 먼저 볼지 선택할 수 있습니다.</span>
        </div>
        <div class="sort-links">
            {''.join(links)}
        </div>
    </div>
    """



def product_sort_key(product):
    return (
        decision_priority(product.get("buy_decision", "")),
        safe_float(product.get("value_score", 0)),
    )


def get_project_stats():
    raw_rows = read_csv_rows("refurb_laptop_prices.csv")
    candidate_rows = read_csv_rows("candidate_products.csv")
    model_rows = read_csv_rows("best_by_model.csv")
    buy_rows = read_csv_rows("buy_timing_result.csv")

    product_ids = set()
    collected_dates = []

    for row in raw_rows:
        product_id = row.get("product_id", "")
        collected_at = row.get("collected_at", "")
        if product_id:
            product_ids.add(product_id)
        if collected_at:
            collected_dates.append(collected_at)

    decision_counter = Counter()
    for row in buy_rows:
        decision_counter[row.get("buy_decision", "미분류")] += 1

    return {
        "raw_count": len(raw_rows),
        "unique_product_count": len(product_ids),
        "candidate_count": len(candidate_rows),
        "model_group_count": len(model_rows),
        "buy_count": len(buy_rows),
        "first_collected": min(collected_dates) if collected_dates else "확인 불가",
        "last_collected": max(collected_dates) if collected_dates else "확인 불가",
        "recommend_count": decision_counter.get("구매 추천", 0),
        "consider_count": decision_counter.get("구매 고려", 0),
        "lack_count": decision_counter.get("데이터 부족", 0),
        "hold_count": decision_counter.get("보류", 0),
    }


def read_products():
    return read_csv_rows(INPUT_FILENAME)


def is_match(row, keyword, ram_filter, ssd_filter, cpu_filter, max_price):
    title = row.get("title", "")
    model_key = row.get("model_key", "")
    brand = row.get("brand", "")
    ram = row.get("ram", "")
    ssd = row.get("ssd", "")
    cpu = row.get("cpu", "")
    price = safe_int(row.get("price", 0))

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


def search_products(keyword_input, ram_input, ssd_input, cpu_input, max_price_input, sort_input='recommend', purpose_input=''):
    keyword = normalize_text(keyword_input)
    ram_filter = normalize_ram(ram_input)
    ssd_filter = normalize_ssd(ssd_input)
    cpu_filter = normalize_cpu(cpu_input)
    max_price = parse_max_price(max_price_input)

    all_products = read_products()

    exact_products = [
        row for row in all_products
        if is_match(row, keyword, ram_filter, ssd_filter, cpu_filter, max_price)
    ]
    exact_products.sort(key=product_sort_key, reverse=True)

    if exact_products:
        search_type = "조건에 맞는 상품"
        products = exact_products
    else:
        relaxed_cpu_products = [
            row for row in all_products
            if is_match(row, keyword, ram_filter, ssd_filter, "", max_price)
        ]
        relaxed_cpu_products.sort(key=product_sort_key, reverse=True)

        if relaxed_cpu_products:
            search_type = "CPU 조건을 조금 넓혀 찾은 상품"
            products = relaxed_cpu_products
        else:
            relaxed_price_products = [
                row for row in all_products
                if is_match(row, keyword, ram_filter, ssd_filter, "", None)
            ]
            relaxed_price_products.sort(key=product_sort_key, reverse=True)

            if relaxed_price_products:
                search_type = "CPU와 가격 조건을 조금 넓혀 찾은 상품"
                products = relaxed_price_products
            else:
                keyword_only_products = [
                    row for row in all_products
                    if is_match(row, keyword, "", "", "", None)
                ]
                keyword_only_products.sort(key=product_sort_key, reverse=True)

                if keyword_only_products:
                    search_type = "키워드 기준으로 찾은 상품"
                    products = keyword_only_products
                else:
                    search_type = "조건에 맞는 상품이 없습니다"
                    products = []

    sort_key = normalize_sort_key(sort_input)
    products = sort_products(products, sort_key)

    return {
        "search_type": search_type,
        "products": products,
        "keyword": keyword_input,
        "ram": ram_filter,
        "ssd": ssd_filter,
        "cpu": cpu_filter,
        "max_price": max_price,
        "sort": sort_key,
        "purpose": purpose_input,
    }


def get_decision_class(decision):
    if decision == "구매 추천":
        return "recommend"
    if decision == "구매 고려":
        return "consider"
    if decision == "데이터 부족":
        return "lack"
    return "hold"


def make_summary_sentence(product):
    decision = product.get("buy_decision", "")
    value_score = product.get("value_score", "")
    mall_count = safe_int(product.get("mall_count", 0))
    price_gap = safe_int(product.get("price_gap_in_group", 0))

    if decision == "구매 추천":
        return (
            f"한줄 판단: 조건이 잘 맞는 편입니다. "
            f"가성비 점수는 {value_score}점이며, 동일 모델을 여러 판매처에서 비교할 수 있습니다."
        )
    if decision == "구매 고려":
        return (
            f"한줄 판단: 후보에 올려두고 비교해 볼 만합니다. "
            f"가성비 점수는 {value_score}점이며, 판매처 {mall_count}곳의 가격 비교가 가능합니다."
        )
    if decision == "데이터 부족":
        return (
            f"한줄 판단: 가성비 점수는 {value_score}점으로 높지만, "
            f"비교할 만한 같은 모델이 적어 상세 페이지 확인이 필요합니다."
        )
    if price_gap >= 100000:
        return (
            "한줄 판단: 지금 바로 고르기에는 아쉬운 점이 있습니다. "
            "다만 판매처마다 가격 차이가 커서 최저가와 상품 상태를 함께 확인해 보세요."
        )
    return (
        "한줄 판단: 지금 바로 고르기에는 아쉬운 점이 있습니다. "
        "가격이나 비교 데이터가 아직 충분히 매력적이지 않습니다."
    )



def get_latest_update_info():
    stats = get_project_stats()
    latest = stats.get("last_collected", "") or "-"
    if latest == "-":
        data_basis = "데이터 없음"
    else:
        data_basis = f"{latest} 기준"

    return {
        "latest_update": latest,
        "auto_update": "매일 오전 9시 17분쯤 자동 갱신",
        "data_basis": data_basis
    }



def get_confidence_label(product):
    mall_count = safe_int(product.get("mall_count", 0))
    seller_count = safe_int(product.get("seller_count", 0))
    observed_count = safe_int(product.get("observed_count", 0))

    comparison_count = max(mall_count, seller_count)

    if comparison_count >= 4 or observed_count >= 120:
        return "높음", "비교할 만한 같은 계열 상품이 비교적 충분합니다."
    if comparison_count >= 2 or observed_count >= 50:
        return "보통", "가격을 비교해 볼 만한 데이터가 어느 정도 있습니다."
    return "낮음", "비교 데이터가 적어 상세 페이지 확인이 특히 중요합니다."


def make_recommendation_points(product):
    decision = product.get("buy_decision", "")
    value_score = safe_float(product.get("value_score", 0))
    mall_count = safe_int(product.get("mall_count", 0))
    seller_count = safe_int(product.get("seller_count", 0))
    price_gap = safe_int(product.get("price_gap_in_group", 0))
    ram = product.get("ram", "")
    ssd = product.get("ssd", "")
    cpu = product.get("cpu", "")

    points = []

    if ram or ssd or cpu:
        spec_parts = []
        if ram:
            spec_parts.append(f"RAM {ram}")
        if ssd:
            spec_parts.append(f"SSD {ssd}")
        if cpu:
            spec_parts.append(f"CPU {cpu}")
        points.append(" / ".join(spec_parts) + " 조건을 기준으로 비교했습니다.")

    if value_score >= 280:
        points.append("가성비 점수가 높은 편이라 먼저 볼 만합니다.")
    elif value_score >= 240:
        points.append("가성비 점수가 나쁘지 않아 비교 후보로 볼 수 있습니다.")
    else:
        points.append("가성비 점수만 보면 조금 신중하게 볼 필요가 있습니다.")

    comparison_count = max(mall_count, seller_count)
    if comparison_count >= 2:
        points.append(f"비슷한 모델 {comparison_count}개를 기준으로 가격을 비교했습니다.")
    else:
        points.append("비교할 만한 같은 모델이 적어 상세 페이지 확인이 필요합니다.")

    if price_gap >= 100000:
        points.append(f"판매처마다 가격 차이가 {price_gap:,}원까지 벌어져 최저가와 상품 상태를 함께 볼 필요가 있습니다.")
    elif price_gap > 0:
        points.append(f"판매처별 가격 차이는 {price_gap:,}원입니다.")

    if decision == "구매 추천":
        points.append("가격과 사양 조건이 좋아 우선 추천으로 분류했습니다.")
    elif decision == "구매 고려":
        points.append("바로 결정하기보다는 상세 조건을 확인한 뒤 비교해 보세요.")
    elif decision == "데이터 부족":
        points.append("점수는 나쁘지 않지만 비교 데이터가 부족합니다.")
    else:
        points.append("가격이나 비교 데이터만 보면 아직은 보류에 가깝습니다.")

    return points[:5]


def get_top_recommendation_products(limit=3):
    products = read_products()
    products.sort(key=product_sort_key, reverse=True)
    return products[:limit]


def get_product_identity(product):
    return (
        product.get("model_key")
        or product.get("product_id")
        or product.get("title")
        or product.get("link")
        or ""
    )


def get_budget_pick(min_price, max_price, used_keys=None):
    used_keys = used_keys or set()

    products = []
    for row in read_products():
        price = safe_int(row.get("price", 0))
        identity = get_product_identity(row)

        if price <= 0:
            continue
        if identity in used_keys:
            continue
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue

        products.append(row)

    products.sort(key=product_sort_key, reverse=True)
    return products[0] if products else None


def get_market_signal():
    stats = get_project_stats()
    top_products = get_top_recommendation_products(3)
    price_rows = read_csv_rows("price_history_summary.csv")

    best_price_row = None
    if price_rows:
        price_rows.sort(key=lambda row: safe_float(row.get("buy_timing_score", 0)), reverse=True)
        best_price_row = price_rows[0]

    if top_products:
        best_product = top_products[0]
        best_title = fix_product_name(best_product.get("title", ""))
        best_price = safe_int(best_product.get("price", 0))
        best_score = safe_float(best_product.get("value_score", 0))
        best_decision = best_product.get("buy_decision", "")
        best_link = best_product.get("link", "")
    else:
        best_title = "아직 보여줄 후보가 없습니다"
        best_price = 0
        best_score = 0
        best_decision = "-"
        best_link = ""

    if best_price_row:
        timing_title = fix_product_name(best_price_row.get("title", ""))
        timing_price = safe_int(best_price_row.get("latest_price", 0))
        timing_score = safe_float(best_price_row.get("buy_timing_score", 0))
        timing_discount = best_price_row.get("change_rate", "")
        timing_link = best_price_row.get("link", "") or best_price_row.get("product_link", "")
    else:
        timing_title = "아직 가격 이력 후보가 없습니다"
        timing_price = 0
        timing_score = 0
        timing_discount = "-"
        timing_link = ""

    return {
        "stats": stats,
        "best_title": best_title,
        "best_price": best_price,
        "best_score": best_score,
        "best_decision": best_decision,
        "best_link": best_link,
        "timing_title": timing_title,
        "timing_price": timing_price,
        "timing_score": timing_score,
        "timing_discount": timing_discount,
        "timing_link": timing_link,
        "top_products": top_products,
    }


def render_signal_link(url):
    if not url:
        return ""
    return f'<a class="signal-link-button" href="{esc(url)}" target="_blank">상품 페이지 보기</a>'


def render_compact_product_pick(product, label):
    if not product:
        return f"""
        <div class="mini-pick-card">
            <div class="mini-pick-label">{esc(label)}</div>
            <h3>이 예산대는 아직 후보가 적습니다</h3>
            <p>데이터가 더 쌓이면 이 구간도 더 자연스럽게 보여드릴 수 있습니다.</p>
        </div>
        """

    title = esc(fix_product_name(product.get("title", "")))
    price = safe_int(product.get("price", 0))
    decision = esc(product.get("buy_decision", ""))
    score = esc(product.get("value_score", ""))
    link = esc(product.get("link", ""))

    return f"""
    <div class="mini-pick-card">
        <div class="mini-pick-label">{esc(label)}</div>
        <h3>{title}</h3>
        <p><b>{price:,}원</b> · {decision} · 가성비 {score}점</p>
        <a href="{link}" target="_blank">상품 보기</a>
    </div>
    """


def render_service_landing_section(keyword_value, ram_value, ssd_value, cpu_value, price_value):
    signal = get_market_signal()
    latest_info = get_latest_update_info()

    best_title = esc(signal["best_title"])
    timing_title = esc(signal["timing_title"])

    used_budget_keys = set()

    budget_50 = get_budget_pick(None, 500000, used_budget_keys)
    if budget_50:
        used_budget_keys.add(get_product_identity(budget_50))

    budget_70 = get_budget_pick(500001, 700000, used_budget_keys)
    if budget_70:
        used_budget_keys.add(get_product_identity(budget_70))

    budget_100 = get_budget_pick(700001, 1000000, used_budget_keys)
    if budget_100:
        used_budget_keys.add(get_product_identity(budget_100))

    return f"""
    <section class="service-landing">
        <div class="landing-left">
            <div class="landing-kicker">REFURB LAPTOP CHECKER</div>
            <h2>리퍼 노트북,<br>가격만 보고 고르기 어렵다면</h2>
            <p>
                현재가, 평균가, 최저가, 판매처 수, 기본 사양을 함께 보고
                먼저 살펴볼 만한 후보를 골라 보여드립니다.
            </p>

            <div id="purpose" class="purpose-panel">
                <div class="purpose-panel-title">
                    <b>용도별로 먼저 보기</b>
                    <span>어떤 용도로 쓸지 고르면 기본 조건을 채워드립니다.</span>
                </div>
                <div class="purpose-grid">
                    <a class="purpose-card" href="/?purpose=student&ram=16GB&ssd=512GB&max_price=700000&sort=recommend#results">
                        <b>대학생용</b><span>강의·과제·문서 작업</span>
                    </a>
                    <a class="purpose-card" href="/?purpose=office&keyword=ThinkPad&ram=16GB&ssd=512GB&max_price=700000&sort=recommend#results">
                        <b>사무용</b><span>문서 작업과 업무용</span>
                    </a>
                    <a class="purpose-card" href="/?purpose=portable&keyword=LG그램&ram=16GB&ssd=512GB&sort=price_asc#results">
                        <b>휴대용</b><span>가벼운 노트북 중심</span>
                    </a>
                    <a class="purpose-card" href="/?purpose=developer&ram=32GB&ssd=1TB&max_price=1000000&sort=value_desc#results">
                        <b>개발용</b><span>여유 있는 메모리·저장공간</span>
                    </a>
                    <a class="purpose-card" href="/?purpose=power&ram=32GB&ssd=1TB&cpu=i7&sort=value_desc#results">
                        <b>고성능</b><span>성능을 우선 볼 때</span>
                    </a>
                    <a class="purpose-card" href="/?purpose=budget&ram=16GB&ssd=512GB&max_price=500000&sort=value_desc#results">
                        <b>가성비</b><span>예산을 아끼고 싶을 때</span>
                    </a>
                </div>
            </div>

            <form class="hero-search-form" method="GET" action="/#results">
                <div class="hero-form-main">
                    <input type="text" name="keyword" value="{keyword_value}" placeholder="브랜드/모델명: 삼성, LG그램, ThinkPad, 맥북">
                    <input type="text" name="ram" value="{ram_value}" placeholder="RAM 예: 16GB">
                    <input type="text" name="ssd" value="{ssd_value}" placeholder="SSD 예: 512GB">
                    <input type="text" name="cpu" value="{cpu_value}" placeholder="CPU 예: i5, i7">
                    <input type="text" name="max_price" value="{price_value}" placeholder="최대 가격 예: 700000">
                </div>
                <button type="submit">조건에 맞는 후보 보기</button>
            </form>

            <div class="hero-quick-chips">
                <a href="/?keyword=삼성&ram=16GB&ssd=512GB#results">삼성 16GB·512GB</a>
                <a href="/?keyword=ThinkPad#results">ThinkPad</a>
                <a href="/?keyword=LG그램#results">LG그램</a>
                <a href="/?keyword=맥북#results">맥북</a>
                <a href="/?max_price=700000#results">70만원 이하</a>
            </div>
        </div>

        <div class="landing-right">
            <div class="signal-card primary-signal">
                <div class="signal-label">오늘 먼저 볼 만한 후보</div>
                <h3>{best_title}</h3>
                <div class="signal-metrics">
                    <span>{signal["best_price"]:,}원</span>
                    <span>{esc(signal["best_decision"])}</span>
                    <span>가성비 {signal["best_score"]:.1f}점</span>
                </div>
                {render_signal_link(signal.get("best_link", ""))}
            </div>

            <div class="signal-card">
                <div class="signal-label">최근 가격 흐름이 괜찮은 후보</div>
                <h3>{timing_title}</h3>
                <div class="signal-metrics">
                    <span>{signal["timing_price"]:,}원</span>
                    <span>구매 타이밍 {signal["timing_score"]:.1f}점</span>
                    <span>평균 대비 {esc(signal["timing_discount"])}%</span>
                </div>
                {render_signal_link(signal.get("timing_link", ""))}
            </div>

            <div class="signal-mini-grid">
                <div>
                    <b>{signal["stats"]["candidate_count"]:,}</b>
                    <span>실사용 후보</span>
                </div>
                <div>
                    <b>{signal["stats"]["model_group_count"]:,}</b>
                    <span>비교 그룹</span>
                </div>
                <div>
                    <b>{esc(latest_info["latest_update"])}</b>
                    <span>최근 갱신</span>
                </div>
            </div>
        </div>
    </section>

    <section class="recommendation-lab">
        <div class="section-heading-row">
            <div>
                <h2>예산별로 먼저 볼 만한 후보</h2>
                <p>예산대별로 하나씩 골라봤습니다. 오른쪽 버튼을 누르면 원하는 조건의 상품 목록으로 바로 이동합니다.</p>
            </div>
            <div class="quick-filter-panel">
                <a href="/?ram=16GB&ssd=512GB#results">16GB·512GB</a>
                <a href="/?ram=32GB&ssd=1TB#results">32GB·1TB</a>
                <a href="/?max_price=700000#results">70만원 이하</a>
                <a href="/?keyword=삼성#results">삼성</a>
                <a href="/?keyword=LG그램#results">LG그램</a>
                <a href="/?keyword=ThinkPad#results">ThinkPad</a>
                <a href="/?keyword=맥북#results">맥북</a>
            </div>
        </div>
        <div class="mini-pick-grid">
            {render_compact_product_pick(budget_50, "50만원 이하")}
            {render_compact_product_pick(budget_70, "50~70만원")}
            {render_compact_product_pick(budget_100, "70~100만원")}
        </div>
    </section>
    """


def render_purchase_checklist_section():
    return """
    <section class="purchase-checklist">
        <div>
            <h2>구매 전에 꼭 확인하세요</h2>
            <p>리퍼·중고 노트북은 가격만큼 상태가 중요합니다. 구매 전 아래 항목을 꼭 확인해 보세요.</p>
        </div>
        <div class="checklist-grid">
            <div>보증 기간</div>
            <div>배터리 상태</div>
            <div>외관 등급</div>
            <div>윈도우 포함 여부</div>
            <div>배송비</div>
            <div>반품 가능 여부</div>
        </div>
    </section>
    """


def render_project_summary_section():
    stats = get_project_stats()
    latest_info = get_latest_update_info()

    return f"""
    <section class="project-summary-box">
        <h2>현재 수집 현황</h2>
        <p class="summary-intro">
            네이버 쇼핑의 공개 상품 정보를 모아 가격과 사양을 정리했습니다.
            실사용 후보를 걸러내고, 비슷한 모델끼리 묶어 비교할 수 있게 했습니다.
        </p>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">누적 수집 기록</div>
                <div class="stat-number">{stats["raw_count"]:,}</div>
                <div class="stat-desc">지금까지 모은 가격 기록</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">수집 상품 ID</div>
                <div class="stat-number">{stats["unique_product_count"]:,}</div>
                <div class="stat-desc">네이버 상품 ID 기준</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">실사용 후보</div>
                <div class="stat-number">{stats["candidate_count"]:,}</div>
                <div class="stat-desc">RAM 16GB 이상 · SSD 512GB 이상</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">비교 그룹</div>
                <div class="stat-number">{stats["model_group_count"]:,}</div>
                <div class="stat-desc">비슷한 상품을 묶어 본 기준</div>
            </div>
        </div>

        <div class="decision-summary">
            <div class="decision-chip recommend-chip">구매 추천 <b>{stats["recommend_count"]:,}</b>개</div>
            <div class="decision-chip consider-chip">구매 고려 <b>{stats["consider_count"]:,}</b>개</div>
            <div class="decision-chip lack-chip">데이터 부족 <b>{stats["lack_count"]:,}</b>개</div>
            <div class="decision-chip hold-chip">보류 <b>{stats["hold_count"]:,}</b>개</div>
        </div>

        <p class="collection-period">
            수집 기간: {esc(stats["first_collected"])} ~ {esc(stats["last_collected"])}
        </p>

        <div class="update-status-box">
            <div class="update-status-item">
                <div class="update-status-label">최근 갱신</div>
                <div class="update-status-value">{esc(latest_info["latest_update"])}</div>
            </div>
            <div class="update-status-item">
                <div class="update-status-label">자동 갱신</div>
                <div class="update-status-value">{esc(latest_info["auto_update"])}</div>
            </div>
            <div class="update-status-item">
                <div class="update-status-label">표시 가격 기준</div>
                <div class="update-status-value">{esc(latest_info["data_basis"])}</div>
            </div>
        </div>

    </section>
    """

def render_price_history_section():
    rows = read_csv_rows("price_history_summary.csv")

    if not rows:
        return """
        <section id="top8" class="price-history-box">
            <h2>가격 이력 분석</h2>
            <p>아직 가격 이력 분석 파일이 없습니다. py analyze_price_history.py를 먼저 실행하세요.</p>
        </section>
        """

    best_rows = []
    used_display_keys = set()

    def make_display_key(row):
        title = fix_product_name(row.get("title", ""))
        title_key = normalize_text(title)

        remove_words = [
            "레노버", "LENOVO", "삼성전자", "삼성", "LG전자", "APPLE",
            "현대HMALL", "HMALL", "리퍼", "중고", "노트북",
            "윈도우11", "윈도우10", "WIN11", "WIN10",
            "사무용", "인강용", "가정용"
        ]

        for word in remove_words:
            title_key = title_key.replace(normalize_text(word), "")

        cpu = normalize_cpu(row.get("cpu", ""))
        ram = normalize_ram(row.get("ram", ""))
        ssd = normalize_ssd(row.get("ssd", ""))

        return f"{title_key[:45]}|{cpu}|{ram}|{ssd}"

    for row in rows:
        display_key = make_display_key(row)

        if display_key in used_display_keys:
            continue

        used_display_keys.add(display_key)
        best_rows.append(row)

        if len(best_rows) >= 8:
            break

    best_rows = best_rows[:8]

    cards = ""

    for index, row in enumerate(best_rows, start=1):
        title = esc(fix_product_name(row.get("title", "")))
        latest_price = safe_int(row.get("latest_price", 0))
        min_price = safe_int(row.get("min_price", 0))
        avg_price = safe_int(row.get("avg_price", 0))
        change_rate = esc(row.get("change_rate", ""))
        observed_count = esc(row.get("observed_count", ""))
        mall_count = esc(row.get("mall_count", ""))
        buy_timing_score = esc(row.get("buy_timing_score", ""))
        timing_signal = esc(row.get("timing_signal", ""))
        link = esc(row.get("link", ""))

        extra_class = " extra-price-card" if index > 4 else ""

        cards += f"""
        <div class="price-card{extra_class}">
            <div class="price-rank">{index}위</div>
            <div class="price-badge">🔥 {timing_signal}</div>
            <div class="timing-score">구매 타이밍 점수 <b>{buy_timing_score}</b>점</div>

            <h3>{title}</h3>

            <div class="price-info-grid">
                <div><b>현재가</b><br>{latest_price:,}원</div>
                <div><b>관측 최저가</b><br>{min_price:,}원</div>
                <div><b>평균가</b><br>{avg_price:,}원</div>
                <div><b>평균 대비</b><br>{change_rate}%</div>
                <div><b>관측 수</b><br>{observed_count}회</div>
                <div><b>판매처 수</b><br>{mall_count}곳</div>
            </div>

            <p class="price-comment">
                현재가가 평균보다 낮은지, 최근 최저가에 가까운지, 비교 데이터가 충분한지를 함께 본 점수입니다.
            </p>

            <a class="link-button" href="{link}" target="_blank">상품 페이지 보기</a>
        </div>
        """

    toggle_html = ""
    if len(best_rows) > 4:
        toggle_html = """
        <label class="top8-toggle-label" for="top8-toggle">
            <span class="show-more-text">8개 모두 보기</span>
            <span class="show-less-text">4개만 보기</span>
        </label>
        """

    return f"""
    <section id="top8" class="price-history-box">
        <div class="section-title-row">
            <div>
                <h2>가격 흐름이 좋은 후보 TOP 8</h2>
                <p class="summary-intro">
                    먼저 상위 4개만 보여드립니다. 더 보고 싶으면 전체 목록을 펼쳐 보세요.
                </p>
            </div>
            <div class="section-mini-badge">가격 이력 기준</div>
        </div>

        <input type="checkbox" id="top8-toggle" class="top8-toggle-input">

        <div class="price-card-list compact-top8">
            {cards}
        </div>

        {toggle_html}
    </section>
    """


def render_criteria_section():
    return """
    <section class="criteria-box">
        <h2>이렇게 판단합니다</h2>
        <p class="criteria-intro">
            가격이 싼지만 보지 않습니다.
            평균가와 최저가, 판매처 수, 기본 사양을 함께 보고 후보를 나눕니다.
        </p>

        <div class="criteria-grid service-criteria-grid">
            <div class="criteria-card">
                <h3>가격이 괜찮은가</h3>
                <p>현재 가격이 평균가보다 낮은지, 최근 최저가에 가까운지 봅니다.</p>
                <div class="factor-row">
                    <span>평균가와 비교</span>
                    <span>최근 최저가</span>
                    <span>가격 차이</span>
                </div>
            </div>

            <div class="criteria-card">
                <h3>사양이 충분한가</h3>
                <p>RAM, SSD, CPU 정보를 보고 기본 사용에 무리가 없는지 확인합니다.</p>
                <div class="factor-row">
                    <span>RAM</span>
                    <span>SSD</span>
                    <span>CPU</span>
                </div>
            </div>

            <div class="criteria-card">
                <h3>비교할 데이터가 충분한가</h3>
                <p>비슷한 모델의 판매처와 가격 기록이 많을수록 판단이 더 안정적입니다.</p>
                <div class="factor-row">
                    <span>관측 수</span>
                    <span>판매처 수</span>
                    <span>비슷한 모델</span>
                </div>
            </div>
        </div>

        <div class="simple-rule-box">
            <h3>결과는 네 가지로 나눕니다</h3>
            <div class="simple-rule-grid">
                <div><b>구매 추천</b><br>가격과 사양이 모두 괜찮은 편</div>
                <div><b>구매 고려</b><br>괜찮지만 상세 확인 필요</div>
                <div><b>데이터 부족</b><br>점수는 좋지만 비교 자료가 적음</div>
                <div><b>보류</b><br>지금은 매력이 크지 않음</div>
            </div>
        </div>

        <p class="criteria-note">
            ※ 리퍼·중고 상품은 상태, 보증, 배송비, 반품 조건에 따라 실제 가치가 달라집니다.
            최종 구매 전에는 반드시 상품 페이지를 직접 확인해 주세요.
        </p>
    </section>
    """



def render_learning_links_section():
    return """
    <section class="learning-links-box">
        <div class="section-heading-row">
            <div>
                <h2>처음 고르는 분을 위한 안내</h2>
                <p>
                    리퍼·중고 노트북은 가격만으로 판단하기 어렵습니다.
                    구매 전에 어떤 기준을 봐야 하는지 짧게 정리해 두었습니다.
                </p>
            </div>
        </div>

        <div class="learning-card-grid">
            <a class="learning-card" href="/guide">
                <span>GUIDE</span>
                <h3>리퍼 노트북 고르는 법</h3>
                <p>가격, 사양, 판매처, 보증 조건을 어떤 순서로 보면 좋은지 정리했습니다.</p>
            </a>

            <a class="learning-card" href="/checklist">
                <span>CHECKLIST</span>
                <h3>구매 전 체크리스트</h3>
                <p>배터리, 외관, 윈도우 포함 여부, 반품 조건 등 꼭 확인할 항목입니다.</p>
            </a>

            <a class="learning-card" href="/about">
                <span>ABOUT</span>
                <h3>리퍼 트래커의 판단 방식</h3>
                <p>평균가, 최저가, 관측 수, 판매처 수를 어떻게 참고하는지 설명합니다.</p>
            </a>
        </div>
    </section>
    """



def render_roadmap_section():
    return """
    
    <section id="notice" class="notice-box">
        <h2>이용 전 참고해 주세요</h2>
        <p>
            리퍼 트래커는 네이버 쇼핑의 공개 상품 정보를 바탕으로
            가격과 사양을 비교해 보는 참고용 도구입니다.
        </p>
        <div class="notice-grid">
            <div>
                <h3>표시 가격 기준</h3>
                <p>현재 표시되는 가격, 평균가, 최저가는 수집 시점의 표시 가격 기준입니다. 실제 판매 페이지의 가격과 조건은 달라질 수 있습니다.</p>
            </div>
            <div>
                <h3>판단 기준</h3>
                <p>구매 타이밍 점수는 평균 대비 할인율, 최근 최저가, 관측 수, 판매처 수 등을 종합해 계산한 참고 지표입니다.</p>
            </div>
            <div>
                <h3>마지막 확인</h3>
                <p>구매 전에는 판매처, 제품 상태, 보증, 배송비, 반품 조건을 꼭 확인해 주세요.</p>
            </div>
        </div>
    </section>

<section class="roadmap-box">
        <div class="future-title-row">
            <h2>앞으로 보완할 기능</h2>
            <p>
                지금은 CSV 기반으로 시작했지만, 데이터가 쌓일수록 가격 흐름을 더 안정적으로 볼 수 있습니다.
                앞으로는 관심 모델 저장, 가격 하락 알림 같은 기능도 붙일 수 있습니다.
            </p>
        </div>

        <div class="roadmap-grid">
            <div class="roadmap-card">
                <h3>1. 가격 기록 더 쌓기</h3>
                <p>기간이 길어질수록 평균가와 최저가 판단이 더 안정됩니다.</p>
            </div>

            <div class="roadmap-card">
                <h3>2. 대용량 가격 이력 분석</h3>
                <p>가격 기록이 많아지면 더 빠르게 조회하고 비교할 수 있는 구조로 확장할 수 있습니다.</p>
            </div>

            <div class="roadmap-card">
                <h3>3. 관심 모델 가격 알림</h3>
                <p>관심 모델이 평균가보다 낮아지거나 최근 최저가에 가까워졌을 때 알려주는 기능을 붙일 수 있습니다.</p>
            </div>

            <div class="roadmap-card">
                <h3>4. 사양 판단 더 정교하게</h3>
                <p>CPU 세대, 무게, 화면 크기, 보증 기간, 리퍼 등급 같은 요소도 반영할 수 있습니다.</p>
            </div>

            <div class="roadmap-card">
                <h3>5. 내 조건 저장</h3>
                <p>자주 찾는 조건을 저장해 두고 다음에 바로 다시 볼 수 있게 할 수 있습니다.</p>
            </div>
        </div>

        <div class="future-message">
            💙 데이터가 쌓일수록 더 쓸 만한 리퍼 노트북 비교 도구로 다듬어가겠습니다.
        </div>
    </section>
    """


def render_user_guide_section():
    return """
    <section class="guide-box">
        <div class="guide-header">
            <div>
                <h2>이렇게 써보세요</h2>
                <p>
                    원하는 브랜드나 모델명, RAM, SSD, 예산을 입력하면
                    현재 수집 표시 가격 기준으로 구매 후보를 비교해 줍니다.
                </p>
            </div>
            <div class="guide-badge">처음 쓰는 분을 위한 안내</div>
        </div>

        <div class="guide-grid">
            <div class="guide-card">
                <div class="guide-step">1</div>
                <h3>브랜드나 모델 입력</h3>
                <p>삼성, LG그램, ThinkPad, 맥북처럼 찾고 싶은 키워드를 넣습니다.</p>
            </div>
            <div class="guide-card">
                <div class="guide-step">2</div>
                <h3>원하는 사양 입력</h3>
                <p>일반적인 사용이라면 RAM 16GB, SSD 512GB 이상부터 보는 편이 좋습니다.</p>
            </div>
            <div class="guide-card">
                <div class="guide-step">3</div>
                <h3>가격과 비교 기준 확인</h3>
                <p>현재가, 평균가, 최저가, 판매처 수를 함께 봅니다.</p>
            </div>
            <div class="guide-card">
                <div class="guide-step">4</div>
                <h3>상품 페이지 확인</h3>
                <p>마지막으로 제품 상태, 보증, 배송비, 반품 조건을 확인합니다.</p>
            </div>
        </div>
    </section>
    """

def render_search_section(keyword_value, ram_value, ssd_value, cpu_value, price_value):
    examples = [
        ("삼성 16GB 512GB", "/?keyword=삼성&ram=16GB&ssd=512GB"),
        ("LG그램 16GB 512GB", "/?keyword=LG그램&ram=16GB&ssd=512GB"),
        ("ThinkPad 16GB 512GB", "/?keyword=ThinkPad&ram=16GB&ssd=512GB"),
        ("맥북 16GB 512GB", "/?keyword=맥북&ram=16GB&ssd=512GB"),
    ]

    example_links = "".join(
        f'<a class="example-chip" href="{url}">{esc(label)}</a>'
        for label, url in examples
    )

    return f"""
    <section class="search-box">
        <div class="search-title-row">
            <div>
                <h2>직접 조건 입력</h2>
                <p>찾고 싶은 브랜드나 모델, 필요한 사양을 직접 넣어보세요.</p>
            </div>
        </div>

        <div class="example-searches">
            <span>빠른 예시</span>
            {example_links}
        </div>

        <form method="GET" action="/#results">
            <div class="form-grid compact-form-grid">
                <div>
                    <label>키워드</label>
                    <input type="text" name="keyword" value="{keyword_value}" placeholder="예: ThinkPad, 맥북, LG그램, 삼성">
                </div>

                <div>
                    <label>RAM</label>
                    <input type="text" name="ram" value="{ram_value}" placeholder="예: 16, 16GB, 32">
                </div>

                <div>
                    <label>SSD</label>
                    <input type="text" name="ssd" value="{ssd_value}" placeholder="예: 512, 512GB, 1TB">
                </div>

                <div>
                    <label>CPU</label>
                    <input type="text" name="cpu" value="{cpu_value}" placeholder="예: i5, i7, Ryzen 5">
                </div>

                <div>
                    <label>최대 가격</label>
                    <input type="text" name="max_price" value="{price_value}" placeholder="예: 700000">
                </div>
            </div>

            <button type="submit">검색하기</button>
        </form>
    </section>
    """



def make_product_strengths(product):
    strengths = []

    price = safe_int(product.get("price", 0))
    value_score = safe_float(product.get("value_score", 0))
    mall_count = safe_int(product.get("mall_count", 0))
    seller_count = safe_int(product.get("seller_count", 0))
    price_gap = safe_int(product.get("price_gap_in_group", 0))
    ram = normalize_ram(product.get("ram", ""))
    ssd = normalize_ssd(product.get("ssd", ""))
    cpu = normalize_cpu(product.get("cpu", ""))
    decision = product.get("buy_decision", "")

    if price and price <= 500000:
        strengths.append("50만원 이하 예산에서 검토 가능한 후보입니다.")
    elif price and price <= 700000:
        strengths.append("70만원 이하 예산에서 실사용 후보로 볼 수 있습니다.")

    if ram in ["16GB", "24GB", "32GB", "64GB"] and ssd in ["512GB", "1TB", "2TB"]:
        strengths.append(f"RAM {ram}, SSD {ssd}로 기본 실사용 사양을 충족합니다.")
    elif ram:
        strengths.append(f"RAM {ram} 정보가 확인됩니다.")

    if cpu in ["i7", "i9", "Ryzen 7", "Apple M2", "Apple M3", "Apple M4"]:
        strengths.append(f"CPU {cpu} 기준으로 성능 여유가 있는 편입니다.")
    elif cpu in ["i5", "Ryzen 5", "Apple M1"]:
        strengths.append(f"CPU {cpu} 기준으로 일반 작업에 무난한 편입니다.")

    comparison_count = max(mall_count, seller_count)
    if comparison_count >= 4:
        strengths.append(f"비슷한 모델 {comparison_count}개와 비교되어 가격 판단이 더 안정적입니다.")
    elif comparison_count >= 2:
        strengths.append(f"비슷한 모델 {comparison_count}개 기준으로 비교가 가능합니다.")

    if value_score >= 280:
        strengths.append("가성비 점수가 높아 우선 검토할 만합니다.")
    elif value_score >= 240:
        strengths.append("가성비 점수가 나쁘지 않아 비교 후보로 볼 수 있습니다.")

    if price_gap >= 100000:
        strengths.append("판매처마다 가격 차이가 커서 최저가 확인 가치가 있습니다.")

    if decision == "구매 추천":
        strengths.append("현재 기준에서는 구매 추천으로 분류된 후보입니다.")

    # 중복 제거 + 최대 4개
    unique = []
    for item in strengths:
        if item not in unique:
            unique.append(item)

    return unique[:4]


def make_product_cautions(product):
    cautions = []

    mall_count = safe_int(product.get("mall_count", 0))
    seller_count = safe_int(product.get("seller_count", 0))
    price_gap = safe_int(product.get("price_gap_in_group", 0))
    ram = product.get("ram", "")
    ssd = product.get("ssd", "")
    cpu = product.get("cpu", "")
    decision = product.get("buy_decision", "")
    title = product.get("title", "")

    comparison_count = max(mall_count, seller_count)

    if comparison_count <= 1:
        cautions.append("비교 가능한 판매처가 적어 실제 상품 페이지 확인이 중요합니다.")

    if not cpu:
        cautions.append("CPU 정보가 명확하지 않아 상세 페이지에서 정확한 모델을 확인해야 합니다.")

    if not ram or not ssd:
        cautions.append("RAM 또는 SSD 정보가 부족해 상세 사양 확인이 필요합니다.")

    if price_gap >= 150000:
        cautions.append("판매처마다 가격 차이가 커서 제품 상태, 보증, 구성품 차이를 비교해야 합니다.")

    if any(word in title for word in ["액정", "파손", "부품", "고장", "베어본"]):
        cautions.append("제목상 상태 확인이 필요한 표현이 포함되어 있습니다.")

    if decision in ["보류", "데이터 부족"]:
        cautions.append("현재 판단은 신중 검토 대상이므로 구매 전 조건 확인이 필요합니다.")

    # 모든 리퍼/중고 공통 주의
    cautions.append("리퍼·중고 상품은 배터리 상태, 외관 등급, 보증 기간, 반품 조건을 확인해야 합니다.")

    unique = []
    for item in cautions:
        if item not in unique:
            unique.append(item)

    return unique[:4]


def render_product_pros_cons(product):
    strengths = make_product_strengths(product)
    cautions = make_product_cautions(product)

    strengths_html = "".join(f"<li>{esc(item)}</li>" for item in strengths) or "<li>추가 장점은 상품 상세 페이지에서 확인하세요.</li>"
    cautions_html = "".join(f"<li>{esc(item)}</li>" for item in cautions) or "<li>구매 전 상세 페이지 확인이 필요합니다.</li>"

    return f"""
    <div class="pros-cons-grid">
        <div class="pros-box">
            <h4>장점</h4>
            <ul>{strengths_html}</ul>
        </div>
        <div class="cautions-box">
            <h4>주의</h4>
            <ul>{cautions_html}</ul>
        </div>
    </div>
    """


def render_purpose_context(result):
    purpose = result.get("purpose", "")
    if not purpose or purpose not in PURPOSE_PRESETS:
        return ""

    preset = PURPOSE_PRESETS[purpose]
    label = esc(preset.get("label", "용도별"))
    desc = esc(preset.get("desc", ""))

    keyword = esc(result.get("keyword", "") or "전체")
    ram = esc(result.get("ram", "") or "전체")
    ssd = esc(result.get("ssd", "") or "전체")
    cpu = esc(result.get("cpu", "") or "전체")

    max_price = result.get("max_price")
    max_price_text = "제한 없음" if max_price is None else f"{max_price:,}원"

    return f"""
    <div class="purpose-context-box">
        <div>
            <span class="purpose-context-label">이 조건으로 찾았습니다</span>
            <h3>{label}</h3>
            <p>{desc}</p>
        </div>
        <div class="purpose-context-grid">
            <div><b>키워드</b><br>{keyword}</div>
            <div><b>RAM</b><br>{ram}</div>
            <div><b>SSD</b><br>{ssd}</div>
            <div><b>CPU</b><br>{cpu}</div>
            <div><b>예산</b><br>{max_price_text}</div>
        </div>
    </div>
    """


def render_sticky_nav():
    return """
    <nav class="sticky-nav" aria-label="빠른 이동 메뉴">
        <a href="#home">처음</a>
        <a href="#purpose">용도별</a>
        <a href="#results">검색 결과</a>
        <a href="#top8">TOP 8</a>
        <a href="#notice">안내</a>
    </nav>
    """

def render_main_dashboard(keyword_value, ram_value, ssd_value, cpu_value, price_value):
    return f"""
    <section class="dashboard-layout">
        <div class="dashboard-left">
            {render_project_summary_section()}
            {render_criteria_section()}
        </div>

        <aside class="dashboard-right">
            {render_price_history_section()}
        </aside>
    </section>
    {render_purchase_checklist_section()}
    """


def render_product_cards(products):
    if not products:
        return """
        <div class='empty'>
            <b>조건에 맞는 상품을 찾지 못했습니다.</b><br>
            키워드를 넓게 잡거나 CPU, 가격 조건을 비워서 다시 찾아보세요.
        </div>
        """

    cards = ""

    for index, product in enumerate(products[:10], start=1):
        title = esc(fix_product_name(product.get("title", "")))
        model_key = esc(product.get("model_key", ""))
        mall = esc(product.get("mall", ""))
        brand = esc(product.get("brand", ""))
        ram = esc(product.get("ram", ""))
        ssd = esc(product.get("ssd", ""))
        cpu = esc(product.get("cpu", ""))
        decision = esc(product.get("buy_decision", ""))
        reason = esc(product.get("decision_reason", ""))
        link = esc(product.get("link", ""))
        value_score = esc(product.get("value_score", ""))
        seller_count = esc(product.get("seller_count", ""))
        mall_count = esc(product.get("mall_count", ""))

        price_gap = safe_int(product.get("price_gap_in_group", 0))
        price = safe_int(product.get("price", 0))

        decision_class = get_decision_class(product.get("buy_decision", ""))
        summary_sentence = esc(make_summary_sentence(product))
        confidence_label, confidence_desc = get_confidence_label(product)
        confidence_class = "confidence-high" if confidence_label == "높음" else "confidence-mid" if confidence_label == "보통" else "confidence-low"

        points = make_recommendation_points(product)
        points_html = "".join(f"<li>{esc(point)}</li>" for point in points)

        cards += f"""
        <div class="card">
            <div class="card-topline">
                <div class="rank">{index}위</div>
                <div class="decision {decision_class}">{decision}</div>
            </div>

            <h3>{title}</h3>

            <p class="summary-sentence">{summary_sentence}</p>

            <div class="confidence-box {confidence_class}">
                <b>비교 신뢰도: {confidence_label}</b>
                <span>{esc(confidence_desc)}</span>
            </div>

            {render_product_pros_cons(product)}

            <div class="recommendation-points">
                <h4>왜 이렇게 봤나요?</h4>
                <ul>{points_html}</ul>
            </div>

            <p class="reason">{reason}</p>

            <div class="info-grid">
                <div><b>가격</b><br>{price:,}원</div>
                <div><b>판매처</b><br>{mall}</div>
                <div><b>브랜드</b><br>{brand}</div>
                <div><b>RAM</b><br>{ram}</div>
                <div><b>SSD</b><br>{ssd}</div>
                <div><b>CPU</b><br>{cpu if cpu else "미확인"}</div>
                <div><b>가성비 점수</b><br>{value_score}</div>
                <div><b>비슷한 모델</b><br>{seller_count}개</div>
                <div><b>판매처 수</b><br>{mall_count}개</div>
                <div><b>가격 차이</b><br>{price_gap:,}원</div>
            </div>

            <p class="model-key"><b>비교 기준:</b> {model_key}</p>
            <a class="link-button" href="{link}" target="_blank">상품 페이지 보기</a>
        </div>
        """

    return cards


def render_page(result=None):
    keyword_value = ""
    ram_value = ""
    ssd_value = ""
    cpu_value = ""
    price_value = ""

    result_html = ""

    if result:
        keyword_value = esc(result.get("keyword", ""))
        ram_value = esc(result.get("ram", ""))
        ssd_value = esc(result.get("ssd", ""))
        cpu_value = esc(result.get("cpu", ""))

        max_price = result.get("max_price")
        max_price_display = "제한 없음"

        if max_price is not None:
            price_value = str(max_price)
            max_price_display = f"{max_price:,}원"

        products = result.get("products", [])
        search_type = esc(result.get("search_type", ""))
        purpose_display = esc(get_purpose_label(result.get("purpose", "")))
        sort_display = esc(get_sort_label(result.get("sort", "recommend")))

        result_html = f"""
        <section class="summary">
            <h2>적용된 조건</h2>
            <div class="condition-grid">
                <div><b>키워드</b><br>{keyword_value if keyword_value else "전체"}</div>
                <div><b>RAM</b><br>{ram_value if ram_value else "전체"}</div>
                <div><b>SSD</b><br>{ssd_value if ssd_value else "전체"}</div>
                <div><b>CPU</b><br>{cpu_value if cpu_value else "전체"}</div>
                <div><b>최대 가격</b><br>{max_price_display}</div>
                <div><b>용도</b><br>{purpose_display}</div>
                <div><b>정렬</b><br>{sort_display}</div>
            </div>
        </section>

        <section id="results" class="results">
            <h2>{search_type}</h2>
            <p class="count">상품 수: {len(products)}개</p>
            {render_purpose_context(result)}
            {render_sort_controls(result)}
            {render_product_cards(products)}
        </section>
        """

    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="리퍼·중고 노트북 가격과 사양을 비교하고, 평균가·최저가·판매처 수를 바탕으로 먼저 볼 만한 후보를 찾아보는 서비스입니다.">
    <title>리퍼 트래커 | Refurb Laptop Tracker</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f5f6fa;
            margin: 0;
            padding: 0;
            color: #222;
        }}

        header {{
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #2563eb 100%);
            color: white;
            padding: 48px 56px 54px;
            border-bottom: 1px solid rgba(255,255,255,0.15);
        }}

        .header-inner {{
            max-width: 1100px;
            margin: 0 auto;
        }}

        .logo-line {{
            display: inline-block;
            padding: 7px 13px;
            margin-bottom: 18px;
            border-radius: 999px;
            background: rgba(255,255,255,0.14);
            color: #dbeafe;
            font-size: 14px;
            font-weight: bold;
        }}

        .main-title {{
            margin: 0;
            font-size: 52px;
            line-height: 1.05;
            font-weight: 900;
            letter-spacing: -1.5px;
        }}

        .sub-title-en {{
            margin-top: 10px;
            font-size: 28px;
            font-weight: 800;
            color: #bfdbfe;
        }}

        .desc-box {{
            margin-top: 26px;
            padding: 18px 22px;
            border-left: 5px solid #93c5fd;
            background: rgba(15, 23, 42, 0.32);
            border-radius: 12px;
            max-width: 860px;
        }}

        .desc-ko-title {{
            font-size: 18px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 7px;
        }}

        .desc-ko-text {{
            font-size: 15px;
            color: #dbeafe;
            line-height: 1.6;
        }}

        main {{
            max-width: 1500px;
            margin: 30px auto;
            padding: 0 24px;
        }}

        .dashboard-layout {{
            display: grid;
            grid-template-columns: minmax(520px, 0.9fr) minmax(720px, 1.1fr);
            gap: 24px;
            align-items: stretch;
            margin-bottom: 12px;
        }}

        .dashboard-left,
        .dashboard-right {{
            min-width: 0;
            display: flex;
            flex-direction: column;
        }}

        .dashboard-left > section:last-child {{
            margin-bottom: 0;
        }}

        .dashboard-left .criteria-box {{
            flex: 1;
            margin-bottom: 0;
        }}

        .dashboard-right .price-history-box {{
            flex: 1;
            margin-bottom: 0;
        }}

        .dashboard-right {{
            position: static;
        }}

        .project-summary-box,
        .criteria-box,
        .search-box,
        .summary,
        .results,
        .roadmap-box,
        .price-history-box {{
            background: white;
            padding: 24px;
            border-radius: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            margin-bottom: 18px;
        }}

        .summary-intro,
        .criteria-intro {{
            color: #4b5563;
            line-height: 1.6;
            margin-bottom: 18px;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 14px;
        }}

        .stat-card {{
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 18px;
        }}

        .stat-label {{
            color: #4b5563;
            font-size: 14px;
            font-weight: bold;
        }}

        .stat-number {{
            margin-top: 8px;
            font-size: 30px;
            font-weight: 900;
            color: #1d4ed8;
        }}

        .stat-desc {{
            margin-top: 6px;
            color: #6b7280;
            font-size: 13px;
        }}

        .decision-summary {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 18px;
        }}

        .decision-chip {{
            padding: 10px 14px;
            border-radius: 999px;
            font-size: 14px;
            font-weight: bold;
        }}

        .recommend-chip {{
            background: #dcfce7;
            color: #166534;
        }}

        .consider-chip {{
            background: #dbeafe;
            color: #1d4ed8;
        }}

        .lack-chip {{
            background: #fef3c7;
            color: #92400e;
        }}

        .hold-chip {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .collection-period {{
            margin-top: 14px;
            color: #6b7280;
            font-size: 14px;
        }}

        .criteria-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 16px;
        }}

        .roadmap-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 14px;
        }}

        .roadmap-box {{
            background: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%);
            border: 1px solid #dbeafe;
        }}

        .future-title-row h2 {{
            margin-bottom: 8px;
        }}

        .future-title-row p {{
            color: #4b5563;
            line-height: 1.6;
            margin-top: 0;
            margin-bottom: 18px;
        }}

        .roadmap-card {{
            padding: 16px;
        }}

        .roadmap-card h3 {{
            margin-bottom: 8px;
        }}

        .roadmap-card p {{
            margin: 0;
            font-size: 14px;
            line-height: 1.55;
        }}

        .future-message {{
            margin-top: 18px;
            padding: 13px 16px;
            text-align: center;
            border-radius: 999px;
            background: #dbeafe;
            color: #1d4ed8;
            font-weight: bold;
        }}

        .criteria-card,
        .roadmap-card {{
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 18px;
        }}

        .criteria-card h3,
        .roadmap-card h3 {{
            margin-top: 0;
            color: #1d4ed8;
            font-size: 18px;
        }}

        .criteria-card p,
        .roadmap-card p {{
            color: #374151;
            line-height: 1.5;
        }}

        .criteria-card ul {{
            padding-left: 18px;
            line-height: 1.7;
            color: #374151;
        }}

        .formula {{
            margin-top: 12px;
            background: #eff6ff;
            color: #1e3a8a;
            padding: 10px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 14px;
            line-height: 1.5;
        }}

        .score-table {{
            margin-top: 12px;
            background: #f3f4f6;
            padding: 10px;
            border-radius: 8px;
            font-size: 14px;
            line-height: 1.6;
            color: #374151;
        }}

        .criteria-note {{
            margin-top: 16px;
            padding: 14px;
            background: #fff7ed;
            color: #9a3412;
            border-radius: 10px;
            font-size: 14px;
            line-height: 1.6;
        }}

        .form-grid,
        .condition-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 14px;
        }}

        .compact-form-grid {{
            grid-template-columns: repeat(2, 1fr);
        }}

        .compact-form-grid div:first-child {{
            grid-column: 1 / -1;
        }}

        label {{
            font-weight: bold;
            font-size: 14px;
        }}

        input {{
            width: 100%;
            box-sizing: border-box;
            margin-top: 6px;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 8px;
            font-size: 14px;
        }}

        button {{
            margin-top: 20px;
            padding: 12px 20px;
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
        }}

        button:hover {{
            background: #1d4ed8;
        }}

        .condition-grid div {{
            background: #f3f4f6;
            padding: 12px;
            border-radius: 10px;
        }}

        .count {{
            color: #555;
        }}

        .card {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 22px;
            margin: 18px 0;
        }}

        .rank {{
            font-weight: bold;
            color: #2563eb;
            margin-bottom: 8px;
        }}

        .decision {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .recommend {{
            background: #dcfce7;
            color: #166534;
        }}

        .consider {{
            background: #dbeafe;
            color: #1d4ed8;
        }}

        .lack {{
            background: #fef3c7;
            color: #92400e;
        }}

        .hold {{
            background: #fee2e2;
            color: #991b1b;
        }}

        h3 {{
            margin-top: 8px;
            margin-bottom: 10px;
        }}

        .summary-sentence {{
            background: #eff6ff;
            padding: 12px;
            border-left: 4px solid #1d4ed8;
            border-radius: 6px;
            color: #1e3a8a;
            font-weight: bold;
            line-height: 1.6;
        }}

        .reason {{
            background: #f9fafb;
            padding: 12px;
            border-left: 4px solid #2563eb;
            border-radius: 6px;
            color: #374151;
        }}

        .info-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin-top: 16px;
        }}

        .info-grid div {{
            background: #f3f4f6;
            padding: 10px;
            border-radius: 8px;
            font-size: 14px;
        }}

        .model-key {{
            color: #555;
            font-size: 14px;
            margin-top: 16px;
        }}

        .link-button {{
            display: inline-block;
            margin-top: 12px;
            padding: 10px 14px;
            background: #111827;
            color: white;
            text-decoration: none;
            border-radius: 8px;
        }}

        .empty {{
            padding: 20px;
            background: #fef2f2;
            border-radius: 10px;
            color: #991b1b;
        }}

        .price-history-box {{
            background: white;
            padding: 24px;
            border-radius: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            margin-bottom: 24px;
        }}

        .price-card-list {{
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 16px;
        }}

        .price-card {{
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 16px;
            background: #ffffff;
        }}

        .price-card h3 {{
            font-size: 15px;
            line-height: 1.45;
        }}

        .price-rank {{
            color: #2563eb;
            font-weight: bold;
            margin-bottom: 8px;
        }}

        .price-badge {{
            display: inline-block;
            background: #fee2e2;
            color: #991b1b;
            padding: 6px 12px;
            border-radius: 999px;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .timing-score {{
            margin: 8px 0 12px;
            padding: 10px 12px;
            border-radius: 10px;
            background: #eff6ff;
            color: #1d4ed8;
            font-weight: 700;
        }}

        .timing-score b {{
            font-size: 22px;
        }}

        .price-info-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-top: 14px;
        }}

        .price-info-grid div {{
            background: #f3f4f6;
            padding: 10px;
            border-radius: 8px;
            font-size: 13px;
        }}

        .price-comment {{
            background: #fff7ed;
            color: #9a3412;
            padding: 10px;
            border-radius: 8px;
            margin-top: 14px;
            line-height: 1.5;
        }}

        @media (max-width: 1200px) {{
            main {{
                max-width: 1100px;
            }}

            .dashboard-layout {{
                grid-template-columns: 1fr;
            }}

            .price-card-list {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .roadmap-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 900px) {{
            header {{
                padding: 36px 24px 42px;
            }}

            .main-title {{
                font-size: 40px;
            }}

            .sub-title-en {{
                font-size: 22px;
            }}

            .dashboard-layout,
            .stats-grid,
            .criteria-grid,
            .form-grid,
            .compact-form-grid,
            .condition-grid,
            .info-grid,
            .roadmap-grid,
            .mini-status-grid,
            .price-card-list,
            .price-info-grid {{
                grid-template-columns: 1fr;
            }}

            .compact-form-grid div:first-child {{
                grid-column: auto;
            }}

            .dashboard-right {{
                position: static;
            }}

            .dashboard-left .criteria-box {{
                flex: none;
            }}
        }}

        @media (max-width: 700px) {{
            header {{
                padding: 32px 20px 36px;
            }}

            .header-inner {{
                max-width: 100%;
            }}

            .logo-line {{
                font-size: 12px;
                padding: 6px 11px;
            }}

            .main-title {{
                font-size: 38px;
                letter-spacing: -1px;
            }}

            .sub-title-en {{
                font-size: 22px;
            }}

            .desc-box {{
                margin-top: 20px;
                padding: 16px 18px;
            }}

            main {{
                margin: 18px auto;
                padding: 0 12px;
            }}

            .project-summary-box,
            .criteria-box,
            .search-box,
            .summary,
            .results,
            .roadmap-box,
            .price-history-box {{
                padding: 18px;
                border-radius: 14px;
            }}

            .stats-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 10px;
            }}

            .stat-card {{
                padding: 14px;
            }}

            .stat-number {{
                font-size: 24px;
            }}

            .decision-summary {{
                gap: 8px;
            }}

            .decision-chip {{
                font-size: 12px;
                padding: 8px 10px;
            }}

            .form-grid,
            .compact-form-grid {{
                grid-template-columns: 1fr;
                gap: 12px;
            }}

            .compact-form-grid div:first-child {{
                grid-column: auto;
            }}

            input {{
                font-size: 16px;
                padding: 12px;
            }}

            button {{
                width: 100%;
                padding: 13px 18px;
            }}

            .price-card-list {{
                grid-template-columns: 1fr;
            }}

            .price-card {{
                padding: 16px;
            }}

            .price-info-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .info-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .condition-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .card {{
                padding: 18px;
            }}

            .card h3,
            .price-card h3 {{
                font-size: 17px;
                line-height: 1.45;
            }}

            .summary-sentence,
            .reason,
            .price-comment {{
                font-size: 14px;
            }}

            .roadmap-grid {{
                grid-template-columns: 1fr;
            }}

            .future-message {{
                border-radius: 14px;
                line-height: 1.5;
            }}

            .service-landing,
            .purchase-checklist {{
                grid-template-columns: 1fr;
            }}

            .landing-left,
            .landing-right,
            .recommendation-lab,
            .purchase-checklist {{
                padding: 18px;
                border-radius: 16px;
            }}

            .landing-left h2 {{
                font-size: 28px;
            }}

            .hero-form-main {{
                grid-template-columns: 1fr;
            }}

            .hero-quick-chips a,
            .soft-link-button {{
                width: 100%;
                box-sizing: border-box;
                text-align: center;
            }}

            .signal-mini-grid,
            .mini-pick-grid,
            .checklist-grid {{
                grid-template-columns: 1fr;
            }}

            .section-heading-row {{
                flex-direction: column;
            }}

            .purpose-panel-title,
            .result-toolbar {{
                flex-direction: column;
            }}

            .purpose-grid {{
                grid-template-columns: 1fr;
            }}

            .sort-links {{
                justify-content: flex-start;
                width: 100%;
            }}

            .sort-links a {{
                flex: 1 1 auto;
                text-align: center;
            }}

            .sticky-nav {{
                overflow-x: auto;
                justify-content: flex-start;
                -webkit-overflow-scrolling: touch;
            }}

            .sticky-nav a {{
                flex: 0 0 auto;
            }}

            .section-title-row,
            .purpose-context-box {{
                grid-template-columns: 1fr;
                flex-direction: column;
            }}

            .purpose-context-grid {{
                grid-template-columns: 1fr 1fr;
            }}

            .pros-cons-grid {{
                grid-template-columns: 1fr;
            }}

            .learning-card-grid {{
                grid-template-columns: 1fr;
            }}

            .learning-links-box {{
                padding: 18px;
                border-radius: 14px;
            }}

            .section-mini-badge {{
                white-space: normal;
                width: fit-content;
            }}

            .quick-filter-panel {{
                width: 100%;
                justify-content: flex-start;
                max-width: none;
            }}

            .quick-filter-panel a {{
                width: 100%;
                box-sizing: border-box;
                text-align: center;
            }}


            .guide-header {{
                flex-direction: column;
            }}

            .guide-badge {{
                white-space: normal;
            }}

            .guide-grid,
            .simple-rule-grid {{
                grid-template-columns: 1fr;
            }}

            .example-searches {{
                align-items: flex-start;
            }}

            .example-chip {{
                width: 100%;
                box-sizing: border-box;
                text-align: center;
            }}

            .confidence-box {{
                font-size: 14px;
            }}



            .update-status-box {{
                grid-template-columns: 1fr;
                padding: 14px;
            }}

            .update-status-item {{
                padding: 12px;
            }}

            .notice-box {{
                padding: 18px;
                border-radius: 14px;
            }}

            .notice-grid {{
                grid-template-columns: 1fr;
            }}

            .notice-box h2 {{
                font-size: 24px;
            }}

        }}


        .notice-box {{
            background: #ffffff;
            border-radius: 20px;
            padding: 32px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            margin-bottom: 28px;
        }}

        .notice-box h2 {{
            font-size: 26px;
            margin-bottom: 12px;
        }}

        .notice-box > p {{
            color: #475569;
            line-height: 1.8;
            margin-bottom: 20px;
        }}

        .notice-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
        }}

        .notice-grid div {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 18px;
        }}

        .notice-grid h3 {{
            color: #2563eb;
            margin-bottom: 8px;
            font-size: 18px;
        }}

        .notice-grid p {{
            color: #475569;
            line-height: 1.7;
            font-size: 14px;
        }}


        .update-status-box {{
            background: linear-gradient(135deg, #eff6ff, #f8fafc);
            border: 1px solid #dbeafe;
            border-radius: 16px;
            padding: 18px 20px;
            margin-top: 18px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
        }}

        .update-status-item {{
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 14px;
        }}

        .update-status-label {{
            font-size: 13px;
            font-weight: 800;
            color: #2563eb;
            margin-bottom: 6px;
        }}

        .update-status-value {{
            color: #334155;
            font-size: 14px;
            line-height: 1.5;
            word-break: keep-all;
        }}


        .guide-box {{
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            padding: 24px;
            border-radius: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            margin-bottom: 18px;
            border: 1px solid #e5e7eb;
        }}

        .guide-header {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
            margin-bottom: 18px;
        }}

        .guide-header h2 {{
            margin: 0 0 8px;
        }}

        .guide-header p {{
            margin: 0;
            color: #4b5563;
            line-height: 1.6;
        }}

        .guide-badge {{
            white-space: nowrap;
            background: #dbeafe;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 8px 12px;
            font-weight: 800;
            font-size: 13px;
        }}

        .guide-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }}

        .guide-card {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 16px;
        }}

        .guide-step {{
            width: 30px;
            height: 30px;
            border-radius: 999px;
            background: #2563eb;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            margin-bottom: 10px;
        }}

        .guide-card h3 {{
            color: #1e3a8a;
            margin: 0 0 8px;
            font-size: 16px;
        }}

        .guide-card p {{
            color: #4b5563;
            line-height: 1.55;
            font-size: 14px;
            margin: 0;
        }}

        .search-title-row p {{
            color: #4b5563;
            margin-top: 6px;
            line-height: 1.5;
        }}

        .example-searches {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            margin: 12px 0 16px;
        }}

        .example-searches span {{
            color: #475569;
            font-size: 14px;
            font-weight: 800;
            margin-right: 4px;
        }}

        .example-chip {{
            display: inline-block;
            text-decoration: none;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 8px 12px;
            font-size: 13px;
            font-weight: 800;
        }}

        .example-chip:hover {{
            background: #dbeafe;
        }}

        .factor-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }}

        .factor-row span {{
            background: #eff6ff;
            color: #1d4ed8;
            padding: 7px 9px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 800;
        }}

        .simple-rule-box {{
            margin-top: 16px;
            padding: 18px;
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
        }}

        .simple-rule-box h3 {{
            margin-top: 0;
            color: #111827;
        }}

        .simple-rule-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
        }}

        .simple-rule-grid div {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 12px;
            color: #4b5563;
            line-height: 1.5;
            font-size: 14px;
        }}

        .simple-rule-grid b {{
            color: #1d4ed8;
        }}

        .card-topline {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .confidence-box {{
            margin: 12px 0;
            padding: 12px;
            border-radius: 10px;
            display: flex;
            flex-direction: column;
            gap: 4px;
            line-height: 1.5;
        }}

        .confidence-box span {{
            color: #475569;
            font-size: 14px;
        }}

        .confidence-high {{
            background: #ecfdf5;
            color: #166534;
            border: 1px solid #bbf7d0;
        }}

        .confidence-mid {{
            background: #eff6ff;
            color: #1d4ed8;
            border: 1px solid #bfdbfe;
        }}

        .confidence-low {{
            background: #fff7ed;
            color: #9a3412;
            border: 1px solid #fed7aa;
        }}

        .recommendation-points {{
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            padding: 12px 14px;
            margin: 12px 0;
        }}

        .recommendation-points h4 {{
            margin: 0 0 8px;
            color: #111827;
        }}

        .recommendation-points ul {{
            margin: 0;
            padding-left: 18px;
            color: #374151;
            line-height: 1.65;
        }}


        .service-landing {{
            display: grid;
            grid-template-columns: minmax(0, 1.12fr) minmax(380px, 0.88fr);
            gap: 24px;
            margin-bottom: 24px;
            align-items: stretch;
        }}

        .landing-left,
        .landing-right,
        .recommendation-lab,
        .purchase-checklist {{
            background: #ffffff;
            border-radius: 22px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
            border: 1px solid #e5e7eb;
        }}

        .landing-left {{
            background:
                radial-gradient(circle at top right, rgba(37, 99, 235, 0.12), transparent 34%),
                linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        }}

        .landing-kicker {{
            display: inline-flex;
            background: #dbeafe;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 8px 12px;
            font-weight: 900;
            font-size: 12px;
            letter-spacing: .4px;
            margin-bottom: 14px;
        }}

        .landing-left h2 {{
            font-size: 34px;
            line-height: 1.24;
            letter-spacing: -1.1px;
            margin: 0 0 14px;
        }}

        .landing-left p {{
            color: #475569;
            line-height: 1.7;
            margin-bottom: 18px;
        }}

        .hero-search-form {{
            background: #0f172a;
            border-radius: 18px;
            padding: 18px;
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.20);
        }}

        .hero-form-main {{
            display: grid;
            grid-template-columns: 1.5fr 0.7fr 0.7fr 0.75fr 0.9fr;
            gap: 10px;
            margin-bottom: 12px;
        }}

        .hero-form-main input {{
            border: 1px solid rgba(255,255,255,0.13);
            background: rgba(255,255,255,0.96);
            border-radius: 12px;
            padding: 13px 12px;
            font-size: 14px;
        }}

        .hero-search-form button {{
            width: 100%;
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: #ffffff;
            border: none;
            border-radius: 12px;
            padding: 14px 18px;
            font-size: 16px;
            font-weight: 900;
            cursor: pointer;
        }}

        .hero-quick-chips {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 14px;
        }}

        .hero-quick-chips a {{
            text-decoration: none;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            color: #1d4ed8;
            padding: 9px 12px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 800;
        }}

        .landing-right {{
            display: flex;
            flex-direction: column;
            gap: 14px;
            background:
                radial-gradient(circle at top right, rgba(37, 99, 235, 0.14), transparent 34%),
                linear-gradient(135deg, #f8fafc 0%, #eef6ff 100%);
            color: #0f172a;
            border: 1px solid #dbeafe;
        }}

        .signal-card {{
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid #dbeafe;
            border-radius: 16px;
            padding: 18px;
            box-shadow: 0 8px 18px rgba(37, 99, 235, 0.08);
        }}

        .primary-signal {{
            background: linear-gradient(135deg, #ffffff 0%, #eff6ff 100%);
            border-color: #bfdbfe;
        }}

        .signal-label {{
            font-size: 13px;
            color: #2563eb;
            font-weight: 900;
            margin-bottom: 8px;
        }}

        .signal-card h3 {{
            margin: 0 0 12px;
            line-height: 1.42;
            font-size: 17px;
            color: #111827;
        }}

        .signal-metrics {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 12px;
        }}

        .signal-metrics span {{
            background: #e0ecff;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 7px 10px;
            font-size: 12px;
            font-weight: 900;
        }}

        .signal-link-button {{
            display: inline-block;
            text-decoration: none;
            background: #0f172a;
            color: #ffffff;
            border-radius: 10px;
            padding: 9px 12px;
            font-size: 13px;
            font-weight: 900;
        }}

        .signal-mini-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr 1.4fr;
            gap: 10px;
        }}

        .signal-mini-grid div {{
            background: rgba(255,255,255,0.78);
            border: 1px solid #dbeafe;
            border-radius: 14px;
            padding: 14px;
        }}

        .signal-mini-grid b {{
            display: block;
            font-size: 20px;
            margin-bottom: 4px;
            color: #1d4ed8;
        }}

        .signal-mini-grid span {{
            color: #475569;
            font-size: 12px;
            line-height: 1.4;
        }}

        .recommendation-lab {{
            margin-bottom: 24px;
            background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
        }}

        .section-heading-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
            margin-bottom: 16px;
        }}

        .section-heading-row h2 {{
            margin: 0 0 8px;
            font-size: 26px;
        }}

        .section-heading-row p {{
            margin: 0;
            color: #475569;
            line-height: 1.6;
        }}

        .soft-link-button {{
            text-decoration: none;
            background: #dbeafe;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 10px 14px;
            font-weight: 900;
            white-space: nowrap;
            font-size: 14px;
        }}

        .mini-pick-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
        }}

        .mini-pick-card {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 18px;
        }}

        .mini-pick-label {{
            color: #1d4ed8;
            font-weight: 900;
            margin-bottom: 10px;
        }}

        .mini-pick-card h3 {{
            font-size: 16px;
            line-height: 1.45;
            margin: 0 0 10px;
        }}

        .mini-pick-card p {{
            color: #475569;
            line-height: 1.5;
            margin: 0 0 12px;
        }}

        .mini-pick-card a {{
            display: inline-block;
            text-decoration: none;
            color: white;
            background: #0f172a;
            border-radius: 10px;
            padding: 9px 12px;
            font-weight: 800;
        }}

        .purchase-checklist {{
            margin-bottom: 24px;
            display: grid;
            grid-template-columns: 0.9fr 1.1fr;
            gap: 20px;
            align-items: center;
        }}

        .purchase-checklist h2 {{
            margin: 0 0 10px;
            font-size: 26px;
        }}

        .purchase-checklist p {{
            color: #475569;
            line-height: 1.7;
            margin: 0;
        }}

        .checklist-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}

        .checklist-grid div {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 999px;
            text-align: center;
            padding: 12px;
            font-weight: 900;
            color: #1e3a8a;
        }}


        .quick-filter-panel {{
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
            max-width: 560px;
        }}

        .quick-filter-panel a {{
            text-decoration: none;
            background: #dbeafe;
            color: #1d4ed8;
            border: 1px solid #bfdbfe;
            border-radius: 999px;
            padding: 9px 12px;
            font-weight: 900;
            white-space: nowrap;
            font-size: 13px;
            transition: background 0.15s ease, transform 0.15s ease;
        }}

        .quick-filter-panel a:hover {{
            background: #bfdbfe;
            transform: translateY(-1px);
        }}


        .purpose-panel {{
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 18px;
            padding: 16px;
            margin: 18px 0;
        }}

        .purpose-panel-title {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
            margin-bottom: 12px;
        }}

        .purpose-panel-title b {{
            color: #1e3a8a;
            font-size: 16px;
        }}

        .purpose-panel-title span {{
            color: #64748b;
            font-size: 13px;
        }}

        .purpose-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }}

        .purpose-card {{
            text-decoration: none;
            display: block;
            border: 1px solid #dbeafe;
            background: #f8fbff;
            border-radius: 14px;
            padding: 14px;
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        }}

        .purpose-card:hover {{
            transform: translateY(-2px);
            border-color: #93c5fd;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.10);
        }}

        .purpose-card b {{
            display: block;
            color: #1d4ed8;
            font-size: 15px;
            margin-bottom: 5px;
        }}

        .purpose-card span {{
            color: #475569;
            font-size: 12px;
            line-height: 1.4;
        }}

        .result-toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 14px;
            padding: 14px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            margin: 14px 0 18px;
        }}

        .result-toolbar b {{
            color: #111827;
            display: block;
            margin-bottom: 4px;
        }}

        .result-toolbar span {{
            color: #64748b;
            font-size: 13px;
            line-height: 1.5;
        }}

        .sort-links {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: flex-end;
        }}

        .sort-links a {{
            text-decoration: none;
            border: 1px solid #bfdbfe;
            background: #ffffff;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 8px 11px;
            font-weight: 900;
            font-size: 13px;
        }}

        .sort-links a.active {{
            background: #2563eb;
            color: #ffffff;
            border-color: #2563eb;
        }}


        .brand-home-link {{
            display: inline-block;
            text-decoration: none;
            color: inherit;
            border-radius: 18px;
            transition: transform 0.15s ease, opacity 0.15s ease;
        }}

        .brand-home-link:hover {{
            transform: translateY(-2px);
            opacity: 0.96;
        }}

        .brand-home-link:focus-visible {{
            outline: 3px solid rgba(147, 197, 253, 0.95);
            outline-offset: 8px;
        }}

        .brand-home-link .main-title,
        .brand-home-link .sub-title-en {{
            color: inherit;
        }}


        .sticky-nav {{
            position: sticky;
            top: 0;
            z-index: 50;
            display: flex;
            justify-content: center;
            gap: 8px;
            padding: 10px 16px;
            background: rgba(248, 250, 252, 0.92);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid #e5e7eb;
        }}

        .sticky-nav a {{
            text-decoration: none;
            color: #1d4ed8;
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 999px;
            padding: 8px 13px;
            font-size: 13px;
            font-weight: 900;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
        }}

        .sticky-nav a:hover {{
            background: #eff6ff;
        }}

        .section-title-row {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            align-items: flex-start;
        }}

        .section-mini-badge {{
            white-space: nowrap;
            background: #dbeafe;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 8px 12px;
            font-size: 13px;
            font-weight: 900;
        }}

        .top8-toggle-input {{
            display: none;
        }}

        .compact-top8 .extra-price-card {{
            display: none;
        }}

        .top8-toggle-input:checked + .compact-top8 .extra-price-card {{
            display: block;
        }}

        .top8-toggle-label {{
            display: block;
            width: fit-content;
            margin: 18px auto 0;
            cursor: pointer;
            background: #0f172a;
            color: #ffffff;
            border-radius: 999px;
            padding: 12px 18px;
            font-size: 14px;
            font-weight: 900;
            box-shadow: 0 8px 18px rgba(15, 23, 42, 0.18);
        }}

        .top8-toggle-label .show-less-text {{
            display: none;
        }}

        .top8-toggle-input:checked ~ .top8-toggle-label .show-more-text {{
            display: none;
        }}

        .top8-toggle-input:checked ~ .top8-toggle-label .show-less-text {{
            display: inline;
        }}

        .pros-cons-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin: 12px 0;
        }}

        .pros-box,
        .cautions-box {{
            border-radius: 12px;
            padding: 14px;
            border: 1px solid #e5e7eb;
        }}

        .pros-box {{
            background: #f0fdf4;
            border-color: #bbf7d0;
        }}

        .cautions-box {{
            background: #fff7ed;
            border-color: #fed7aa;
        }}

        .pros-box h4,
        .cautions-box h4 {{
            margin: 0 0 8px;
            font-size: 15px;
        }}

        .pros-box h4 {{
            color: #166534;
        }}

        .cautions-box h4 {{
            color: #9a3412;
        }}

        .pros-box ul,
        .cautions-box ul {{
            margin: 0;
            padding-left: 18px;
            color: #374151;
            line-height: 1.6;
            font-size: 14px;
        }}

        .purpose-context-box {{
            display: grid;
            grid-template-columns: minmax(240px, 0.9fr) minmax(360px, 1.1fr);
            gap: 16px;
            align-items: stretch;
            background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
            border: 1px solid #bfdbfe;
            border-radius: 16px;
            padding: 18px;
            margin: 14px 0 18px;
        }}

        .purpose-context-label {{
            display: inline-block;
            background: #dbeafe;
            color: #1d4ed8;
            border-radius: 999px;
            padding: 7px 10px;
            font-weight: 900;
            font-size: 12px;
            margin-bottom: 10px;
        }}

        .purpose-context-box h3 {{
            margin: 0 0 8px;
            color: #1e3a8a;
            font-size: 22px;
        }}

        .purpose-context-box p {{
            margin: 0;
            color: #475569;
            line-height: 1.6;
        }}

        .purpose-context-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
        }}

        .purpose-context-grid div {{
            background: #ffffff;
            border: 1px solid #dbeafe;
            border-radius: 12px;
            padding: 12px;
            color: #334155;
            line-height: 1.45;
            font-size: 13px;
        }}

        .purpose-context-grid b {{
            color: #1d4ed8;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        #home,
        #purpose,
        #results,
        #top8,
        #notice {{
            scroll-margin-top: 72px;
        }}


        .learning-links-box {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
            margin-bottom: 28px;
        }}

        .learning-card-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 14px;
            margin-top: 18px;
        }}

        .learning-card {{
            display: block;
            text-decoration: none;
            background: #f8fafc;
            border: 1px solid #dbeafe;
            border-radius: 16px;
            padding: 20px;
            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        }}

        .learning-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.10);
            border-color: #93c5fd;
        }}

        .learning-card span {{
            display: inline-block;
            color: #2563eb;
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.4px;
            margin-bottom: 8px;
        }}

        .learning-card h3 {{
            margin: 0 0 8px;
            color: #111827;
            font-size: 19px;
        }}

        .learning-card p {{
            margin: 0;
            color: #475569;
            line-height: 1.6;
            font-size: 14px;
        }}

    </style>
</head>

<body>
    <header id="home">
        <div class="header-inner">
            <a class="brand-home-link" href="/" aria-label="리퍼 트래커 홈으로 이동">
                <div class="logo-line">DATA-DRIVEN PRICE TRACKING</div>

                <h1 class="main-title">리퍼 트래커</h1>
                <div class="sub-title-en">Refurb Laptop Tracker</div>
            </a>

            <div class="desc-box">
                <div class="desc-ko-title">리퍼·중고 노트북 가격 비교 도구</div>
                <div class="desc-ko-text">
                    네이버 쇼핑 데이터를 바탕으로 가격과 사양을 함께 비교합니다.
                </div>
            </div>
        </div>
    </header>

    {render_sticky_nav()}

    <main>
        {render_service_landing_section(keyword_value, ram_value, ssd_value, cpu_value, price_value)}
        {result_html}
        {render_main_dashboard(keyword_value, ram_value, ssd_value, cpu_value, price_value)}

        {render_roadmap_section()}
    </main>
</body>
</html>
"""


def render_static_page(title, subtitle, body_html, description):
    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(title)} | 리퍼 트래커</title>
    <meta name="description" content="{esc(description)}">
    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", Arial, sans-serif;
            background: #f8fafc;
            color: #0f172a;
        }}

        .page-header {{
            background: linear-gradient(135deg, #1e3a8a, #2563eb);
            color: white;
            padding: 42px 22px 46px;
        }}

        .page-header-inner {{
            max-width: 980px;
            margin: 0 auto;
        }}

        .top-link {{
            display: inline-block;
            color: #dbeafe;
            text-decoration: none;
            font-weight: 800;
            margin-bottom: 18px;
        }}

        .page-header h1 {{
            font-size: 40px;
            line-height: 1.22;
            margin: 0 0 12px;
            letter-spacing: -1px;
        }}

        .page-header p {{
            max-width: 760px;
            margin: 0;
            color: #dbeafe;
            line-height: 1.7;
            font-size: 17px;
        }}

        main {{
            max-width: 980px;
            margin: 28px auto 48px;
            padding: 0 18px;
        }}

        .content-card {{
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 22px;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
            padding: 34px;
        }}

        .content-card h2 {{
            font-size: 26px;
            margin: 30px 0 12px;
            color: #1e3a8a;
        }}

        .content-card h2:first-child {{
            margin-top: 0;
        }}

        .content-card p {{
            color: #334155;
            line-height: 1.82;
            font-size: 16px;
        }}

        .content-card ul {{
            margin: 10px 0 22px;
            padding-left: 22px;
            color: #334155;
            line-height: 1.85;
        }}

        .content-card li {{
            margin-bottom: 7px;
        }}

        .tip-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 16px;
            padding: 18px 20px;
            margin: 22px 0;
        }}

        .tip-box b {{
            color: #1d4ed8;
        }}

        .cta-box {{
            margin-top: 30px;
            background: #0f172a;
            color: white;
            border-radius: 18px;
            padding: 24px;
        }}

        .cta-box p {{
            color: #e2e8f0;
        }}

        .cta-box a {{
            display: inline-block;
            text-decoration: none;
            background: #2563eb;
            color: white;
            border-radius: 999px;
            padding: 12px 16px;
            font-weight: 900;
            margin-top: 8px;
        }}

        .sub-links {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 22px;
        }}

        .sub-links a {{
            text-decoration: none;
            color: #1d4ed8;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 999px;
            padding: 9px 13px;
            font-weight: 800;
            font-size: 14px;
        }}

        @media (max-width: 700px) {{
            .page-header h1 {{
                font-size: 30px;
            }}

            .content-card {{
                padding: 22px;
                border-radius: 16px;
            }}
        }}
    </style>
</head>
<body>
    <header class="page-header">
        <div class="page-header-inner">
            <a class="top-link" href="/">← 리퍼 트래커로 돌아가기</a>
            <h1>{esc(title)}</h1>
            <p>{esc(subtitle)}</p>
        </div>
    </header>

    <main>
        <article class="content-card">
            {body_html}

            <div class="cta-box">
                <h2>직접 조건을 넣어 비교해 보세요</h2>
                <p>
                    브랜드, RAM, SSD, 예산을 입력하면 현재 수집 데이터 기준으로 먼저 볼 만한 후보를 확인할 수 있습니다.
                </p>
                <a href="/">리퍼 트래커에서 검색하기</a>
            </div>

            <div class="sub-links">
                <a href="/guide">리퍼 노트북 고르는 법</a>
                <a href="/checklist">구매 전 체크리스트</a>
                <a href="/about">판단 방식 보기</a>
            </div>
        </article>
    </main>
</body>
</html>
"""


def render_guide_page():
    body = """
    <h2>처음에는 가격보다 조건을 먼저 정하세요</h2>
    <p>
        리퍼·중고 노트북은 같은 모델처럼 보여도 RAM, SSD, CPU, 보증 조건, 제품 상태가 다를 수 있습니다.
        그래서 단순히 가장 싼 상품을 고르기보다, 먼저 내가 필요한 최소 조건을 정해두는 편이 좋습니다.
    </p>

    <div class="tip-box">
        <b>기본 추천 조건</b><br>
        일반적인 문서 작업, 온라인 강의, 웹서핑, 가벼운 업무라면 RAM 16GB, SSD 512GB 이상부터 보는 것을 권합니다.
    </div>

    <h2>가격은 평균가와 함께 보세요</h2>
    <p>
        리퍼 상품은 판매처마다 가격 차이가 큽니다. 현재가가 낮아 보여도 원래 그 모델의 평균 가격과 비교해야
        실제로 저렴한지 판단할 수 있습니다.
    </p>
    <ul>
        <li>현재 가격이 평균가보다 낮은지 확인합니다.</li>
        <li>최근 관측 최저가에 가까운지 확인합니다.</li>
        <li>판매처가 여러 곳인지 확인합니다.</li>
        <li>가격 차이가 너무 크면 제품 상태나 보증 조건이 다른지 확인합니다.</li>
    </ul>

    <h2>판매처 수가 많을수록 비교하기 쉽습니다</h2>
    <p>
        같은 모델을 여러 판매처가 팔고 있다면 가격 비교가 조금 더 쉽습니다. 반대로 판매처가 한 곳뿐이라면
        가격이 괜찮아 보여도 상세 페이지를 더 꼼꼼히 확인해야 합니다.
    </p>

    <h2>리퍼·중고는 마지막 확인이 중요합니다</h2>
    <p>
        데이터는 후보를 좁혀주는 데 도움이 되지만, 최종 구매 전에는 상품 상세 페이지에서 제품 상태와 반품 조건을 직접 확인해야 합니다.
    </p>
    """
    return render_static_page(
        "리퍼 노트북 고르는 법",
        "처음 리퍼·중고 노트북을 고를 때 가격, 사양, 판매처를 어떤 순서로 보면 좋은지 정리했습니다.",
        body,
        "리퍼 노트북을 고를 때 확인해야 할 가격, 사양, 판매처, 보증 조건을 정리한 안내 페이지입니다."
    )


def render_checklist_page():
    body = """
    <h2>1. 사양 확인</h2>
    <ul>
        <li>RAM은 최소 16GB 이상인지 확인합니다.</li>
        <li>SSD는 최소 512GB 이상인지 확인합니다.</li>
        <li>CPU 모델과 세대가 명확히 표시되어 있는지 봅니다.</li>
        <li>윈도우 포함 여부를 확인합니다.</li>
    </ul>

    <h2>2. 제품 상태 확인</h2>
    <ul>
        <li>외관 등급이 적혀 있는지 확인합니다.</li>
        <li>액정, 키보드, 힌지, 포트 상태를 확인합니다.</li>
        <li>배터리 상태나 사이클 수가 표시되어 있는지 봅니다.</li>
        <li>구성품이 충전기 포함인지 확인합니다.</li>
    </ul>

    <h2>3. 가격과 판매 조건 확인</h2>
    <ul>
        <li>배송비가 별도인지 확인합니다.</li>
        <li>반품 가능 여부와 반품 배송비를 확인합니다.</li>
        <li>보증 기간이 있는지 확인합니다.</li>
        <li>같은 모델의 다른 판매처 가격도 함께 봅니다.</li>
    </ul>

    <div class="tip-box">
        <b>주의할 점</b><br>
        너무 싼 상품은 이유가 있을 수 있습니다. 부품용, 액정 파손, 배터리 불량, 윈도우 미포함 같은 조건이 숨어 있을 수 있으니
        제목과 상세 설명을 꼭 확인하세요.
    </div>

    <h2>4. 구매 전 마지막 질문</h2>
    <ul>
        <li>이 가격이 평균가보다 충분히 낮은가?</li>
        <li>상세 페이지에서 제품 상태가 명확한가?</li>
        <li>반품이나 보증이 가능한가?</li>
        <li>내가 필요한 RAM, SSD, CPU 조건을 충족하는가?</li>
    </ul>
    """
    return render_static_page(
        "중고·리퍼 노트북 구매 전 체크리스트",
        "구매 전에 사양, 제품 상태, 보증, 반품 조건을 빠뜨리지 않고 확인할 수 있도록 정리했습니다.",
        body,
        "중고 노트북과 리퍼 노트북을 구매하기 전 확인해야 할 사양, 배터리, 보증, 반품 조건 체크리스트입니다."
    )


def render_about_page():
    body = """
    <h2>리퍼 트래커는 무엇을 하나요?</h2>
    <p>
        리퍼 트래커는 네이버 쇼핑의 공개 상품 데이터를 수집해 리퍼·중고 노트북의 가격과 사양을 비교하는 도구입니다.
        사용자가 브랜드, RAM, SSD, CPU, 예산을 입력하면 조건에 맞는 후보를 찾아 보여줍니다.
    </p>

    <h2>어떤 기준으로 판단하나요?</h2>
    <p>
        리퍼 트래커는 단순히 가장 싼 상품만 보여주지 않습니다. 현재 가격이 평균가보다 낮은지, 관측 최저가에 가까운지,
        판매처 수와 관측 수가 충분한지, RAM과 SSD 조건이 실사용에 적합한지를 함께 봅니다.
    </p>

    <ul>
        <li>현재가와 평균가 비교</li>
        <li>최근 최저가 여부</li>
        <li>판매처 수와 관측 수</li>
        <li>RAM, SSD, CPU 사양</li>
        <li>동일·유사 모델 간 가격 차이</li>
    </ul>

    <h2>점수는 참고용입니다</h2>
    <p>
        리퍼·중고 상품은 실제 상태가 매우 중요합니다. 같은 모델이라도 외관, 배터리, 보증 기간, 구성품에 따라 가치가 달라질 수 있습니다.
        그래서 리퍼 트래커의 점수는 구매 결정을 대신하는 것이 아니라, 먼저 살펴볼 후보를 좁혀주는 참고 정보입니다.
    </p>

    <h2>앞으로 보완할 점</h2>
    <p>
        데이터가 더 쌓이면 가격 흐름을 더 안정적으로 볼 수 있습니다. 이후에는 관심 모델 저장, 가격 하락 알림,
        판매처 신뢰도 반영, CPU 세대 분석 같은 기능으로 확장할 수 있습니다.
    </p>
    """
    return render_static_page(
        "리퍼 트래커의 판단 방식",
        "리퍼 트래커가 가격, 평균가, 최저가, 판매처 수, 사양 정보를 어떻게 참고하는지 설명합니다.",
        body,
        "리퍼 트래커가 리퍼·중고 노트북의 가격과 사양을 비교하고 구매 후보를 판단하는 방식을 설명합니다."
    )

app = Flask(__name__)



@app.route("/guide")
def guide():
    return Response(render_guide_page(), mimetype="text/html; charset=utf-8")


@app.route("/checklist")
def checklist():
    return Response(render_checklist_page(), mimetype="text/html; charset=utf-8")


@app.route("/about")
def about():
    return Response(render_about_page(), mimetype="text/html; charset=utf-8")



@app.route("/google47e9a5428b88c145.html")
def google_site_verification():
    return Response("google-site-verification: google47e9a5428b88c145.html", mimetype="text/plain; charset=utf-8")


@app.route("/robots.txt")
def robots_txt():
    content = """User-agent: *
Allow: /
Sitemap: https://refurb-laptop-tracker.onrender.com/sitemap.xml
"""
    return Response(content, mimetype="text/plain; charset=utf-8")


@app.route("/sitemap.xml")
def sitemap_xml():
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://refurb-laptop-tracker.onrender.com/</loc>
  </url>
  <url>
    <loc>https://refurb-laptop-tracker.onrender.com/guide</loc>
  </url>
  <url>
    <loc>https://refurb-laptop-tracker.onrender.com/checklist</loc>
  </url>
  <url>
    <loc>https://refurb-laptop-tracker.onrender.com/about</loc>
  </url>
</urlset>
"""
    return Response(content, mimetype="application/xml; charset=utf-8")


@app.route("/")
def index():
    keyword = request.args.get("keyword", "")
    ram = request.args.get("ram", "")
    ssd = request.args.get("ssd", "")
    cpu = request.args.get("cpu", "")
    max_price = request.args.get("max_price", "")
    purpose = request.args.get("purpose", "")
    sort_key = request.args.get("sort", "recommend")

    keyword, ram, ssd, cpu, max_price, sort_key = apply_purpose_defaults(
        purpose, keyword, ram, ssd, cpu, max_price, sort_key
    )

    has_query = any([keyword, ram, ssd, cpu, max_price, purpose])

    if has_query:
        result = search_products(keyword, ram, ssd, cpu, max_price, sort_key, purpose)
    else:
        result = None

    page = render_page(result)
    return Response(page, mimetype="text/html; charset=utf-8")


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    print("=" * 70)
    print("Flask 웹 서버 실행 중")
    print("=" * 70)
    print("브라우저에서 아래 주소를 여세요.")
    print(f"http://localhost:{port}")
    print()
    print("종료하려면 터미널에서 Ctrl + C를 누르세요.")

    app.run(host="0.0.0.0", port=port, debug=True)
