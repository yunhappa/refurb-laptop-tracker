import csv
import html
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

INPUT_FILENAME = "buy_timing_result.csv"


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


def search_products(keyword_input, ram_input, ssd_input, cpu_input, max_price_input):
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
        search_type = "정확히 일치하는 검색 결과"
        products = exact_products
    else:
        relaxed_cpu_products = [
            row for row in all_products
            if is_match(row, keyword, ram_filter, ssd_filter, "", max_price)
        ]
        relaxed_cpu_products.sort(key=product_sort_key, reverse=True)

        if relaxed_cpu_products:
            search_type = "유사 상품 추천: CPU 조건을 제외한 결과"
            products = relaxed_cpu_products
        else:
            relaxed_price_products = [
                row for row in all_products
                if is_match(row, keyword, ram_filter, ssd_filter, "", None)
            ]
            relaxed_price_products.sort(key=product_sort_key, reverse=True)

            if relaxed_price_products:
                search_type = "유사 상품 추천: CPU와 최대 가격 조건을 제외한 결과"
                products = relaxed_price_products
            else:
                keyword_only_products = [
                    row for row in all_products
                    if is_match(row, keyword, "", "", "", None)
                ]
                keyword_only_products.sort(key=product_sort_key, reverse=True)

                if keyword_only_products:
                    search_type = "유사 상품 추천: 키워드만 적용한 결과"
                    products = keyword_only_products
                else:
                    search_type = "검색 결과 없음"
                    products = []

    return {
        "search_type": search_type,
        "products": products,
        "keyword": keyword_input,
        "ram": ram_filter,
        "ssd": ssd_filter,
        "cpu": cpu_filter,
        "max_price": max_price,
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
            f"추천 요약: 현재 조건에서는 구매 추천 상품입니다. "
            f"가성비 점수는 {value_score}점이며, 동일 모델을 여러 판매처에서 비교할 수 있습니다."
        )
    if decision == "구매 고려":
        return (
            f"추천 요약: 현재 조건에서는 구매를 고려할 만한 상품입니다. "
            f"가성비 점수는 {value_score}점이며, 판매처 {mall_count}곳의 가격 비교가 가능합니다."
        )
    if decision == "데이터 부족":
        return (
            f"추천 요약: 가성비 점수는 {value_score}점으로 높지만, "
            f"동일 모델 비교 데이터가 부족하여 추가 확인이 필요합니다."
        )
    if price_gap >= 100000:
        return (
            "추천 요약: 현재 기준으로는 보류입니다. "
            "다만 판매처별 가격 차이가 커서 최저가 확인은 필요합니다."
        )
    return (
        "추천 요약: 현재 기준으로는 보류입니다. "
        "가성비 점수가 상대적으로 낮거나 비교 데이터가 충분하지 않습니다."
    )


def render_project_summary_section():
    stats = get_project_stats()

    return f"""
    <section class="project-summary-box">
        <h2>프로젝트 현황 요약</h2>
        <p class="summary-intro">
            네이버 쇼핑 API를 통해 리퍼/중고 노트북 데이터를 수집하고,
            실사용 후보 필터링, 가성비 점수화, 모델·사양별 그룹화, 구매 판단까지 수행했습니다.
        </p>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">전체 수집 기록</div>
                <div class="stat-number">{stats["raw_count"]:,}</div>
                <div class="stat-desc">누적 가격 관측 데이터</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">고유 상품 ID</div>
                <div class="stat-number">{stats["unique_product_count"]:,}</div>
                <div class="stat-desc">네이버 상품 ID 기준</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">실사용 후보</div>
                <div class="stat-number">{stats["candidate_count"]:,}</div>
                <div class="stat-desc">RAM 16GB 이상, SSD 512GB 이상</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">모델/사양 그룹</div>
                <div class="stat-number">{stats["model_group_count"]:,}</div>
                <div class="stat-desc">중복 판매처를 묶은 비교 단위</div>
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
    </section>
    """

