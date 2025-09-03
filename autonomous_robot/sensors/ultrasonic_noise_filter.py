#!/usr/bin/env python3
# 파일명: ultrasonic_noise_filter.py
# 설명: 초음파 센서 오동작 방지를 위한 고급 노이즈 필터링 시스템 (고등학생 수준)
# 작성일: 2024

import time
import statistics
from typing import List, Optional, Dict, Tuple
from collections import deque

# =============================================================================
# 전역 변수 (필터링 시스템 설정)
# =============================================================================

# 측정값 저장소들
raw_distance_measurements = deque(maxlen=50)  # 원시 측정값 (최근 50개)
filtered_distance_history = deque(maxlen=20)  # 필터링된 값들 (최근 20개)
reliable_distance_history = deque(maxlen=10)  # 신뢰할 수 있는 값들 (최근 10개)

# 필터링 설정값들
MIN_VALID_DISTANCE = 2.0  # 최소 유효 거리 (cm)
MAX_VALID_DISTANCE = 300.0  # 최대 유효 거리 (cm)
MULTIPLE_SAMPLE_COUNT = 5  # 한 번에 측정할 횟수
OUTLIER_DETECTION_THRESHOLD = 3.0  # 이상값 감지 임계치 (표준편차 배수)
CONSISTENCY_CHECK_WINDOW = 3  # 일관성 확인할 윈도우 크기
MAX_CHANGE_RATE = 50.0  # 최대 변화율 (cm/초)

# 오류 감지 통계
total_measurements = 0  # 총 측정 횟수
filtered_out_count = 0  # 필터링된 측정값 개수
noise_detected_count = 0  # 노이즈 감지 횟수
last_measurement_time = 0.0  # 마지막 측정 시간

# 센서 상태 추적
sensor_reliability_score = 100.0  # 센서 신뢰도 점수 (0-100)
consecutive_bad_readings = 0  # 연속된 불량 측정 횟수
is_sensor_working_properly = True  # 센서 정상 작동 여부

# =============================================================================
# 기본 측정값 검증 함수들
# =============================================================================


def is_distance_measurement_physically_possible(distance_cm: Optional[float]) -> bool:
    """
    측정된 거리가 물리적으로 가능한 값인지 확인하는 함수

    체크 항목:
    - None이 아닌지
    - 최소/최대 거리 범위 내인지
    - 무한대나 NaN이 아닌지
    """
    if distance_cm is None:
        return False

    # 무한대나 NaN 체크
    try:
        if not (distance_cm == distance_cm):  # NaN 체크
            return False
        if distance_cm == float("inf") or distance_cm == float("-inf"):
            return False
    except:
        return False

    # 유효 범위 체크
    if distance_cm < MIN_VALID_DISTANCE or distance_cm > MAX_VALID_DISTANCE:
        return False

    return True


def check_if_measurement_is_reasonable_change(new_distance: float) -> bool:
    """
    새로운 측정값이 이전 값과 비교해서 합리적인 변화인지 확인하는 함수

    로봇이 아무리 빨라도 초음파 측정 간격(0.1초) 동안
    50cm 이상 이동하는 것은 비현실적입니다.
    """
    global last_measurement_time

    current_time = time.time()

    # 이전 측정값이 없으면 일단 허용
    if len(reliable_distance_history) == 0:
        last_measurement_time = current_time
        return True

    # 시간 간격 계산
    time_diff = current_time - last_measurement_time
    if time_diff <= 0:
        time_diff = 0.1  # 최소 간격 설정

    # 이전 값과의 차이 계산
    last_reliable_distance = reliable_distance_history[-1]
    distance_change = abs(new_distance - last_reliable_distance)

    # 변화율 계산 (cm/초)
    change_rate = distance_change / time_diff

    last_measurement_time = current_time

    # 변화율이 너무 크면 이상값으로 판단
    if change_rate > MAX_CHANGE_RATE:
        return False

    return True


