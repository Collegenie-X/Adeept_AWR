#!/usr/bin/env python3
# 파일명: simple_ultrasonic_functions.py
# 설명: 초음파 센서로 장애물을 감지하는 간단한 함수들 (고등학생 수준)
# 작성일: 2024

import time
from typing import Optional, List

# =============================================================================
# 전역 변수들 (초음파 센서 설정)
# =============================================================================

# 초음파 센서 핀 번호들 (HC-SR04 기준)
ULTRASONIC_TRIGGER_PIN = 16  # 트리거 핀 (소리를 보내는 핀)
ULTRASONIC_ECHO_PIN = 18  # 에코 핀 (소리를 받는 핀)

# 거리 기준값들 (단위: cm)
VERY_DANGEROUS_DISTANCE = 10  # 10cm 이하 - 즉시 멈춰야 함
DANGEROUS_DISTANCE = 20  # 20cm 이하 - 피해야 함
CAUTION_DISTANCE = 40  # 40cm 이하 - 주의해야 함
SAFE_DISTANCE = 100  # 100cm 이상 - 안전함

# 측정 설정
MAX_MEASUREMENT_DISTANCE = 300  # 최대 측정 거리 (cm)
MEASUREMENT_TIMEOUT = 0.03  # 측정 타임아웃 (30ms)

# 거리 측정 기록 저장 (노이즈 제거용)
recent_distance_measurements = []
DISTANCE_MEMORY_SIZE = 5  # 최근 5개 측정값 저장

# 초기화 상태
is_ultrasonic_initialized = False


# =============================================================================
# 기본 센서 설정 함수들
# =============================================================================


def setup_ultrasonic_sensor_pins() -> bool:
    """
    초음파 센서 핀들을 설정하는 함수
    트리거 핀은 출력으로, 에코 핀은 입력으로 설정합니다.
    """
    global is_ultrasonic_initialized

    try:
        import RPi.GPIO as GPIO

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        # 트리거 핀: 출력으로 설정하고 처음에는 LOW
        GPIO.setup(ULTRASONIC_TRIGGER_PIN, GPIO.OUT, initial=GPIO.LOW)

        # 에코 핀: 입력으로 설정
        GPIO.setup(ULTRASONIC_ECHO_PIN, GPIO.IN)

        is_ultrasonic_initialized = True
        print("✅ 초음파 센서 초기화 성공!")
        return True

    except Exception as error:
        print(f"❌ 초음파 센서 초기화 실패: {error}")
        return False


def check_if_ultrasonic_is_ready() -> bool:
    """
    초음파 센서가 사용할 준비가 되었는지 확인하는 함수
    """
    if not is_ultrasonic_initialized:
        print(
            "⚠️ 초음파 센서가 아직 초기화되지 않았습니다. setup_ultrasonic_sensor_pins() 함수를 먼저 실행하세요."
        )
        return False
    return True


# =============================================================================
# 거리 측정 함수들
# =============================================================================


