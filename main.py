import json
import time


def mac_score(pattern, filter_matrix):
    """두 개의 같은 크기 2차원 배열을 위치별로 곱해 모두 더한다."""
    if len(pattern) != len(filter_matrix):
        raise ValueError("패턴과 필터의 행 크기가 다릅니다.")

    size = len(pattern)
    total = 0.0

    for row in range(size):
        if len(pattern[row]) != size or len(filter_matrix[row]) != size:
            raise ValueError("정사각형 행렬이 아닙니다.")

        for column in range(size):
            total += pattern[row][column] * filter_matrix[row][column]

    return total


def load_data(filename="data.json"):
    """JSON 파일을 읽어 Python 딕셔너리로 반환한다."""
    with open(filename, "r", encoding="utf-8") as file:
        return json.load(file)


def describe_data(data):
    """불러온 JSON의 기본 구조를 확인한다."""
    filters = data.get("filters", {})
    patterns = data.get("patterns", {})

    print("필터:", ", ".join(filters.keys()))
    print("패턴 수:", len(patterns))

    for name, item in patterns.items():
        matrix = item.get("input", [])
        expected = item.get("expected")
        size = len(matrix)
        print(f"{name}: {size}x{size}, expected={expected}")


def normalize_label(label):
    """입력 라벨을 Cross 또는 X로 통일한다."""
    value = str(label).strip().lower()

    if value in {"+", "cross", "십자가"}:
        return "Cross"

    if value in {"x", "×"}:
        return "X"

    raise ValueError(f"알 수 없는 라벨입니다: {label}")


def classify_pattern(data, pattern_name, epsilon=1e-9):
    """패턴을 Cross/X 필터와 비교해 판정 결과를 반환한다."""
    parts = pattern_name.split("_")
    if len(parts) < 2 or not parts[1].isdigit():
        raise ValueError(f"잘못된 패턴 이름입니다: {pattern_name}")

    size = int(parts[1])
    filter_group = data["filters"][f"size_{size}"]
    pattern_info = data["patterns"][pattern_name]
    pattern = pattern_info["input"]

    cross_score = mac_score(pattern, filter_group["cross"])
    x_score = mac_score(pattern, filter_group["x"])

    if abs(cross_score - x_score) < epsilon:
        result = "UNDECIDED"
    elif cross_score > x_score:
        result = "Cross"
    else:
        result = "X"

    expected = normalize_label(pattern_info["expected"])

    return {
        "name": pattern_name,
        "cross_score": cross_score,
        "x_score": x_score,
        "result": result,
        "expected": expected,
        "passed": result == expected
    }


def analyze_all(data):
    """모든 JSON 패턴을 분석하고 케이스별 결과를 반환한다."""
    results = []

    for pattern_name in data.get("patterns", {}):
        try:
            result = classify_pattern(data, pattern_name)
        except (KeyError, TypeError, ValueError, IndexError) as error:
            result = {
                "name": pattern_name,
                "result": "ERROR",
                "expected": "-",
                "passed": False,
                "error": str(error)
            }

        results.append(result)

    return results


def print_analysis(results):
    """분석 결과와 전체 통계를 출력한다."""
    passed = 0

    for result in results:
        if result["result"] == "ERROR":
            print(f"{result['name']}: ERROR - {result['error']}")
            continue

        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"{result['name']}: "
            f"Cross={result['cross_score']:.6f}, "
            f"X={result['x_score']:.6f}, "
            f"판정={result['result']}, "
            f"expected={result['expected']} -> {status}"
        )

        if result["passed"]:
            passed += 1

    print()
    print(f"총 테스트: {len(results)}개")
    print(f"통과: {passed}개")
    print(f"실패: {len(results) - passed}개")