def detect_outliers_using_statistical_method(measurements: List[float]) -> List[bool]:
    """
    통계적 방법으로 이상값을 감지하는 함수

    표준편차를 이용한 Z-score 방법:
    평균에서 표준편차의 3배 이상 떨어진 값들을 이상값으로 판단
    """
    if len(measurements) < 3:
        # 데이터가 부족하면 모두 정상으로 판단
        return [True] * len(measurements)

    try:
        mean_value = statistics.mean(measurements)
        std_dev = statistics.stdev(measurements)

        # 표준편차가 0에 가까우면 모든 값이 비슷한 것이므로 정상
        if std_dev < 0.1:
            return [True] * len(measurements)

        outlier_flags = []
        for measurement in measurements:
            z_score = abs(measurement - mean_value) / std_dev
            is_normal = z_score <= OUTLIER_DETECTION_THRESHOLD
            outlier_flags.append(is_normal)

        return outlier_flags

    except statistics.StatisticsError:
        # 통계 계산 오류 시 모두 정상으로 판단
        return [True] * len(measurements)


def find_most_reliable_value_from_multiple_measurements(
    measurements: List[float],
) -> Optional[float]:
    """
    여러 측정값 중에서 가장 신뢰할 수 있는 값을 찾는 함수

    방법:
    1. 이상값 제거
    2. 중간값(median) 선택 - 평균보다 노이즈에 강함
    3. 측정값들의 일관성도 함께 확인
    """
    if not measurements:
        return None

    # 유효한 측정값만 필터링
    valid_measurements = [
        m for m in measurements if is_distance_measurement_physically_possible(m)
    ]

    if not valid_measurements:
        return None

    if len(valid_measurements) == 1:
        return valid_measurements[0]

    # 이상값 감지
    outlier_flags = detect_outliers_using_statistical_method(valid_measurements)

    # 정상값들만 선별
    normal_measurements = [
        measurement
        for measurement, is_normal in zip(valid_measurements, outlier_flags)
        if is_normal
    ]

    if not normal_measurements:
        # 모든 값이 이상값이면 원래 값들의 중간값 사용
        normal_measurements = valid_measurements

    # 중간값 반환 (노이즈에 가장 강한 방법)
    return statistics.median(normal_measurements)


# =============================================================================
# 고급 필터링 함수들
# =============================================================================


def apply_moving_average_filter(new_distance: float, window_size: int = 5) -> float:
    """
    이동평균 필터를 적용하는 함수

    최근 window_size개의 측정값들의 평균을 구해서
    급격한 변화를 부드럽게 만듭니다.
    """
    # 새 값을 신뢰할 수 있는 기록에 추가
    reliable_distance_history.append(new_distance)

    # 지정된 크기만큼의 최근 값들로 평균 계산
    recent_values = list(reliable_distance_history)[-window_size:]

    if len(recent_values) >= 2:
        return statistics.mean(recent_values)
    else:
        return new_distance


def apply_kalman_like_filter(
    new_distance: float, previous_estimate: float = None
) -> float:
    """
    칼만 필터와 비슷한 방식의 예측 필터

    이전 값과 새로운 값을 가중평균하여
    측정 노이즈의 영향을 줄입니다.
    """
    if previous_estimate is None:
        # 이전 값이 없으면 새 값 그대로 사용
        return new_distance

    # 센서 신뢰도에 따라 가중치 조정
    sensor_trust = sensor_reliability_score / 100.0

    # 가중평균 계산
    # 센서가 신뢰할수록 새 값의 비중이 높아짐
    filtered_value = (sensor_trust * new_distance) + (
        (1 - sensor_trust) * previous_estimate
    )

    return filtered_value


def check_measurement_consistency_over_time() -> bool:
    """
    시간에 따른 측정값의 일관성을 확인하는 함수

    최근 몇 개의 측정값들이 서로 비슷한지 확인해서
    센서가 안정적으로 작동하는지 판단합니다.
    """
    if len(reliable_distance_history) < CONSISTENCY_CHECK_WINDOW:
        return True  # 데이터 부족 시 일관성 있다고 가정

    recent_values = list(reliable_distance_history)[-CONSISTENCY_CHECK_WINDOW:]

    try:
        # 표준편차 계산
        std_dev = statistics.stdev(recent_values)
        mean_value = statistics.mean(recent_values)

        # 변동계수 계산 (표준편차/평균)
        coefficient_of_variation = std_dev / mean_value if mean_value > 0 else 0

        # 변동계수가 0.2 이하면 일관성 있음 (20% 이내 변동)
        return coefficient_of_variation <= 0.2

    except statistics.StatisticsError:
        return True


# =============================================================================
# 센서 신뢰도 관리 함수들
# =============================================================================