def render_price_history_section():
    rows = read_csv_rows("price_history_summary.csv")

    if not rows:
        return """
        <section class="price-history-box">
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

    # price_history_summary.csv가 이미 구매 적기 점수 기준으로 정렬되어 있으므로
    # 웹에서는 그 순서를 유지하되, 화면상 같은 상품만 한 번 더 제거한다.
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

        cards += f"""
        <div class="price-card">
            <div class="price-rank">{index}위</div>
            <div class="price-badge">🔥 {timing_signal}</div>\n            <div class="timing-score">구매 적기 점수 <b>{buy_timing_score}</b>점</div>

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
                구매 적기 점수는 평균 대비 할인율, 최근 최저가 여부, 관측 수, 판매처 수를 종합한 값입니다.
            </p>

            <a class="link-button" href="{link}" target="_blank">상품 페이지 열기</a>
        </div>
        """

    return f"""
    <section class="price-history-box">
        <h2>구매 적기 점수 TOP 8</h2>
        <p class="summary-intro">
            평균 대비 할인율, 최근 최저가 여부, 관측 수, 판매처 수를 종합해 현재 구매 타이밍이 좋은 상품을 보여줍니다.
        </p>

        <div class="price-card-list">
            {cards}
        </div>
    </section>
    """

def render_criteria_section():
    return """
    <section class="criteria-box">
        <h2>가성비 판단 기준</h2>
        <p class="criteria-intro">
            본 서비스는 단순히 상품을 검색하는 것이 아니라,
            RAM·SSD·CPU를 점수화하고 가격과 비교하여 가성비 점수를 계산합니다.
            또한 동일 모델의 판매처 수와 가격 차이를 함께 고려하여 구매 판단을 제공합니다.
        </p>

        <div class="criteria-grid">
            <div class="criteria-card">
                <h3>1. 사양 점수</h3>
                <p>노트북의 기본 성능을 RAM, SSD, CPU 기준으로 점수화합니다.</p>
                <div class="formula">사양 점수 = RAM×3 + SSD(GB)×0.05 + CPU 점수</div>
                <div class="score-table">
                    CPU 점수 예시<br>
                    i3: 30점 / i5: 50점 / i7: 70점 / i9: 90점<br>
                    Ryzen 5: 50점 / Ryzen 7: 70점<br>
                    Apple M1: 60점 / M2: 70점 / M3: 80점 / M4: 90점
                </div>
            </div>

            <div class="criteria-card">
                <h3>2. 가성비 점수</h3>
                <p>
                    사양 점수를 가격으로 나누어 가격 대비 성능을 계산합니다.
                    같은 사양이라면 가격이 낮을수록 가성비 점수가 높아집니다.
                </p>
                <div class="formula">가성비 점수 = 사양 점수 ÷ 가격(백만 원 단위)</div>
                <div class="score-table">
                    예시<br>
                    사양 점수 150점, 가격 500,000원인 경우<br>
                    150 ÷ 0.5 = 300점
                </div>
            </div>

            <div class="criteria-card">
                <h3>3. 구매 판단</h3>
                <p>가성비 점수와 동일 모델 판매처 수를 함께 고려합니다.</p>
                <ul>
                    <li>280점 이상 + 판매처 2곳 이상: 구매 추천</li>
                    <li>240점 이상 + 판매처 2곳 이상: 구매 고려</li>
                    <li>240점 이상 + 판매처 1곳: 데이터 부족</li>
                    <li>그 외: 보류</li>
                </ul>
                <div class="score-table">
                    판매처별 가격 차이가 10만 원 이상이면<br>
                    최저가 판매처 확인 문구를 추가합니다.
                </div>
            </div>
        </div>

        <p class="criteria-note">
            ※ 현재 버전은 CSV 기반의 규칙 기반 프로토타입입니다.
            데이터가 장기간 누적되면 가격 이력, 평균가, 최저가, 가격 하락률을 반영하여
            더 정교한 구매 적기 판단 모델로 확장할 수 있습니다.
        </p>
    </section>
    """


def render_roadmap_section():
    return """
    <section class="roadmap-box">
        <div class="future-title-row">
            <h2>앞으로 계속 더 좋아집니다! 🚀</h2>
            <p>
                현재 버전은 CSV 기반 프로토타입이지만, 데이터가 더 쌓일수록 가격 판단의 정확도를 높이고
                더 편리한 구매 추천 서비스로 확장할 수 있습니다.
            </p>
        </div>

        <div class="roadmap-grid">
            <div class="roadmap-card">
                <h3>1. 더 많은 데이터 수집</h3>
                <p>수집 기간이 길어질수록 평균가, 최저가, 가격 하락률 판단이 더 안정적으로 변합니다.</p>
            </div>

            <div class="roadmap-card">
                <h3>2. ClickHouse 대용량 분석</h3>
                <p>장기간 누적 데이터를 ClickHouse에 적재하여 수십만 건 이상의 가격 이력을 빠르게 조회할 수 있습니다.</p>
            </div>

            <div class="roadmap-card">
                <h3>3. 가격 하락 알림</h3>
                <p>관심 모델이 평균가보다 낮아지거나 최근 최저가가 되면 알림을 주는 기능으로 발전시킬 수 있습니다.</p>
            </div>

            <div class="roadmap-card">
                <h3>4. 사양 점수 고도화</h3>
                <p>CPU 세대, 무게, 화면 크기, 보증 여부, 리퍼 등급, 판매처 신뢰도를 반영할 수 있습니다.</p>
            </div>

            <div class="roadmap-card">
                <h3>5. 사용자 맞춤 추천</h3>
                <p>사용자의 검색 이력과 선호 사양을 바탕으로 더 적합한 상품을 우선 추천할 수 있습니다.</p>
            </div>
        </div>

        <div class="future-message">
            💙 사용자의 피드백과 데이터가 쌓일수록 더 똑똑한 리퍼 트래커로 발전합니다.
        </div>
    </section>
    """

def render_search_section(keyword_value, ram_value, ssd_value, cpu_value, price_value):
    return f"""
    <section class="search-box">
        <h2>검색 조건 입력</h2>

        <form method="GET" action="/">
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


