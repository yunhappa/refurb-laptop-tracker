# 리퍼 트래커 / Refurb Laptop Tracker

리퍼 트래커는 리퍼·중고 노트북을 구매할 때 가격과 사양을 함께 비교해 볼 수 있도록 만든 웹서비스입니다.  
네이버 쇼핑 API로 수집한 상품 데이터를 바탕으로 현재가, 평균가, 최저가, 판매처 수, RAM, SSD, CPU 정보를 정리하고, 먼저 살펴볼 만한 후보를 보여줍니다.

- 서비스 주소: https://refurb-laptop-tracker.onrender.com
- GitHub 저장소: https://github.com/yunhappa/refurb-laptop-tracker

---

## 1. 프로젝트 소개

리퍼·중고 노트북은 같은 모델처럼 보여도 판매처, 제품 상태, RAM, SSD, CPU, 보증 조건에 따라 실제 가치가 크게 달라집니다.  
단순히 최저가만 보고 고르기 어렵기 때문에, 이 프로젝트는 다음 정보를 함께 비교하도록 구성했습니다.

- 현재 가격
- 평균 가격
- 관측 최저가
- 판매처 수
- 동일·유사 모델 후보 수
- RAM / SSD / CPU 사양
- 예산별 후보
- 용도별 추천 조건
- 구매 전 확인할 주의 사항

최종 목표는 사용자가 원하는 노트북 조건을 입력했을 때, 현재 시장 가격이 괜찮은지 판단하는 데 도움을 주는 것입니다.

---

## 2. 주요 기능

### 2.1 조건 기반 상품 검색

사용자는 아래 조건을 입력해 리퍼·중고 노트북 후보를 찾을 수 있습니다.

- 브랜드 또는 모델명
- RAM
- SSD
- CPU
- 최대 가격

예를 들어 `ThinkPad`, `16GB`, `512GB`, `70만원 이하` 같은 조건으로 후보를 좁혀 볼 수 있습니다.

### 2.2 용도별 추천

처음부터 세부 사양을 잘 모르는 사용자를 위해 용도별 추천 버튼을 제공합니다.

- 대학생용
- 사무용
- 휴대용
- 개발용
- 고성능
- 가성비

각 버튼은 해당 용도에 맞는 기본 검색 조건을 적용합니다.

### 2.3 예산별 후보

예산대별로 먼저 볼 만한 후보를 보여줍니다.

- 50만원 이하
- 50~70만원
- 70~100만원

### 2.4 구매 판단 보조

상품별로 단순 가격만 보여주는 것이 아니라, 아래 정보를 함께 제공합니다.

- 한줄 판단
- 비교 신뢰도
- 장점
- 주의할 점
- 추천 판단 근거
- 상품 페이지 이동 링크

### 2.5 가격 이력 기반 후보

수집된 가격 데이터를 바탕으로 평균가 대비 현재 가격, 관측 최저가, 판매처 수 등을 비교해 가격 흐름이 좋은 후보를 보여줍니다.

---

## 3. 데이터 수집 방식

데이터는 네이버 쇼핑 API를 통해 수집합니다.  
수집 대상 키워드는 리퍼·중고 노트북과 관련된 검색어입니다.

예시 키워드:

- 리퍼 노트북
- 중고 노트북
- 리퍼 맥북
- 중고 맥북
- LG그램 리퍼
- ThinkPad 중고
- 갤럭시북 리퍼

수집된 데이터는 CSV 파일로 저장한 뒤, 분석 스크립트를 통해 후보 필터링과 점수 계산에 사용합니다.

---

## 4. 데이터 처리 흐름

전체 흐름은 다음과 같습니다.

```text
네이버 쇼핑 API 수집
        ↓
CSV 저장
        ↓
상품명 정리 및 사양 추출
        ↓
RAM / SSD / CPU 정보 추출
        ↓
실사용 후보 필터링
        ↓
동일·유사 모델 그룹화
        ↓
가성비 점수 계산
        ↓
구매 판단 결과 생성
        ↓
Flask 웹서비스에서 결과 표시
```

---

## 5. 추천 판단 기준

리퍼 트래커는 다음 기준을 종합해 상품을 분류합니다.

### 가격 기준

- 현재가가 평균가보다 낮은지
- 최근 관측 최저가에 가까운지
- 판매처별 가격 차이가 큰지

### 사양 기준

- RAM 16GB 이상 여부
- SSD 512GB 이상 여부
- CPU 정보 확인 여부
- 용도별 조건 충족 여부

### 비교 신뢰도 기준

- 동일·유사 모델 후보 수
- 판매처 수
- 관측 데이터 수

결과는 다음과 같이 표시합니다.

- 구매 추천
- 구매 고려
- 데이터 부족
- 보류

단, 리퍼·중고 상품은 제품 상태, 배터리, 보증, 반품 조건에 따라 실제 가치가 달라질 수 있으므로 최종 구매 전 상품 페이지 확인이 필요합니다.

---

## 6. 기술 스택

### Backend

- Python
- Flask
- Gunicorn

### Data Collection / Analysis

- Naver Shopping API
- pandas
- CSV 기반 데이터 처리
- 정규표현식 기반 RAM / SSD / CPU 추출

### Deployment

- Render
- GitHub
- GitHub Actions

### SEO / Search Registration

- Google Search Console
- Naver Search Advisor
- sitemap.xml
- robots.txt
- RSS
- Open Graph meta tags

---

## 7. 주요 파일 구조