def update_sensor_reliability_score(measurement_was_good: bool) -> None:
    """
    측정 결과에 따라 센서 신뢰도 점수를 업데이트하는 함수

    좋은 측정이면 점수 상승, 나쁜 측정이면 점수 하락
    """
    global sensor_reliability_score, consecutive_bad_readings, is_sensor_working_properly

    if measurement_was_good:
        # 좋은 측정 - 신뢰도 점수 상승
        sensor_reliability_score = min(100.0, sensor_reliability_score + 2.0)
        consecutive_bad_readings = 0
    else:
        # 나쁜 측정 - 신뢰도 점수 하락
        sensor_reliability_score = max(0.0, sensor_reliability_score - 5.0)
        consecutive_bad_readings += 1

    # 센서 작동 상태 판단
    if consecutive_bad_readings >= 10:
        is_sensor_working_properly = False
        print("⚠️ 초음파 센서 문제 감지! 연속 10회 이상 불량 측정")
    elif sensor_reliability_score > 80.0:
        is_sensor_working_properly = True


def get_sensor_health_status() -> Dict[str, any]:
    """
    센서의 건강 상태를 반환하는 함수
    """
    if sensor_reliability_score >= 90:
        health_status = "excellent"
    elif sensor_reliability_score >= 70:
        health_status = "good"
    elif sensor_reliability_score >= 50:
        health_status = "fair"
    elif sensor_reliability_score >= 30:
        health_status = "poor"
    else:
        health_status = "critical"

    return {
        "reliability_score": sensor_reliability_score,
        "health_status": health_status,
        "is_working_properly": is_sensor_working_properly,
        "consecutive_bad_readings": consecutive_bad_readings,
        "total_measurements": total_measurements,
        "noise_detection_rate": (noise_detected_count / max(total_measurements, 1))
        * 100,
    }


# =============================================================================
# 메인 필터링 함수들
# =============================================================================


def take_multiple_measurements_and_filter_noise() -> Optional[float]:
    """
    여러 번 측정해서 노이즈를 필터링하는 메인 함수

    이 함수가 하는 일:
    1. 5번 연속 측정
    2. 이상값 제거
    3. 중간값 선택
    4. 이전 값과의 일관성 확인
    5. 필터 적용
    """
    global total_measurements, filtered_out_count, noise_detected_count

    # 1단계: 여러 번 측정
    current_measurements = []

    for i in range(MULTIPLE_SAMPLE_COUNT):
        # 실제 초음파 센서 측정 (여기서는 시뮬레이션)
        raw_distance = measure_distance_once_with_error_handling()

        if raw_distance is not None:
            current_measurements.append(raw_distance)
            raw_distance_measurements.append(raw_distance)

        time.sleep(0.01)  # 측정 간 10ms 간격

    total_measurements += len(current_measurements)

    # 2단계: 측정값이 충분하지 않으면 실패
    if len(current_measurements) < 2:
        update_sensor_reliability_score(False)
        return None

    # 3단계: 가장 신뢰할 수 있는 값 선택
    reliable_measurement = find_most_reliable_value_from_multiple_measurements(
        current_measurements
    )

    if reliable_measurement is None:
        update_sensor_reliability_score(False)
        filtered_out_count += len(current_measurements)
        return None

    # 4단계: 합리적인 변화인지 확인
    if not check_if_measurement_is_reasonable_change(reliable_measurement):
        noise_detected_count += 1
        update_sensor_reliability_score(False)
        print(f"⚠️ 비합리적인 거리 변화 감지: {reliable_measurement:.1f}cm")
        return None

    # 5단계: 이동평균 필터 적용
    previous_estimate = (
        reliable_distance_history[-1] if reliable_distance_history else None
    )
    filtered_value = apply_kalman_like_filter(reliable_measurement, previous_estimate)
    final_value = apply_moving_average_filter(filtered_value)

    # 6단계: 일관성 확인
    is_consistent = check_measurement_consistency_over_time()

    if not is_consistent:
        print(f"⚠️ 측정값 일관성 부족, 신중하게 사용: {final_value:.1f}cm")
        update_sensor_reliability_score(False)
    else:
        update_sensor_reliability_score(True)

    # 7단계: 필터링된 기록에 추가
    filtered_distance_history.append(final_value)

    return final_value


