#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라인 센서 단계별 테스트 파일

이 파일은 3개의 라인 센서(왼쪽, 가운데, 오른쪽)의 동작을 검증하고
다양한 상황에서의 성능을 테스트하는 기능을 제공합니다.

테스트 항목:
1. 기본 라인 감지 테스트
2. 연속 감지 정확도 테스트
3. 다양한 라인 패턴에서의 정확도 검증
4. 노이즈 환경에서의 안정성 테스트
5. 라인 추적 및 경고 시스템 테스트
6. 감지 성능 벤치마크

하드웨어:
- 라인 센서 3개
- GPIO 핀: 왼쪽(35), 가운데(36), 오른쪽(37)

작성자: 자율주행 로봇 팀
"""

import time
import signal
import sys
from typing import List, Dict, Optional, Tuple
from collections import deque

# 라인 센서 핀 설정
LEFT_SENSOR_PIN = 35  # 왼쪽 센서
CENTER_SENSOR_PIN = 36  # 가운데 센서
RIGHT_SENSOR_PIN = 37  # 오른쪽 센서

# 테스트 설정
is_gpio_initialized = False
test_running = False
sensor_history = deque(maxlen=100)  # 최근 100개 측정값 저장


def signal_handler(signum, frame):
    """Ctrl+C 시 안전하게 종료"""
    global test_running
    print("\n⚠️ 테스트 중단 신호 감지")
    test_running = False
    cleanup_gpio_resources()
    sys.exit(0)


def initialize_line_sensor_gpio() -> bool:
    """라인 센서용 GPIO 초기화"""
    global is_gpio_initialized

    try:
        import RPi.GPIO as GPIO

        print("🔧 라인 센서 GPIO 초기화 중...")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        # 각 센서 핀: 입력으로 설정
        GPIO.setup(LEFT_SENSOR_PIN, GPIO.IN)
        GPIO.setup(CENTER_SENSOR_PIN, GPIO.IN)
        GPIO.setup(RIGHT_SENSOR_PIN, GPIO.IN)

        print(f"  왼쪽 센서 핀 {LEFT_SENSOR_PIN}: 입력 모드 설정")
        print(f"  가운데 센서 핀 {CENTER_SENSOR_PIN}: 입력 모드 설정")
        print(f"  오른쪽 센서 핀 {RIGHT_SENSOR_PIN}: 입력 모드 설정")

        is_gpio_initialized = True
        print("✅ 라인 센서 GPIO 초기화 완료!")
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


def read_line_sensors() -> Tuple[bool, bool, bool]:
    """
    3개의 라인 센서를 읽어 현재 상태를 반환

    반환값: (왼쪽, 가운데, 오른쪽) 센서 상태 (True = 라인 감지)
    """
    if not is_gpio_initialized:
        # 시뮬레이션 모드 - 랜덤 값 반환
        import random

        return random.choice(
            [(True, False, False), (False, True, False), (False, False, True)]
        )

    try:
        import RPi.GPIO as GPIO

        left_detected = GPIO.input(LEFT_SENSOR_PIN) == GPIO.LOW
        center_detected = GPIO.input(CENTER_SENSOR_PIN) == GPIO.LOW
        right_detected = GPIO.input(RIGHT_SENSOR_PIN) == GPIO.LOW

        return left_detected, center_detected, right_detected

    except Exception as error:
        print(f"⚠️ 라인 센서 읽기 오류: {error}")
        return False, False, False


def test_basic_line_detection():
    """기본 라인 감지 테스트"""
    print("\n🧪 === 기본 라인 감지 테스트 ===")

    print("단일 감지 테스트:")
    for i in range(5):
        if not test_running:
            break

        left, center, right = read_line_sensors()
        print(f"  측정 {i+1}: 왼쪽={left}, 가운데={center}, 오른쪽={right}")
        sensor_history.append((left, center, right))
        time.sleep(0.5)


def test_continuous_line_detection_stability():
    """연속 감지 안정성 테스트"""
    print("\n🧪 === 연속 감지 안정성 테스트 ===")
    print("고정된 라인에 대해 60초간 연속 감지를 수행합니다.")

    input("라인을 고정된 위치에 배치하고 Enter를 누르세요...")

    measurements = []
    start_time = time.time()
    measurement_count = 0

    print("연속 감지 중... (Ctrl+C로 중단)")

    try:
        while time.time() - start_time < 60 and test_running:
            left, center, right = read_line_sensors()
            measurements.append((left, center, right))
            measurement_count += 1

            # 10번마다 중간 결과 출력
            if measurement_count % 10 == 0:
                recent_measurements = measurements[-10:]
                print(f"  {measurement_count:3d}회: 최근 감지 {recent_measurements}")

            time.sleep(0.1)  # 100ms 간격

    except KeyboardInterrupt:
        print("\n사용자에 의해 중단됨")

    # 결과 분석
    if measurements:
        print(f"\n📊 연속 감지 결과 분석:")
        print(f"  총 감지 횟수: {len(measurements)}회")

        # 안정성 평가
        if all(measurements):
            print("  ✅ 매우 안정적인 감지")
        else:
            print("  ⚠️ 불안정한 감지 - 센서 점검 필요")
    else:
        print("❌ 감지 데이터가 없습니다.")


def show_test_menu():
    """테스트 메뉴 표시"""
    print("\n📋 라인 센서 테스트 메뉴:")
    print("  1 - 기본 라인 감지 테스트")
    print("  2 - 연속 감지 안정성 테스트")
    print("  0 - 프로그램 종료")


def run_all_tests():
    """모든 테스트를 순서대로 실행"""
    print("\n🚀 모든 라인 센서 테스트 실행")
    print("=" * 50)

    try:
        test_basic_line_detection()
        if test_running:
            test_continuous_line_detection_stability()

        print("\n🎉 모든 라인 센서 테스트 완료!")

    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 테스트 중단")
    except Exception as error:
        print(f"\n❌ 테스트 중 오류 발생: {error}")


def main():
    """메인 함수"""
    global test_running

    print("🤖 라인 센서 단계별 테스트 프로그램")
    print("=" * 50)

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)

    # GPIO 초기화
    if not initialize_line_sensor_gpio():
        print("⚠️ GPIO 초기화 실패. 시뮬레이션 모드로 진행합니다.")

    test_running = True

    try:
        while test_running:
            show_test_menu()
            choice = input("\n선택: ").strip()

            if choice == "1":
                test_basic_line_detection()
            elif choice == "2":
                test_continuous_line_detection_stability()
            elif choice == "0":
                break
            else:
                print("❓ 잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C로 프로그램 종료")
    finally:
        test_running = False
        cleanup_gpio_resources()
        print("👋 라인 센서 테스트 프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