def render_main_dashboard(keyword_value, ram_value, ssd_value, cpu_value, price_value):
    return f"""
    <section class="dashboard-layout">
        <div class="dashboard-left">
            {render_project_summary_section()}
            {render_search_section(keyword_value, ram_value, ssd_value, cpu_value, price_value)}
            {render_criteria_section()}
        </div>

        <aside class="dashboard-right">
            {render_price_history_section()}
        </aside>
    </section>
    """


def render_product_cards(products):
    if not products:
        return "<p class='empty'>조건에 맞는 상품이 없습니다.</p>"

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

        cards += f"""
        <div class="card">
            <div class="rank">{index}위</div>
            <div class="decision {decision_class}">{decision}</div>

            <h3>{title}</h3>

            <p class="summary-sentence">{summary_sentence}</p>
            <p class="reason">{reason}</p>

            <div class="info-grid">
                <div><b>가격</b><br>{price:,}원</div>
                <div><b>판매처</b><br>{mall}</div>
                <div><b>브랜드</b><br>{brand}</div>
                <div><b>RAM</b><br>{ram}</div>
                <div><b>SSD</b><br>{ssd}</div>
                <div><b>CPU</b><br>{cpu if cpu else "미확인"}</div>
                <div><b>가성비 점수</b><br>{value_score}</div>
                <div><b>동일 모델 후보</b><br>{seller_count}개</div>
                <div><b>판매처 수</b><br>{mall_count}개</div>
                <div><b>가격 차이</b><br>{price_gap:,}원</div>
            </div>

            <p class="model-key"><b>모델키:</b> {model_key}</p>
            <a class="link-button" href="{link}" target="_blank">상품 페이지 열기</a>
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

        result_html = f"""
        <section class="summary">
            <h2>입력한 검색 조건</h2>
            <div class="condition-grid">
                <div><b>키워드</b><br>{keyword_value if keyword_value else "전체"}</div>
                <div><b>RAM</b><br>{ram_value if ram_value else "전체"}</div>
                <div><b>SSD</b><br>{ssd_value if ssd_value else "전체"}</div>
                <div><b>CPU</b><br>{cpu_value if cpu_value else "전체"}</div>
                <div><b>최대 가격</b><br>{max_price_display}</div>
            </div>
        </section>

        <section class="results">
            <h2>{search_type}</h2>
            <p class="count">상품 수: {len(products)}개</p>
            {render_product_cards(products)}
        </section>
        """

    return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
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
    </style>
</head>

<body>
    <header>
        <div class="header-inner">
            <div class="logo-line">DATA-DRIVEN PRICE TRACKING</div>

            <h1 class="main-title">리퍼 트래커</h1>
            <div class="sub-title-en">Refurb Laptop Tracker</div>

            <div class="desc-box">
                <div class="desc-ko-title">리퍼/중고 노트북 구매 판단 검색기</div>
                <div class="desc-ko-text">
                    네이버 쇼핑 API 수집 데이터 기반으로 모델·사양·가격을 비교하고 구매 판단을 제공합니다.
                </div>
            </div>
        </div>
    </header>

    <main>
        {render_main_dashboard(keyword_value, ram_value, ssd_value, cpu_value, price_value)}

        {result_html}

        {render_roadmap_section()}
    </main>
</body>
</html>
"""


class LaptopSearchHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)

        keyword = query.get("keyword", [""])[0]
        ram = query.get("ram", [""])[0]
        ssd = query.get("ssd", [""])[0]
        cpu = query.get("cpu", [""])[0]
        max_price = query.get("max_price", [""])[0]

        has_query = any([keyword, ram, ssd, cpu, max_price])

        if has_query:
            result = search_products(keyword, ram, ssd, cpu, max_price)
        else:
            result = None

        page = render_page(result)

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))


def run_server():
    server_address = ("localhost", 8000)
    httpd = HTTPServer(server_address, LaptopSearchHandler)

    print("=" * 70)
    print("웹 서버 실행 중")
    print("=" * 70)
    print("브라우저에서 아래 주소를 여세요.")
    print("http://localhost:8000")
    print()
    print("종료하려면 터미널에서 Ctrl + C를 누르세요.")

    httpd.serve_forever()


run_server()