def measure_distance_once_with_error_handling() -> Optional[float]:
    """
    한 번의 거리 측정을 수행하고 기본적인 오류 처리를 하는 함수
    (실제 초음파 센서 코드를 여기서 호출)
    """
    try:
        # 실제 초음파 센서 측정 코드 호출
        # (simple_ultrasonic_functions.py의 measure_distance_once_in_centimeters 함수 사용)
        from .simple_ultrasonic_functions import measure_distance_once_in_centimeters

        distance = measure_distance_once_in_centimeters()
        return distance

    except ImportError:
        # 테스트 환경에서는 시뮬레이션 값 반환
        import random

        # 20-100cm 범위의 시뮬레이션 값 (가끔 노이즈 추가)
        base_distance = 50.0

        # 10% 확률로 노이즈 값 생성
        if random.random() < 0.1:
            return random.uniform(1.0, 300.0)  # 노이즈
        else:
            return base_distance + random.uniform(-5.0, 5.0)  # 정상값

    except Exception as e:
        print(f"거리 측정 오류: {e}")
        return None


def get_ultra_reliable_distance_measurement() -> Dict[str, any]:
    """
    최고 신뢰도의 거리 측정을 수행하는 함수

    이 함수는 모든 필터링 기법을 종합해서
    가장 신뢰할 수 있는 측정값을 제공합니다.
    """
    # 다중 측정 및 필터링 수행
    filtered_distance = take_multiple_measurements_and_filter_noise()

    # 센서 상태 정보
    sensor_status = get_sensor_health_status()

    # 신뢰도 등급 결정
    if sensor_status["reliability_score"] >= 90:
        confidence_level = "very_high"
    elif sensor_status["reliability_score"] >= 70:
        confidence_level = "high"
    elif sensor_status["reliability_score"] >= 50:
        confidence_level = "medium"
    elif sensor_status["reliability_score"] >= 30:
        confidence_level = "low"
    else:
        confidence_level = "very_low"

    # 측정 통계
    consistency_score = check_measurement_consistency_over_time()

    result = {
        "distance_cm": filtered_distance,
        "confidence_level": confidence_level,
        "reliability_score": sensor_status["reliability_score"],
        "is_sensor_healthy": sensor_status["is_working_properly"],
        "measurement_consistency": consistency_score,
        "raw_measurements_count": len(raw_distance_measurements),
        "filtered_measurements_count": len(filtered_distance_history),
        "noise_detection_rate": sensor_status["noise_detection_rate"],
    }

    return result


# =============================================================================
# 시스템 관리 및 디버깅 함수들
# =============================================================================


def reset_all_filter_systems() -> None:
    """
    모든 필터링 시스템을 초기화하는 함수
    """
    global raw_distance_measurements, filtered_distance_history, reliable_distance_history
    global total_measurements, filtered_out_count, noise_detected_count
    global sensor_reliability_score, consecutive_bad_readings, is_sensor_working_properly
    global last_measurement_time

    raw_distance_measurements.clear()
    filtered_distance_history.clear()
    reliable_distance_history.clear()

    total_measurements = 0
    filtered_out_count = 0
    noise_detected_count = 0

    sensor_reliability_score = 100.0
    consecutive_bad_readings = 0
    is_sensor_working_properly = True
    last_measurement_time = 0.0

    print("🔄 초음파 센서 필터링 시스템 초기화 완료")


def print_detailed_filter_status() -> None:
    """
    필터링 시스템의 상세 상태를 출력하는 함수 (디버깅용)
    """
    sensor_status = get_sensor_health_status()

    print(f"\n=== 초음파 센서 필터링 시스템 상태 ===")
    print(
        f"센서 신뢰도: {sensor_status['reliability_score']:.1f}% ({sensor_status['health_status']})"
    )
    print(
        f"센서 정상 작동: {'예' if sensor_status['is_working_properly'] else '아니오'}"
    )
    print(f"연속 불량 측정: {sensor_status['consecutive_bad_readings']}회")
    print(f"총 측정 횟수: {total_measurements}회")
    print(f"필터링된 측정: {filtered_out_count}회")
    print(f"노이즈 감지율: {sensor_status['noise_detection_rate']:.1f}%")
    print(f"원시 데이터: {len(raw_distance_measurements)}개")
    print(f"필터링 데이터: {len(filtered_distance_history)}개")
    print(f"신뢰 데이터: {len(reliable_distance_history)}개")

    # 최근 측정값들 출력
    if reliable_distance_history:
        recent_values = list(reliable_distance_history)[-5:]
        print(f"최근 측정값: {[f'{v:.1f}' for v in recent_values]} cm")

    print("=" * 40)