def measure_distance_once_in_centimeters() -> Optional[float]:
    """
    초음파를 한 번 보내서 거리를 측정하는 함수

    작동 원리:
    1. 트리거 핀에 10마이크로초 HIGH 신호 보냄
    2. 센서가 초음파 8개를 발사
    3. 에코 핀에서 반사파가 돌아오는 시간 측정
    4. 거리 = (시간 × 소리속도) ÷ 2

    반환값: 거리(cm) 또는 None(측정 실패)
    """
    if not check_if_ultrasonic_is_ready():
        return None

    try:
        import RPi.GPIO as GPIO

        # 1단계: 트리거 신호 보내기 (10마이크로초)
        GPIO.output(ULTRASONIC_TRIGGER_PIN, GPIO.HIGH)
        time.sleep(0.00001)  # 10마이크로초 대기
        GPIO.output(ULTRASONIC_TRIGGER_PIN, GPIO.LOW)

        # 2단계: 에코 신호 시작 시점 찾기
        pulse_start_time = time.time()
        timeout_start = pulse_start_time

        while GPIO.input(ULTRASONIC_ECHO_PIN) == 0:
            pulse_start_time = time.time()
            # 타임아웃 체크 (너무 오래 기다리지 않기)
            if pulse_start_time - timeout_start > MEASUREMENT_TIMEOUT:
                return None

        # 3단계: 에코 신호 끝나는 시점 찾기
        pulse_end_time = time.time()
        timeout_start = pulse_end_time

        while GPIO.input(ULTRASONIC_ECHO_PIN) == 1:
            pulse_end_time = time.time()
            # 타임아웃 체크
            if pulse_end_time - pulse_start_time > MEASUREMENT_TIMEOUT:
                return None

        # 4단계: 거리 계산
        # 소리 속도 = 340m/s = 34000cm/s
        # 왕복 시간이므로 2로 나누기
        pulse_duration = pulse_end_time - pulse_start_time
        distance_cm = (pulse_duration * 34000) / 2

        # 5단계: 측정 범위 확인
        if 2.0 <= distance_cm <= MAX_MEASUREMENT_DISTANCE:
            return distance_cm
        else:
            return None  # 측정 범위를 벗어남

    except Exception as error:
        print(f"거리 측정 오류: {error}")
        return None