def measure_performance(data, repeats=10):
    """필터 크기별 MAC 평균 시간과 연산 횟수를 측정한다."""
    print()
    print("크기       평균 시간(ms)    연산 횟수")

    for size in (3, 5, 13, 25):
        if size == 3:
            pattern = [
                [0, 1, 0],
                [1, 1, 1],
                [0, 1, 0]
            ]
            filter_matrix = pattern
        else:
            pattern = data["filters"][f"size_{size}"]["cross"]
            filter_matrix = data["filters"][f"size_{size}"]["cross"]

        start = time.perf_counter()
        for _ in range(repeats):
            mac_score(pattern, filter_matrix)
        elapsed = time.perf_counter() - start

        average_ms = elapsed / repeats * 1000
        print(f"{size}x{size:<5} {average_ms:>12.6f}    {size * size}")


def validate_data(data):
    """필터·패턴의 필수 키와 행렬 크기를 검증한다."""
    errors = []
    filters = data.get("filters")
    patterns = data.get("patterns")

    if not isinstance(filters, dict):
        errors.append("filters가 없습니다.")
        return errors

    if not isinstance(patterns, dict):
        errors.append("patterns가 없습니다.")
        return errors

    for size in (5, 13, 25):
        group = filters.get(f"size_{size}")
        if not isinstance(group, dict):
            errors.append(f"size_{size} 필터가 없습니다.")
            continue

        for label in ("cross", "x"):
            matrix = group.get(label)
            if not isinstance(matrix, list) or len(matrix) != size:
                errors.append(f"size_{size}.{label} 행 수가 잘못되었습니다.")
                continue

            if any(not isinstance(row, list) or len(row) != size for row in matrix):
                errors.append(f"size_{size}.{label} 열 수가 잘못되었습니다.")

    for name, item in patterns.items():
        parts = name.split("_")
        if len(parts) < 2 or not parts[1].isdigit():
            errors.append(f"잘못된 패턴 키: {name}")
            continue

        size = int(parts[1])
        matrix = item.get("input") if isinstance(item, dict) else None

        if not isinstance(matrix, list) or len(matrix) != size:
            errors.append(f"{name} 행 수가 잘못되었습니다.")
            continue

        if any(not isinstance(row, list) or len(row) != size for row in matrix):
            errors.append(f"{name} 열 수가 잘못되었습니다.")

        try:
            normalize_label(item.get("expected"))
        except (AttributeError, ValueError):
            errors.append(f"{name} expected 라벨이 잘못되었습니다.")

    return errors


def read_matrix(size, name):
    """사용자로부터 size x size 숫자 행렬을 입력받는다."""
    print(f"{name} ({size}줄, 공백 구분)")
    matrix = []

    for row_number in range(size):
        while True:
            try:
                values = [
                    float(value)
                    for value in input(f"{row_number + 1}행: ").split()
                ]

                if len(values) != size:
                    raise ValueError

                matrix.append(values)
                break
            except ValueError:
                print(f"입력 형식 오류: 한 줄에 숫자 {size}개를 입력하세요.")

    return matrix


def run_user_mode():
    """3 x 3 필터와 패턴을 직접 입력받아 판정한다."""
    filter_a = read_matrix(3, "필터 A")
    filter_b = read_matrix(3, "필터 B")
    pattern = read_matrix(3, "패턴")

    score_a = mac_score(pattern, filter_a)
    score_b = mac_score(pattern, filter_b)

    if abs(score_a - score_b) < 1e-9:
        result = "UNDECIDED"
    elif score_a > score_b:
        result = "A"
    else:
        result = "B"

    print(f"A 점수: {score_a}")
    print(f"B 점수: {score_b}")
    print(f"판정: {result}")


def run_json_mode():
    """data.json의 모든 패턴을 검증하고 분석한다."""
    data = load_data()
    errors = validate_data(data)

    if errors:
        print("JSON 검증 실패")
        for error in errors:
            print("-", error)
        return

    results = analyze_all(data)
    print_analysis(results)
    measure_performance(data)


def main():
    print("=== Mini NPU Simulator ===")
    print("1. 사용자 입력 (3x3)")
    print("2. data.json 분석")

    while True:
        choice = input("선택: ").strip()

        if choice == "1":
            run_user_mode()
            break
        if choice == "2":
            run_json_mode()
            break

        print("1 또는 2를 선택하세요.")


if __name__ == "__main__":
    main()
