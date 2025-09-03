#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
초음파 센서 (HC-SR04) 단계별 테스트 파일

이 파일은 HC-SR04 초음파 센서의 동작을 검증하고
다양한 상황에서의 성능을 테스트하는 기능을 제공합니다.

테스트 항목:
1. 기본 거리 측정 테스트
2. 연속 측정 정확도 테스트
3. 다양한 거리에서의 정확도 검증
4. 노이즈 환경에서의 안정성 테스트
5. 장애물 감지 및 경고 시스템 테스트
6. 측정 성능 벤치마크

하드웨어:
- HC-SR04 초음파 센서
- 트리거 핀: GPIO 16
- 에코 핀: GPIO 18

작성자: 자율주행 로봇 팀
"""

import time
import signal
import sys
import statistics
from typing import List, Dict, Optional, Tuple
from collections import deque

# 초음파 센서 핀 설정
TRIGGER_PIN = 16  # 트리거 핀 (소리 발사)
ECHO_PIN = 18  # 에코 핀 (소리 수신)

# 측정 설정
MAX_DISTANCE = 300  # 최대 측정 거리 (cm)
MIN_DISTANCE = 2  # 최소 측정 거리 (cm)
MEASUREMENT_TIMEOUT = 0.03  # 측정 타임아웃 (30ms)
SOUND_SPEED = 34300  # 소리 속도 (cm/s)

# 테스트 설정
is_gpio_initialized = False
test_running = False
measurement_history = deque(maxlen=100)  # 최근 100개 측정값 저장


def signal_handler(signum, frame):
    """Ctrl+C 시 안전하게 종료"""
    global test_running
    print("\n⚠️ 테스트 중단 신호 감지")
    test_running = False
    cleanup_gpio_resources()
    sys.exit(0)


def initialize_ultrasonic_gpio() -> bool:
    """초음파 센서용 GPIO 초기화"""
    global is_gpio_initialized

    try:
        import RPi.GPIO as GPIO

        print("🔧 초음파 센서 GPIO 초기화 중...")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        # 트리거 핀: 출력으로 설정, 초기값 LOW
        GPIO.setup(TRIGGER_PIN, GPIO.OUT, initial=GPIO.LOW)
        print(f"  트리거 핀 {TRIGGER_PIN}: 출력 모드 설정")

        # 에코 핀: 입력으로 설정
        GPIO.setup(ECHO_PIN, GPIO.IN)
        print(f"  에코 핀 {ECHO_PIN}: 입력 모드 설정")

        is_gpio_initialized = True
        print("✅ 초음파 센서 GPIO 초기화 완료!")
        return True

    except ImportError:
        print("⚠️ RPi.GPIO 모듈을 찾을 수 없습니다. 시뮬레이션 모드로 실행됩니다.")
        is_gpio_initialized = False
        return False

    except Exception as error:
        print(f"❌ GPIO 초기화 실패: {error}")
        return False


def cleanup_gpio_resources():
    """GPIO 자원 정리"""
    global is_gpio_initialized

    if is_gpio_initialized:
        print("🧹 GPIO 자원 정리 중...")
        try:
            import RPi.GPIO as GPIO

            GPIO.cleanup()
            print("✅ GPIO 정리 완료")
        except:
            pass
        is_gpio_initialized = False


def measure_distance_once() -> Optional[float]:
    """
    초음파를 한 번 발사하여 거리를 측정하는 함수

    반환값: 거리(cm) 또는 None(측정 실패)
    """
    if not is_gpio_initialized:
        # 시뮬레이션 모드 - 랜덤 값 반환
        import random

        base_distance = 50.0
        noise = random.uniform(-5.0, 5.0)
        simulated_distance = base_distance + noise
        return max(MIN_DISTANCE, min(MAX_DISTANCE, simulated_distance))

    try:
        import RPi.GPIO as GPIO

        # 1단계: 트리거 신호 발사 (10마이크로초)
        GPIO.output(TRIGGER_PIN, GPIO.HIGH)
        time.sleep(0.00001)  # 10μs
        GPIO.output(TRIGGER_PIN, GPIO.LOW)

        # 2단계: 에코 신호 시작 시점 감지
        pulse_start = time.time()
        timeout_start = pulse_start

        while GPIO.input(ECHO_PIN) == 0:
            pulse_start = time.time()
            if pulse_start - timeout_start > MEASUREMENT_TIMEOUT:
                return None  # 타임아웃

        # 3단계: 에코 신호 종료 시점 감지
        pulse_end = time.time()
        timeout_start = pulse_end

        while GPIO.input(ECHO_PIN) == 1:
            pulse_end = time.time()
            if pulse_end - pulse_start > MEASUREMENT_TIMEOUT:
                return None  # 타임아웃

        # 4단계: 거리 계산
        pulse_duration = pulse_end - pulse_start
        distance = (pulse_duration * SOUND_SPEED) / 2

        # 5단계: 유효 범위 검사
        if MIN_DISTANCE <= distance <= MAX_DISTANCE:
            return distance
        else:
            return None

    except Exception as error:
        print(f"⚠️ 거리 측정 오류: {error}")
        return None


def measure_distance_multiple_times(count: int = 5) -> Dict[str, any]:
    """
    여러 번 측정하여 통계적으로 안정된 결과를 반환

    매개변수:
    - count: 측정 횟수 (기본 5회)

    반환값: 측정 결과 딕셔너리
    """
    measurements = []
    failed_measurements = 0

    print(f"📏 {count}회 연속 측정 중...", end="", flush=True)

    for i in range(count):
        distance = measure_distance_once()
        if distance is not None:
            measurements.append(distance)
            print(".", end="", flush=True)
        else:
            failed_measurements += 1
            print("x", end="", flush=True)

        # 측정 간격
        time.sleep(0.01)

    print("")  # 줄바꿈

    if not measurements:
        return {
            "success": False,
            "error": "모든 측정 실패",
            "failed_count": failed_measurements,
        }

    # 통계 계산
    avg_distance = statistics.mean(measurements)
    median_distance = statistics.median(measurements)
    std_deviation = statistics.stdev(measurements) if len(measurements) > 1 else 0
    min_distance = min(measurements)
    max_distance = max(measurements)

    # 측정 신뢰도 계산 (변동계수 기반)
    coefficient_of_variation = (
        (std_deviation / avg_distance) * 100 if avg_distance > 0 else 100
    )

    if coefficient_of_variation < 5:
        reliability = "매우 높음"
    elif coefficient_of_variation < 10:
        reliability = "높음"
    elif coefficient_of_variation < 20:
        reliability = "보통"
    else:
        reliability = "낮음"

    result = {
        "success": True,
        "measurements": measurements,
        "count": len(measurements),
        "failed_count": failed_measurements,
        "average": avg_distance,
        "median": median_distance,
        "std_deviation": std_deviation,
        "min": min_distance,
        "max": max_distance,
        "range": max_distance - min_distance,
        "coefficient_of_variation": coefficient_of_variation,
        "reliability": reliability,
    }

    return result


def test_basic_distance_measurement():
    """기본 거리 측정 테스트"""
    print("\n🧪 === 기본 거리 측정 테스트 ===")

    print("단일 측정 테스트:")
    for i in range(5):
        if not test_running:
            break

        distance = measure_distance_once()
        if distance is not None:
            print(f"  측정 {i+1}: {distance:.1f}cm")
            measurement_history.append(distance)
        else:
            print(f"  측정 {i+1}: 실패")
        time.sleep(0.5)

    print("\n다중 측정 통계 테스트:")
    result = measure_distance_multiple_times(10)

    if result["success"]:
        print(f"  성공 측정: {result['count']}/10회")
        print(f"  평균 거리: {result['average']:.1f}cm")
        print(f"  중간값: {result['median']:.1f}cm")
        print(f"  표준편차: {result['std_deviation']:.2f}cm")
        print(f"  측정 범위: {result['min']:.1f}~{result['max']:.1f}cm")
        print(
            f"  신뢰도: {result['reliability']} (변동계수: {result['coefficient_of_variation']:.1f}%)"
        )
    else:
        print(f"  ❌ 측정 실패: {result['error']}")


def test_accuracy_at_different_distances():
    """다양한 거리에서의 정확도 테스트"""
    print("\n🧪 === 다양한 거리 정확도 테스트 ===")
    print("⚠️ 이 테스트는 사용자가 물체를 다양한 거리에 배치해야 합니다!")

    test_distances = [
        (10, "10cm - 매우 가까운 거리"),
        (30, "30cm - 가까운 거리"),
        (50, "50cm - 중간 거리"),
        (100, "100cm - 먼 거리"),
        (200, "200cm - 매우 먼 거리"),
    ]

    accuracy_results = []

    for expected_distance, description in test_distances:
        if not test_running:
            break

        print(f"\n--- {description} ---")
        input(f"물체를 약 {expected_distance}cm 거리에 배치하고 Enter를 누르세요...")

        result = measure_distance_multiple_times(10)

        if result["success"]:
            measured_distance = result["average"]
            error = abs(measured_distance - expected_distance)
            error_percentage = (error / expected_distance) * 100

            print(f"  예상 거리: {expected_distance}cm")
            print(f"  측정 거리: {measured_distance:.1f}cm")
            print(f"  오차: {error:.1f}cm ({error_percentage:.1f}%)")
            print(f"  신뢰도: {result['reliability']}")

            accuracy_results.append(
                {
                    "expected": expected_distance,
                    "measured": measured_distance,
                    "error": error,
                    "error_percentage": error_percentage,
                    "reliability": result["reliability"],
                }
            )
        else:
            print(f"  ❌ 측정 실패")

    # 전체 정확도 평가
    if accuracy_results:
        print(f"\n📊 전체 정확도 평가:")
        avg_error = statistics.mean([r["error"] for r in accuracy_results])
        avg_error_percentage = statistics.mean(
            [r["error_percentage"] for r in accuracy_results]
        )

        print(f"  평균 절대 오차: {avg_error:.1f}cm")
        print(f"  평균 상대 오차: {avg_error_percentage:.1f}%")

        if avg_error_percentage < 5:
            print("  ✅ 매우 정확한 센서")
        elif avg_error_percentage < 10:
            print("  ✅ 정확한 센서")
        elif avg_error_percentage < 20:
            print("  ⚠️ 보통 정확도의 센서")
        else:
            print("  ❌ 부정확한 센서 - 보정 필요")


def test_continuous_measurement_stability():
    """연속 측정 안정성 테스트"""
    print("\n🧪 === 연속 측정 안정성 테스트 ===")
    print("고정된 물체에 대해 60초간 연속 측정을 수행합니다.")

    input("물체를 고정된 위치에 배치하고 Enter를 누르세요...")

    measurements = []
    start_time = time.time()
    measurement_count = 0

    print("연속 측정 중... (Ctrl+C로 중단)")

    try:
        while time.time() - start_time < 60 and test_running:
            distance = measure_distance_once()
            if distance is not None:
                measurements.append(distance)
                measurement_count += 1

                # 10번마다 중간 결과 출력
                if measurement_count % 10 == 0:
                    recent_avg = statistics.mean(measurements[-10:])
                    print(f"  {measurement_count:3d}회: 최근 평균 {recent_avg:.1f}cm")

            time.sleep(0.1)  # 100ms 간격

    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")

    # 결과 분석
    if measurements:
        avg_distance = statistics.mean(measurements)
        std_deviation = statistics.stdev(measurements) if len(measurements) > 1 else 0
        min_distance = min(measurements)
        max_distance = max(measurements)

        print(f"\n📊 연속 측정 결과 분석:")
        print(f"  총 측정 횟수: {len(measurements)}회")
        print(f"  평균 거리: {avg_distance:.1f}cm")
        print(f"  표준편차: {std_deviation:.2f}cm")
        print(f"  최소/최대: {min_distance:.1f}~{max_distance:.1f}cm")
        print(f"  측정 범위: {max_distance - min_distance:.1f}cm")

        # 안정성 평가
        if std_deviation < 1.0:
            print("  ✅ 매우 안정적인 측정")
        elif std_deviation < 2.0:
            print("  ✅ 안정적인 측정")
        elif std_deviation < 5.0:
            print("  ⚠️ 보통 안정성")
        else:
            print("  ❌ 불안정한 측정 - 센서 점검 필요")
    else:
        print("❌ 측정 데이터가 없습니다.")


def test_obstacle_detection_and_warning():
    """장애물 감지 및 경고 시스템 테스트"""
    print("\n🧪 === 장애물 감지 및 경고 시스템 테스트 ===")

    # 거리 임계값 설정
    danger_zones = [
        (10, "매우 위험", "🔴"),
        (20, "위험", "🟠"),
        (40, "주의", "🟡"),
        (100, "안전", "🟢"),
    ]

    print("실시간 장애물 감지 테스트 (30초)")
    print("물체를 센서 앞에서 움직여보세요!")

    start_time = time.time()

    try:
        while time.time() - start_time < 30 and test_running:
            distance = measure_distance_once()

            if distance is not None:
                # 위험도 판단
                warning_level = "알 수 없음"
                warning_icon = "❓"

                for threshold, level, icon in danger_zones:
                    if distance <= threshold:
                        warning_level = level
                        warning_icon = icon
                        break

                # 실시간 출력
                print(
                    f"\r거리: {distance:6.1f}cm | {warning_icon} {warning_level}",
                    end="",
                    flush=True,
                )

                # 위험 상황 특별 처리
                if distance <= 10:
                    print("  ⚠️ 비상! 즉시 정지 필요!")
                elif distance <= 20:
                    print("  ⚠️ 장애물 회피 필요!")

            else:
                print(
                    "\r측정 실패                                    ",
                    end="",
                    flush=True,
                )

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")

    print("\n✅ 장애물 감지 테스트 완료")


def test_sensor_performance_benchmark():
    """센서 성능 벤치마크 테스트"""
    print("\n🧪 === 센서 성능 벤치마크 테스트 ===")

    # 1. 측정 속도 테스트
    print("1. 측정 속도 테스트")
    measurement_times = []

    for i in range(50):
        if not test_running:
            break

        start_time = time.time()
        distance = measure_distance_once()
        end_time = time.time()

        if distance is not None:
            measurement_time = (end_time - start_time) * 1000  # 밀리초 단위
            measurement_times.append(measurement_time)

    if measurement_times:
        avg_time = statistics.mean(measurement_times)
        max_time = max(measurement_times)
        min_time = min(measurement_times)

        print(f"  평균 측정 시간: {avg_time:.2f}ms")
        print(f"  최소/최대 시간: {min_time:.2f}~{max_time:.2f}ms")
        print(f"  초당 측정 횟수: {1000/avg_time:.1f}회")

    # 2. 신뢰성 테스트
    print("\n2. 측정 신뢰성 테스트 (100회)")
    successful_measurements = 0
    failed_measurements = 0

    for i in range(100):
        if not test_running:
            break

        distance = measure_distance_once()
        if distance is not None:
            successful_measurements += 1
        else:
            failed_measurements += 1

        if (i + 1) % 20 == 0:
            print(f"  진행: {i+1}/100")

    success_rate = (successful_measurements / 100) * 100
    print(f"  성공률: {success_rate:.1f}% ({successful_measurements}/100)")

    if success_rate >= 95:
        print("  ✅ 매우 신뢰할 수 있는 센서")
    elif success_rate >= 90:
        print("  ✅ 신뢰할 수 있는 센서")
    elif success_rate >= 80:
        print("  ⚠️ 보통 신뢰성의 센서")
    else:
        print("  ❌ 불신뢰한 센서 - 교체 필요")


def test_noise_environment_stability():
    """노이즈 환경에서의 안정성 테스트"""
    print("\n🧪 === 노이즈 환경 안정성 테스트 ===")
    print("⚠️ 이 테스트 중에는 의도적으로 방해 요소를 만들어보세요:")
    print("   - 손으로 센서 앞을 빠르게 가리기")
    print("   - 다른 물체들을 센서 앞에서 움직이기")
    print("   - 센서를 가볍게 건드리기")

    input("준비가 되면 Enter를 누르세요...")

    measurements = []
    outliers = []  # 이상값들
    stable_measurements = []  # 안정적인 측정값들

    print("30초간 노이즈 환경 테스트 중...")
    start_time = time.time()

    try:
        while time.time() - start_time < 30 and test_running:
            distance = measure_distance_once()

            if distance is not None:
                measurements.append(distance)

                # 간단한 이상값 감지 (최근 5개 측정값의 중간값과 비교)
                if len(measurements) >= 5:
                    recent_median = statistics.median(measurements[-5:])
                    if abs(distance - recent_median) > 20:  # 20cm 이상 차이
                        outliers.append(distance)
                        print(
                            f"\r이상값 감지: {distance:.1f}cm (기준: {recent_median:.1f}cm)",
                            end="",
                        )
                    else:
                        stable_measurements.append(distance)
                        print(f"\r정상 측정: {distance:.1f}cm", end="")
                else:
                    stable_measurements.append(distance)
                    print(f"\r측정: {distance:.1f}cm", end="")
            else:
                print(f"\r측정 실패", end="")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")

    # 결과 분석
    total_measurements = len(measurements)
    outlier_count = len(outliers)
    stable_count = len(stable_measurements)

    print(f"\n📊 노이즈 환경 테스트 결과:")
    print(f"  총 측정: {total_measurements}회")
    print(
        f"  안정적 측정: {stable_count}회 ({stable_count/total_measurements*100:.1f}%)"
    )
    print(
        f"  이상값 감지: {outlier_count}회 ({outlier_count/total_measurements*100:.1f}%)"
    )

    if stable_count > 0:
        stable_avg = statistics.mean(stable_measurements)
        stable_std = (
            statistics.stdev(stable_measurements) if len(stable_measurements) > 1 else 0
        )
        print(f"  안정적 측정 평균: {stable_avg:.1f}cm (±{stable_std:.2f}cm)")

    # 노이즈 저항성 평가
    if outlier_count / total_measurements < 0.1:
        print("  ✅ 노이즈에 매우 강한 센서")
    elif outlier_count / total_measurements < 0.2:
        print("  ✅ 노이즈에 강한 센서")
    elif outlier_count / total_measurements < 0.4:
        print("  ⚠️ 노이즈에 보통 저항성")
    else:
        print("  ❌ 노이즈에 취약한 센서 - 필터링 필요")


def show_test_menu():
    """테스트 메뉴 표시"""
    print("\n📋 초음파 센서 테스트 메뉴:")
    print("  1 - 기본 거리 측정 테스트")
    print("  2 - 다양한 거리 정확도 테스트")
    print("  3 - 연속 측정 안정성 테스트")
    print("  4 - 장애물 감지 및 경고 테스트")
    print("  5 - 센서 성능 벤치마크")
    print("  6 - 노이즈 환경 안정성 테스트")
    print("  7 - 모든 테스트 실행")
    print("  8 - 측정 히스토리 보기")
    print("  0 - 프로그램 종료")


def show_measurement_history():
    """측정 히스토리 표시"""
    print("\n📊 === 측정 히스토리 ===")

    if not measurement_history:
        print("저장된 측정 데이터가 없습니다.")
        return

    history_list = list(measurement_history)
    print(f"최근 {len(history_list)}개의 측정값:")

    # 최근 20개만 표시
    recent_measurements = history_list[-20:]
    for i, distance in enumerate(recent_measurements, 1):
        print(f"  {i:2d}: {distance:.1f}cm")

    # 통계 정보
    if len(history_list) > 1:
        avg_distance = statistics.mean(history_list)
        median_distance = statistics.median(history_list)
        std_deviation = statistics.stdev(history_list)
        min_distance = min(history_list)
        max_distance = max(history_list)

        print(f"\n통계 정보:")
        print(f"  총 측정 횟수: {len(history_list)}회")
        print(f"  평균: {avg_distance:.1f}cm")
        print(f"  중간값: {median_distance:.1f}cm")
        print(f"  표준편차: {std_deviation:.2f}cm")
        print(f"  범위: {min_distance:.1f}~{max_distance:.1f}cm")


def run_all_tests():
    """모든 테스트를 순서대로 실행"""
    print("\n🚀 모든 초음파 센서 테스트 실행")
    print("=" * 50)

    try:
        test_basic_distance_measurement()
        if test_running:
            test_accuracy_at_different_distances()
        if test_running:
            test_continuous_measurement_stability()
        if test_running:
            test_obstacle_detection_and_warning()
        if test_running:
            test_sensor_performance_benchmark()
        if test_running:
            test_noise_environment_stability()

        print("\n🎉 모든 초음파 센서 테스트 완료!")

    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 테스트 중단")
    except Exception as error:
        print(f"\n❌ 테스트 중 오류 발생: {error}")


def main():
    """메인 함수"""
    global test_running

    print("🤖 초음파 센서 (HC-SR04) 단계별 테스트 프로그램")
    print("=" * 50)

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)

    # GPIO 초기화
    if not initialize_ultrasonic_gpio():
        print("⚠️ GPIO 초기화 실패. 시뮬레이션 모드로 진행합니다.")

    test_running = True

    try:
        while test_running:
            show_test_menu()
            choice = input("\n선택: ").strip()

            if choice == "1":
                test_basic_distance_measurement()
            elif choice == "2":
                test_accuracy_at_different_distances()
            elif choice == "3":
                test_continuous_measurement_stability()
            elif choice == "4":
                test_obstacle_detection_and_warning()
            elif choice == "5":
                test_sensor_performance_benchmark()
            elif choice == "6":
                test_noise_environment_stability()
            elif choice == "7":
                run_all_tests()
            elif choice == "8":
                show_measurement_history()
            elif choice == "0":
                break
            else:
                print("❓ 잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C로 프로그램 종료")
    finally:
        test_running = False
        cleanup_gpio_resources()
        print("👋 초음파 센서 테스트 프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