def measure_distance_multiple_times_and_get_average(
    sample_count: int = 3,
) -> Optional[float]:
    """
    여러 번 측정해서 평균값을 구하는 함수 (노이즈 제거)

    매개변수:
    - sample_count: 측정할 횟수 (기본 3번)
    """
    valid_measurements = []

    for i in range(sample_count):
        distance = measure_distance_once_in_centimeters()
        if distance is not None:
            valid_measurements.append(distance)
        time.sleep(0.01)  # 측정 간격 10ms

    if not valid_measurements:
        return None

    # 이상값 제거를 위해 중간값 사용 (3개 이상일 때)
    if len(valid_measurements) >= 3:
        valid_measurements.sort()
        return valid_measurements[len(valid_measurements) // 2]  # 중간값
    else:
        # 평균값 사용
        return sum(valid_measurements) / len(valid_measurements)


def get_stable_distance_using_history() -> Optional[float]:
    """
    최근 측정 기록을 이용해서 안정된 거리값을 구하는 함수
    급격한 변화를 부드럽게 만들어 줍니다.
    """
    global recent_distance_measurements

    # 새로운 측정값 구하기
    new_distance = measure_distance_multiple_times_and_get_average()

    if new_distance is not None:
        # 측정 기록에 추가
        recent_distance_measurements.append(new_distance)

        # 기록 크기 제한 (최근 5개만 보관)
        if len(recent_distance_measurements) > DISTANCE_MEMORY_SIZE:
            recent_distance_measurements.pop(0)  # 가장 오래된 것 제거

        # 평균값 계산 (2개 이상 있을 때)
        if len(recent_distance_measurements) >= 2:
            return sum(recent_distance_measurements) / len(recent_distance_measurements)

    return new_distance


# =============================================================================
# 위험도 분석 함수들
# =============================================================================


def analyze_danger_level_from_distance(distance_cm: Optional[float]) -> str:
    """
    측정된 거리를 보고 위험도를 분석하는 함수

    위험도 레벨:
    - "very_dangerous": 10cm 이하 - 즉시 정지해야 함
    - "dangerous": 20cm 이하 - 피해야 함
    - "caution": 40cm 이하 - 주의 필요
    - "safe": 40cm 초과 - 안전함
    - "unknown": 측정 실패
    """
    if distance_cm is None:
        return "unknown"

    if distance_cm <= VERY_DANGEROUS_DISTANCE:
        return "very_dangerous"
    elif distance_cm <= DANGEROUS_DISTANCE:
        return "dangerous"
    elif distance_cm <= CAUTION_DISTANCE:
        return "caution"
    else:
        return "safe"


def get_recommended_action_for_obstacle_avoidance(
    distance_cm: Optional[float],
) -> Dict[str, any]:
    """
    측정된 거리에 따라 추천 행동을 결정하는 함수

    이 함수는 장애물 회피를 위한 명령을 만들어 줍니다.
    """
    danger_level = analyze_danger_level_from_distance(distance_cm)

    if danger_level == "very_dangerous":
        return {
            "action": "stop_all_motors",
            "speed": 0,
            "priority": "emergency",
            "reason": f"매우 위험! 거리 {distance_cm:.1f}cm - 즉시 정지",
        }

    elif danger_level == "dangerous":
        return {
            "action": "turn_right_to_avoid_obstacle",
            "speed": 60,
            "priority": "high",
            "reason": f"위험! 거리 {distance_cm:.1f}cm - 우회전으로 회피",
        }

    elif danger_level == "caution":
        return {
            "action": "move_straight_forward_slowly",
            "speed": 50,
            "priority": "normal",
            "reason": f"주의! 거리 {distance_cm:.1f}cm - 속도 감소",
        }

    elif danger_level == "safe":
        return {
            "action": "move_straight_forward",
            "speed": 80,
            "priority": "low",
            "reason": f"안전! 거리 {distance_cm:.1f}cm - 정상 주행",
        }

    else:  # unknown
        return {
            "action": "stop_all_motors",
            "speed": 0,
            "priority": "high",
            "reason": "거리 측정 실패 - 안전을 위해 정지",
        }


# =============================================================================
# LED 제어를 위한 보조 함수들
# =============================================================================


def get_warning_led_color_based_on_distance(
    distance_cm: Optional[float],
) -> Tuple[int, int, int]:
    """
    거리에 따라 LED 색깔을 결정하는 함수

    반환값: (빨강, 초록, 파랑) 값 (0~255)
    """
    danger_level = analyze_danger_level_from_distance(distance_cm)

    if danger_level == "very_dangerous":
        return (255, 0, 0)  # 빨강 (매우 위험)
    elif danger_level == "dangerous":
        return (255, 100, 0)  # 주황 (위험)
    elif danger_level == "caution":
        return (255, 255, 0)  # 노랑 (주의)
    elif danger_level == "safe":
        return (0, 255, 0)  # 초록 (안전)
    else:  # unknown
        return (100, 100, 100)  # 회색 (알 수 없음)


def should_led_blink_based_on_danger(distance_cm: Optional[float]) -> bool:
    """
    위험도에 따라 LED가 깜빡여야 하는지 결정하는 함수
    """
    danger_level = analyze_danger_level_from_distance(distance_cm)
    return danger_level in ["very_dangerous", "dangerous"]


# =============================================================================
# 통합 함수 (다른 모듈에서 호출할 메인 함수)
# =============================================================================


def get_complete_obstacle_status_and_recommendation() -> Dict[str, any]:
    """
    장애물 감지부터 행동 추천까지 모든 것을 한 번에 처리하는 함수

    이 함수를 호출하면:
    1. 고급 노이즈 필터링으로 정확한 거리 측정
    2. 위험도를 분석하고
    3. 추천 행동을 결정하고
    4. LED 색깔도 정해줍니다
    """
    # 고급 노이즈 필터링을 사용한 초정밀 거리 측정
    try:
        from .ultrasonic_noise_filter import get_ultra_reliable_distance_measurement

        # 노이즈 필터링된 측정 결과
        filter_result = get_ultra_reliable_distance_measurement()
        current_distance = filter_result["distance_cm"]
        measurement_confidence = filter_result["confidence_level"]
        sensor_health = filter_result["is_sensor_healthy"]

    except ImportError:
        # 노이즈 필터 모듈이 없으면 기본 방법 사용
        current_distance = get_stable_distance_using_history()
        measurement_confidence = "medium"
        sensor_health = True

    # 위험도 분석
    danger_level = analyze_danger_level_from_distance(current_distance)

    # 센서 상태에 따른 위험도 조정
    if not sensor_health and danger_level != "unknown":
        print("⚠️ 초음파 센서 상태 불량 - 보수적 판단 적용")
        # 센서가 불안정하면 더 보수적으로 판단
        if danger_level == "safe":
            danger_level = "caution"
        elif danger_level == "caution":
            danger_level = "dangerous"

    # 추천 행동 결정
    recommended_action = get_recommended_action_for_obstacle_avoidance(current_distance)

    # LED 색깔 결정
    led_color = get_warning_led_color_based_on_distance(current_distance)
    should_blink = should_led_blink_based_on_danger(current_distance)

    # 모든 정보를 하나로 합치기
    complete_status = {
        "distance_cm": current_distance,
        "danger_level": danger_level,
        "recommended_action": recommended_action["action"],
        "recommended_speed": recommended_action["speed"],
        "priority": recommended_action["priority"],
        "reason": recommended_action["reason"],
        "led_color": led_color,
        "led_should_blink": should_blink,
        "measurement_history_count": len(recent_distance_measurements),
        # 노이즈 필터링 관련 정보 추가
        "measurement_confidence": measurement_confidence,
        "sensor_health": sensor_health,
        "noise_filtered": True,
    }

    return complete_status


# =============================================================================
# 모니터링 및 디버깅 함수들
# =============================================================================


def print_ultrasonic_status_for_debugging():
    """
    현재 초음파 센서 상태를 출력하는 디버깅 함수
    """
    status = get_complete_obstacle_status_and_recommendation()

    print(f"\n=== 초음파 센서 상태 ===")
    print(
        f"거리: {status['distance_cm']:.1f}cm"
        if status["distance_cm"]
        else "거리: 측정 실패"
    )
    print(f"위험도: {status['danger_level']}")
    print(f"추천 행동: {status['recommended_action']}")
    print(f"추천 속도: {status['recommended_speed']}%")
    print(f"우선순위: {status['priority']}")
    print(f"이유: {status['reason']}")
    print(f"LED 색깔: RGB{status['led_color']}")
    print(f"LED 깜빡임: {'예' if status['led_should_blink'] else '아니오'}")
    print(f"측정 기록 개수: {status['measurement_history_count']}개")
    print("=" * 25)


def continuous_distance_monitoring_for_testing(duration_seconds: int = 10):
    """
    지정된 시간 동안 계속 거리를 측정하고 출력하는 테스트 함수
    """
    print(f"🧪 {duration_seconds}초 동안 연속 거리 측정 시작")

    if not setup_ultrasonic_sensor_pins():
        print("❌ 초음파 센서 초기화 실패로 테스트 중단")
        return

    start_time = time.time()
    measurement_count = 0

    while time.time() - start_time < duration_seconds:
        status = get_complete_obstacle_status_and_recommendation()
        measurement_count += 1

        if status["distance_cm"]:
            print(
                f"측정 {measurement_count}: {status['distance_cm']:.1f}cm | {status['danger_level']} | {status['recommended_action']}"
            )
        else:
            print(f"측정 {measurement_count}: 실패")

        time.sleep(0.2)  # 0.2초마다 측정

    print(f"✅ 연속 측정 완료 (총 {measurement_count}회)")


def reset_ultrasonic_memory():
    """
    초음파 센서 측정 기록을 모두 지우는 함수
    """
    global recent_distance_measurements
    recent_distance_measurements = []
    print("🔄 초음파 센서 메모리 초기화 완료")


def cleanup_ultrasonic_resources():
    """
    초음파 센서 관련 자원을 정리하는 함수
    """
    global is_ultrasonic_initialized

    if is_ultrasonic_initialized:
        try:
            import RPi.GPIO as GPIO

            GPIO.cleanup()
            print("✅ 초음파 센서 자원 정리 완료")
        except:
            print("⚠️ GPIO 정리 중 오류 발생")

        is_ultrasonic_initialized = False


if __name__ == "__main__":
    # 이 파일을 직접 실행할 때만 테스트 실행
    continuous_distance_monitoring_for_testing(5)
