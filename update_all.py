import subprocess
import sys
from datetime import datetime
from pathlib import Path

scripts = [
    "naver_shopping_collect.py",
    "analyze_price_history.py",
    "analyze_latest_products.py",
    "score_candidates.py",
    "show_top10_unique.py",
    "judge_buy_timing.py",
]


def run_script(script_name):
    if not Path(script_name).exists():
        print("=" * 70)
        print(f"건너뜀: {script_name}")
        print("이유: 파일이 현재 폴더에 없습니다.")
        return False

    print("=" * 70)
    print(f"실행 시작: {script_name}")
    print("=" * 70)

    result = subprocess.run([sys.executable, script_name])

    if result.returncode == 0:
        print(f"실행 완료: {script_name}")
        return True
    else:
        print(f"실행 실패: {script_name}")
        print(f"오류 코드: {result.returncode}")
        return False


print("=" * 70)
print("리퍼 트래커 전체 데이터 갱신")
print("=" * 70)
print("시작 시각:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print()

success_count = 0

for script in scripts:
    success = run_script(script)

    if success:
        success_count += 1
    else:
        print()
        print("중간에 실패한 단계가 있습니다.")
        print("위 오류 메시지를 확인한 뒤 다시 실행하세요.")
        break

    print()

print("=" * 70)
print("전체 갱신 종료")
print("=" * 70)
print(f"성공한 단계: {success_count}/{len(scripts)}")
print("종료 시각:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print()
print("웹 화면을 보려면 다음 명령을 실행하세요.")
print("py web_app.py")