def run_filter_performance_test(test_duration: int = 30) -> Dict[str, any]:
    """
    필터링 시스템의 성능을 테스트하는 함수
    """
    print(f"🧪 필터링 시스템 성능 테스트 시작 ({test_duration}초)")

    reset_all_filter_systems()

    start_time = time.time()
    test_results = []

    while time.time() - start_time < test_duration:
        # 필터링된 측정 수행
        result = get_ultra_reliable_distance_measurement()
        test_results.append(result)

        if len(test_results) % 10 == 0:  # 10회마다 상태 출력
            print(
                f"  측정 {len(test_results)}회: 거리={result['distance_cm']:.1f}cm, "
                f"신뢰도={result['confidence_level']}"
            )

        time.sleep(0.5)  # 0.5초 간격

    # 테스트 결과 분석
    successful_measurements = [r for r in test_results if r["distance_cm"] is not None]
    success_rate = len(successful_measurements) / len(test_results) * 100

    if successful_measurements:
        distances = [r["distance_cm"] for r in successful_measurements]
        avg_distance = statistics.mean(distances)
        std_deviation = statistics.stdev(distances) if len(distances) > 1 else 0
    else:
        avg_distance = 0
        std_deviation = 0

    final_sensor_status = get_sensor_health_status()

    performance_report = {
        "test_duration": test_duration,
        "total_attempts": len(test_results),
        "successful_measurements": len(successful_measurements),
        "success_rate_percentage": success_rate,
        "average_distance": avg_distance,
        "measurement_stability": std_deviation,
        "final_sensor_score": final_sensor_status["reliability_score"],
        "noise_detection_rate": final_sensor_status["noise_detection_rate"],
    }

    print(f"\n✅ 성능 테스트 완료!")
    print(f"성공률: {success_rate:.1f}%")
    print(f"평균 거리: {avg_distance:.1f}cm")
    print(f"측정 안정성: ±{std_deviation:.1f}cm")
    print(f"최종 센서 점수: {final_sensor_status['reliability_score']:.1f}%")

    return performance_report


# =============================================================================
# 테스트 및 시뮬레이션 함수들
# =============================================================================


def simulate_noisy_sensor_data_and_test_filtering():
    """
    노이즈가 있는 센서 데이터를 시뮬레이션하고 필터링 효과를 테스트하는 함수
    """
    print("🧪 노이즈 센서 데이터 시뮬레이션 테스트")

    import random

    # 시뮬레이션 데이터 생성
    true_distance = 50.0  # 실제 거리
    simulation_data = []

    for i in range(100):
        if random.random() < 0.8:  # 80% 정상 데이터
            noisy_distance = true_distance + random.gauss(0, 2)  # 표준편차 2cm 노이즈
        else:  # 20% 이상 데이터
            noisy_distance = random.uniform(5, 200)  # 완전히 잘못된 값

        simulation_data.append(noisy_distance)

    print(f"시뮬레이션 데이터 {len(simulation_data)}개 생성")
    print(f"실제 거리: {true_distance}cm")

    # 필터링 시스템 초기화
    reset_all_filter_systems()

    # 각 데이터에 대해 필터링 적용
    filtered_results = []

    for i, raw_value in enumerate(simulation_data):
        # 원시 값을 시스템에 주입 (실제 측정 대신)
        raw_distance_measurements.append(raw_value)

        # 필터링 수행
        result = get_ultra_reliable_distance_measurement()
        filtered_results.append(result)

        if i % 20 == 0:  # 20개마다 출력
            print(
                f"  단계 {i}: 원시값={raw_value:.1f}cm, "
                f"필터링={result['distance_cm']:.1f}cm, "
                f"신뢰도={result['confidence_level']}"
            )

    # 결과 분석
    valid_filtered = [
        r["distance_cm"] for r in filtered_results if r["distance_cm"] is not None
    ]

    if valid_filtered:
        avg_filtered = statistics.mean(valid_filtered)
        error = abs(avg_filtered - true_distance)
        print(f"\n📊 필터링 결과:")
        print(f"평균 필터링 값: {avg_filtered:.1f}cm")
        print(f"실제 거리와 오차: {error:.1f}cm")
        print(
            f"유효 측정 비율: {len(valid_filtered)}/{len(filtered_results)} ({len(valid_filtered)/len(filtered_results)*100:.1f}%)"
        )

    print_detailed_filter_status()


if __name__ == "__main__":
    # 이 파일을 직접 실행할 때만 테스트 실행
    simulate_noisy_sensor_data_and_test_filtering()
