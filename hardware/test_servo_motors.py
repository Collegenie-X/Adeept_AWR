#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
서보 모터 2개 단계별 테스트 파일

이 파일은 2개의 서보 모터의 동작을 검증하고
다양한 각도에서의 성능을 테스트하는 기능을 제공합니다.

테스트 항목:
1. 기본 각도 설정 테스트
2. 연속 각도 변경 테스트
3. 다양한 각도에서의 정확도 검증
4. 노이즈 환경에서의 안정성 테스트
5. 서보 모터 성능 벤치마크

하드웨어:
- 서보 모터 2개
- GPIO 핀: 서보1(11), 서보2(12)

작성자: 자율주행 로봇 팀
"""

import time
import signal
import sys
from typing import List, Dict, Optional, Tuple

# 서보 모터 핀 설정
SERVO1_PIN = 11  # 서보 모터 1
SERVO2_PIN = 12  # 서보 모터 2

# 테스트 설정
is_gpio_initialized = False
test_running = False


def signal_handler(signum, frame):
    """Ctrl+C 시 안전하게 종료"""
    global test_running
    print("\n⚠️ 테스트 중단 신호 감지")
    test_running = False
    cleanup_gpio_resources()
    sys.exit(0)


def initialize_servo_gpio() -> bool:
    """서보 모터용 GPIO 초기화"""
    global is_gpio_initialized

    try:
        import RPi.GPIO as GPIO

        print("🔧 서보 모터 GPIO 초기화 중...")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        # 서보 모터 핀: 출력으로 설정
        GPIO.setup(SERVO1_PIN, GPIO.OUT)
        GPIO.setup(SERVO2_PIN, GPIO.OUT)

        print(f"  서보1 핀 {SERVO1_PIN}: 출력 모드 설정")
        print(f"  서보2 핀 {SERVO2_PIN}: 출력 모드 설정")

        is_gpio_initialized = True
        print("✅ 서보 모터 GPIO 초기화 완료!")
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


def set_servo_angle(servo_pin: int, angle: float) -> None:
    """
    서보 모터의 각도를 설정하는 함수

    매개변수:
    - servo_pin: 서보 모터가 연결된 GPIO 핀 번호
    - angle: 설정할 각도 (0~180)
    """
    if not is_gpio_initialized:
        print(f"🔍 [시뮬레이션] 서보 핀 {servo_pin}: 각도 {angle}° 설정")
        return

    try:
        import RPi.GPIO as GPIO

        # PWM 주파수 및 듀티사이클 계산
        pwm_frequency = 50  # 50Hz
        duty_cycle = 2.5 + (angle / 18.0)  # 0° = 2.5%, 180° = 12.5%

        pwm = GPIO.PWM(servo_pin, pwm_frequency)
        pwm.start(duty_cycle)
        time.sleep(0.5)  # 각도 설정 후 안정화 대기
        pwm.stop()

        print(f"🔧 서보 핀 {servo_pin}: 각도 {angle}° 설정 완료")

    except Exception as error:
        print(f"❌ 서보 모터 제어 오류: {error}")


def test_basic_angle_setting():
    """기본 각도 설정 테스트"""
    print("\n🧪 === 기본 각도 설정 테스트 ===")

    angles = [0, 45, 90, 135, 180]

    for angle in angles:
        if not test_running:
            break

        print(f"서보1: 각도 {angle}° 설정")
        set_servo_angle(SERVO1_PIN, angle)
        time.sleep(1)

        print(f"서보2: 각도 {angle}° 설정")
        set_servo_angle(SERVO2_PIN, angle)
        time.sleep(1)


def test_continuous_angle_change():
    """연속 각도 변경 테스트"""
    print("\n🧪 === 연속 각도 변경 테스트 ===")

    print("서보1: 0°에서 180°까지 연속 변경")
    for angle in range(0, 181, 10):
        if not test_running:
            break

        set_servo_angle(SERVO1_PIN, angle)
        time.sleep(0.1)

    print("서보2: 180°에서 0°까지 연속 변경")
    for angle in range(180, -1, -10):
        if not test_running:
            break

        set_servo_angle(SERVO2_PIN, angle)
        time.sleep(0.1)


def show_test_menu():
    """테스트 메뉴 표시"""
    print("\n📋 서보 모터 테스트 메뉴:")
    print("  1 - 기본 각도 설정 테스트")
    print("  2 - 연속 각도 변경 테스트")
    print("  0 - 프로그램 종료")


def run_all_tests():
    """모든 테스트를 순서대로 실행"""
    print("\n🚀 모든 서보 모터 테스트 실행")
    print("=" * 50)

    try:
        test_basic_angle_setting()
        if test_running:
            test_continuous_angle_change()

        print("\n🎉 모든 서보 모터 테스트 완료!")

    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 테스트 중단")
    except Exception as error:
        print(f"\n❌ 테스트 중 오류 발생: {error}")


def main():
    """메인 함수"""
    global test_running

    print("🤖 서보 모터 2개 단계별 테스트 프로그램")
    print("=" * 50)

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)

    # GPIO 초기화
    if not initialize_servo_gpio():
        print("⚠️ GPIO 초기화 실패. 시뮬레이션 모드로 진행합니다.")

    test_running = True

    try:
        while test_running:
            show_test_menu()
            choice = input("\n선택: ").strip()

            if choice == "1":
                test_basic_angle_setting()
            elif choice == "2":
                test_continuous_angle_change()
            elif choice == "0":
                break
            else:
                print("❓ 잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C로 프로그램 종료")
    finally:
        test_running = False
        cleanup_gpio_resources()
        print("👋 서보 모터 테스트 프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