```text
refurb-laptop-tracker/
│
├─ app.py
│  └─ Flask 웹서비스 메인 파일
│
├─ naver_shopping_collect.py
│  └─ 네이버 쇼핑 API 데이터 수집 스크립트
│
├─ update_all.py
│  └─ 수집부터 분석까지 전체 파이프라인 실행
│
├─ analyze_prices.py
│  └─ 가격 데이터 분석
│
├─ analyze_latest_products.py
│  └─ 최신 상품 후보 분석
│
├─ score_candidates.py
│  └─ 후보 상품 점수 계산
│
├─ judge_buy_timing.py
│  └─ 구매 판단 결과 생성
│
├─ analyze_price_history.py
│  └─ 가격 이력 분석
│
├─ requirements.txt
│  └─ Python 패키지 목록
│
├─ .github/workflows/update_data.yml
│  └─ GitHub Actions 자동 데이터 갱신 설정
│
├─ refurb_laptop_prices.csv
│  └─ 누적 수집 원본 데이터
│
├─ candidate_products.csv
│  └─ 실사용 후보 상품 데이터
│
├─ scored_candidates.csv
│  └─ 점수 계산 결과
│
├─ buy_timing_result.csv
│  └─ 구매 판단 결과
│
└─ price_history_summary.csv
   └─ 가격 이력 요약 데이터
```

---

## 8. 로컬 실행 방법

### 8.1 저장소 클론

```bash
git clone https://github.com/yunhappa/refurb-laptop-tracker.git
cd refurb-laptop-tracker
```

### 8.2 패키지 설치

```bash
pip install -r requirements.txt
```

### 8.3 환경 변수 설정

프로젝트 루트에 `.env` 파일을 만들고 네이버 API 키를 입력합니다.

```env
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

`.env` 파일은 GitHub에 올리지 않습니다.

### 8.4 데이터 수집 및 분석 실행

```bash
python update_all.py
```

### 8.5 웹서비스 실행

```bash
python app.py
```

브라우저에서 아래 주소를 열면 됩니다.

```text
http://localhost:5000
```

---

## 9. 자동 데이터 갱신

GitHub Actions를 이용해 데이터를 자동으로 갱신합니다.

워크플로 파일:

```text
.github/workflows/update_data.yml
```

자동화 흐름:

```text
정해진 시간에 GitHub Actions 실행
        ↓
Python 환경 준비
        ↓
필요 패키지 설치
        ↓
update_all.py 실행
        ↓
변경된 CSV 파일 commit
        ↓
Render 자동 배포
```

네이버 API 키는 GitHub Secrets에 저장합니다.

- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`

---

## 10. 배포

Render에서 Flask 앱을 배포합니다.

Build Command:

```text
pip install -r requirements.txt
```

Start Command:

```text
gunicorn app:app
```

GitHub 저장소에 push하면 Render가 자동 배포합니다.

---

## 11. 검색엔진 최적화

검색엔진이 사이트를 더 잘 이해하도록 다음 항목을 구성했습니다.

- `robots.txt`
- `sitemap.xml`
- `rss.xml`
- Open Graph 제목/설명
- canonical URL
- 각 페이지별 title과 meta description
- 안내 페이지 내부 링크
- 404 상태 코드 처리

검색엔진 등록:

- Google Search Console
- Naver Search Advisor

현재 제공하는 주요 안내 페이지:

- `/guide`  
  리퍼 노트북 고르는 법

- `/checklist`  
  중고·리퍼 노트북 구매 전 체크리스트

- `/about`  
  리퍼 트래커의 판단 방식

- `/used-laptop-16gb-512gb`  
  중고 노트북 16GB 512GB는 충분할까?

- `/refurb-laptop-caution`  
  리퍼 노트북 살 때 조심해야 할 점

- `/laptop-price-guide`  
  중고 노트북 가격이 적당한지 확인하는 법

---

## 12. 프로젝트를 통해 구현한 것

이 프로젝트에서는 단순 웹페이지 제작뿐 아니라 다음 과정을 함께 구현했습니다.

- 외부 API 데이터 수집
- CSV 기반 데이터 저장
- 상품명 기반 사양 추출
- 가격 데이터 분석
- 후보 상품 점수화
- Flask 웹서비스 구현
- GitHub Actions 자동화
- Render 배포
- Google / Naver 검색엔진 등록
- SEO 기본 구조 구성

---

## 13. 향후 개선 계획

### 13.1 가격 하락 알림

관심 모델을 등록하면 평균가보다 낮아졌을 때 알림을 받을 수 있도록 확장할 수 있습니다.

### 13.2 사용자 조건 저장

자주 검색하는 조건을 저장하고, 다음 방문 시 바로 확인할 수 있도록 개선할 수 있습니다.

### 13.3 데이터베이스 전환

현재는 CSV 기반이지만, 데이터가 많아지면 ClickHouse 또는 다른 데이터베이스로 전환할 수 있습니다.

### 13.4 추천 기준 고도화

다음 요소를 추가로 반영할 수 있습니다.

- CPU 세대
- 화면 크기
- 무게
- 배터리 상태
- 리퍼 등급
- 보증 기간
- 판매처 신뢰도

### 13.5 사용자 피드백 수집

추천 결과가 실제 구매 판단에 도움이 되는지 피드백을 받아 추천 기준을 개선할 수 있습니다.

---

## 14. 주의 사항

이 서비스는 리퍼·중고 노트북 구매 판단을 돕는 참고용 도구입니다.  
실제 구매 전에는 반드시 판매 페이지에서 아래 항목을 직접 확인해야 합니다.

- 제품 상태
- 배터리 상태
- 외관 등급
- 보증 기간
- 윈도우 포함 여부
- 배송비
- 반품 가능 여부

표시되는 가격과 상품 정보는 수집 시점의 데이터 기준이며, 실제 판매 페이지의 조건과 달라질 수 있습니다.

---

## 15. License

개인 학습 및 포트폴리오 목적의 프로젝트입니다.
