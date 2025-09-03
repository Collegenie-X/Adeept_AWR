#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기어 모터 4개 단계별 테스트 파일

이 파일은 L298N 모터 드라이버를 통해 연결된 4개의 기어 모터를
개별적으로 그리고 조합하여 테스트하는 기능을 제공합니다.

테스트 항목:
1. 개별 모터 동작 테스트 (앞/뒤/정지)
2. 모터 방향 확인 테스트
3. PWM 속도 제어 테스트
4. 동시 모터 제어 테스트 (직진, 후진, 좌회전, 우회전)
5. 모터 성능 벤치마크 테스트

하드웨어:
- L298N 모터 드라이버 보드
- 기어 모터 4개 (좌전, 우전, 좌후, 우후)
- 라즈베리파이 GPIO 연결

작성자: 자율주행 로봇 팀
"""

import time
import sys
import signal
from typing import Dict, List, Optional, Tuple

# GPIO 핀 설정 (L298N 연결)
# 왼쪽 앞 모터 (Left Front)
LF_MOTOR_PIN1 = 11  # IN1
LF_MOTOR_PIN2 = 12  # IN2
LF_MOTOR_PWM_PIN = 13  # ENA

# 오른쪽 앞 모터 (Right Front)
RF_MOTOR_PIN1 = 15  # IN3
RF_MOTOR_PIN2 = 16  # IN4
RF_MOTOR_PWM_PIN = 18  # ENB

# 왼쪽 뒤 모터 (Left Rear)
LR_MOTOR_PIN1 = 19  # IN1 (두 번째 L298N)
LR_MOTOR_PIN2 = 21  # IN2
LR_MOTOR_PWM_PIN = 22  # ENA

# 오른쪽 뒤 모터 (Right Rear)
RR_MOTOR_PIN1 = 23  # IN3 (두 번째 L298N)
RR_MOTOR_PIN2 = 24  # IN4
RR_MOTOR_PWM_PIN = 26  # ENB

# PWM 주파수 설정
PWM_FREQUENCY = 1000  # 1kHz

# 전역 변수
is_gpio_initialized = False
pwm_objects = {}
test_running = False


def signal_handler(signum, frame):
    """Ctrl+C 시 안전하게 종료"""
    global test_running
    print("\n⚠️ 테스트 중단 신호 감지")
    test_running = False
    cleanup_gpio_resources()
    sys.exit(0)


def initialize_gpio_for_motors() -> bool:
    """모터 제어를 위한 GPIO 초기화"""
    global is_gpio_initialized, pwm_objects

    try:
        import RPi.GPIO as GPIO

        print("🔧 GPIO 초기화 중...")
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)

        # 모든 모터 핀 설정
        motor_pins = [
            # 왼쪽 앞 모터
            (LF_MOTOR_PIN1, GPIO.OUT, "LF_PIN1"),
            (LF_MOTOR_PIN2, GPIO.OUT, "LF_PIN2"),
            (LF_MOTOR_PWM_PIN, GPIO.OUT, "LF_PWM"),
            # 오른쪽 앞 모터
            (RF_MOTOR_PIN1, GPIO.OUT, "RF_PIN1"),
            (RF_MOTOR_PIN2, GPIO.OUT, "RF_PIN2"),
            (RF_MOTOR_PWM_PIN, GPIO.OUT, "RF_PWM"),
            # 왼쪽 뒤 모터
            (LR_MOTOR_PIN1, GPIO.OUT, "LR_PIN1"),
            (LR_MOTOR_PIN2, GPIO.OUT, "LR_PIN2"),
            (LR_MOTOR_PWM_PIN, GPIO.OUT, "LR_PWM"),
            # 오른쪽 뒤 모터
            (RR_MOTOR_PIN1, GPIO.OUT, "RR_PIN1"),
            (RR_MOTOR_PIN2, GPIO.OUT, "RR_PIN2"),
            (RR_MOTOR_PWM_PIN, GPIO.OUT, "RR_PWM"),
        ]

        for pin, mode, name in motor_pins:
            GPIO.setup(pin, mode, initial=GPIO.LOW)
            print(f"  {name}: GPIO {pin} 설정 완료")

        # PWM 객체 생성
        pwm_pins = [
            LF_MOTOR_PWM_PIN,
            RF_MOTOR_PWM_PIN,
            LR_MOTOR_PWM_PIN,
            RR_MOTOR_PWM_PIN,
        ]
        pwm_names = ["LF", "RF", "LR", "RR"]

        for pin, name in zip(pwm_pins, pwm_names):
            pwm = GPIO.PWM(pin, PWM_FREQUENCY)
            pwm.start(0)  # 0% 듀티사이클로 시작
            pwm_objects[name] = pwm
            print(f"  PWM {name}: 핀 {pin}에서 {PWM_FREQUENCY}Hz로 시작")

        is_gpio_initialized = True
        print("✅ 모든 GPIO 및 PWM 초기화 완료!")
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
    global is_gpio_initialized, pwm_objects

    if is_gpio_initialized:
        print("🧹 GPIO 자원 정리 중...")

        # PWM 정지
        for name, pwm in pwm_objects.items():
            try:
                pwm.stop()
                print(f"  PWM {name} 정지")
            except:
                pass

        pwm_objects.clear()

        # GPIO 정리
        try:
            import RPi.GPIO as GPIO

            GPIO.cleanup()
            print("✅ GPIO 정리 완료")
        except:
            pass

        is_gpio_initialized = False


def control_single_motor(motor_name: str, direction: str, speed: int = 80) -> bool:
    """
    단일 모터 제어 함수

    매개변수:
    - motor_name: "LF", "RF", "LR", "RR" 중 하나
    - direction: "forward", "backward", "stop" 중 하나
    - speed: 0~100 (PWM 듀티사이클 %)
    """
    if not is_gpio_initialized:
        print(f"🔍 [시뮬레이션] {motor_name} 모터: {direction} 방향, 속도 {speed}%")
        return True

    try:
        import RPi.GPIO as GPIO

        # 모터별 핀 매핑
        motor_pins = {
            "LF": (LF_MOTOR_PIN1, LF_MOTOR_PIN2),
            "RF": (RF_MOTOR_PIN1, RF_MOTOR_PIN2),
            "LR": (LR_MOTOR_PIN1, LR_MOTOR_PIN2),
            "RR": (RR_MOTOR_PIN1, RR_MOTOR_PIN2),
        }

        if motor_name not in motor_pins:
            print(f"❌ 잘못된 모터 이름: {motor_name}")
            return False

        pin1, pin2 = motor_pins[motor_name]
        pwm = pwm_objects.get(motor_name)

        if pwm is None:
            print(f"❌ {motor_name} 모터의 PWM 객체를 찾을 수 없습니다")
            return False

        # 방향 제어
        if direction == "forward":
            GPIO.output(pin1, GPIO.HIGH)
            GPIO.output(pin2, GPIO.LOW)
            pwm.ChangeDutyCycle(speed)
            print(f"🟢 {motor_name} 모터: 전진, 속도 {speed}%")

        elif direction == "backward":
            GPIO.output(pin1, GPIO.LOW)
            GPIO.output(pin2, GPIO.HIGH)
            pwm.ChangeDutyCycle(speed)
            print(f"🔴 {motor_name} 모터: 후진, 속도 {speed}%")

        elif direction == "stop":
            GPIO.output(pin1, GPIO.LOW)
            GPIO.output(pin2, GPIO.LOW)
            pwm.ChangeDutyCycle(0)
            print(f"⏹️ {motor_name} 모터: 정지")

        else:
            print(f"❌ 잘못된 방향 명령: {direction}")
            return False

        return True

    except Exception as error:
        print(f"❌ {motor_name} 모터 제어 오류: {error}")
        return False


def stop_all_motors():
    """모든 모터 즉시 정지"""
    print("🛑 모든 모터 정지")
    for motor in ["LF", "RF", "LR", "RR"]:
        control_single_motor(motor, "stop")


def test_individual_motors():
    """개별 모터 동작 테스트"""
    print("\n🧪 === 개별 모터 동작 테스트 ===")

    motors = [
        ("LF", "왼쪽 앞"),
        ("RF", "오른쪽 앞"),
        ("LR", "왼쪽 뒤"),
        ("RR", "오른쪽 뒤"),
    ]

    for motor_code, motor_name in motors:
        if not test_running:
            break

        print(f"\n--- {motor_name} 모터 ({motor_code}) 테스트 ---")

        # 전진 테스트
        print(f"1. {motor_name} 모터 전진 (2초)")
        control_single_motor(motor_code, "forward", 70)
        time.sleep(2)

        # 정지
        control_single_motor(motor_code, "stop")
        time.sleep(0.5)

        # 후진 테스트
        print(f"2. {motor_name} 모터 후진 (2초)")
        control_single_motor(motor_code, "backward", 70)
        time.sleep(2)

        # 정지
        control_single_motor(motor_code, "stop")
        print(f"✅ {motor_name} 모터 테스트 완료")
        time.sleep(1)


def test_motor_speed_control():
    """모터 속도 제어 테스트"""
    print("\n🧪 === 모터 속도 제어 테스트 ===")

    # 왼쪽 앞 모터로 속도 테스트
    test_motor = "LF"
    print(f"{test_motor} 모터로 속도 변화 테스트")

    # 속도 단계별 테스트
    speeds = [30, 50, 70, 90, 100]

    for speed in speeds:
        if not test_running:
            break

        print(f"속도 {speed}% 테스트 (3초)")
        control_single_motor(test_motor, "forward", speed)
        time.sleep(3)

    # 정지
    control_single_motor(test_motor, "stop")
    print("✅ 속도 제어 테스트 완료")


def test_robot_movements():
    """로봇 움직임 조합 테스트"""
    print("\n🧪 === 로봇 움직임 조합 테스트 ===")

    movements = [
        (
            "직진",
            [
                ("LF", "forward"),
                ("RF", "forward"),
                ("LR", "forward"),
                ("RR", "forward"),
            ],
        ),
        (
            "후진",
            [
                ("LF", "backward"),
                ("RF", "backward"),
                ("LR", "backward"),
                ("RR", "backward"),
            ],
        ),
        (
            "좌회전",
            [
                ("LF", "backward"),
                ("RF", "forward"),
                ("LR", "backward"),
                ("RR", "forward"),
            ],
        ),
        (
            "우회전",
            [
                ("LF", "forward"),
                ("RF", "backward"),
                ("LR", "forward"),
                ("RR", "backward"),
            ],
        ),
        (
            "제자리 좌회전",
            [
                ("LF", "backward"),
                ("RF", "forward"),
                ("LR", "backward"),
                ("RR", "forward"),
            ],
        ),
        (
            "제자리 우회전",
            [
                ("LF", "forward"),
                ("RF", "backward"),
                ("LR", "forward"),
                ("RR", "backward"),
            ],
        ),
    ]

    for movement_name, motor_commands in movements:
        if not test_running:
            break

        print(f"\n--- {movement_name} 테스트 (3초) ---")

        # 모든 모터에 명령 전송
        for motor, direction in motor_commands:
            control_single_motor(motor, direction, 60)

        time.sleep(3)

        # 정지
        stop_all_motors()
        time.sleep(1)

        print(f"✅ {movement_name} 테스트 완료")


def test_motor_direction_verification():
    """모터 방향 확인 테스트 (사용자 검증 필요)"""
    print("\n🧪 === 모터 방향 확인 테스트 ===")
    print("⚠️ 이 테스트는 사용자가 직접 확인해야 합니다!")
    print("각 모터가 올바른 방향으로 회전하는지 육안으로 확인하세요.")

    motors = [
        ("LF", "왼쪽 앞"),
        ("RF", "오른쪽 앞"),
        ("LR", "왼쪽 뒤"),
        ("RR", "오른쪽 뒤"),
    ]

    for motor_code, motor_name in motors:
        if not test_running:
            break

        print(f"\n--- {motor_name} 모터 방향 확인 ---")
        input(f"Enter를 누르면 {motor_name} 모터가 전진 방향으로 3초간 동작합니다...")

        control_single_motor(motor_code, "forward", 50)
        time.sleep(3)
        control_single_motor(motor_code, "stop")

        # 사용자 확인
        while True:
            response = (
                input(f"{motor_name} 모터가 올바른 방향으로 회전했나요? (y/n): ")
                .strip()
                .lower()
            )
            if response in ["y", "yes"]:
                print(f"✅ {motor_name} 모터 방향 확인 완료")
                break
            elif response in ["n", "no"]:
                print(f"⚠️ {motor_name} 모터 배선을 확인해주세요!")
                print(f"   핀 1과 핀 2의 연결을 바꿔보세요.")
                break
            else:
                print("y 또는 n을 입력해주세요.")


def test_motor_performance_benchmark():
    """모터 성능 벤치마크 테스트"""
    print("\n🧪 === 모터 성능 벤치마크 테스트 ===")

    # 연속 동작 테스트
    print("1. 연속 동작 테스트 (30초)")
    print("   모든 모터가 30초간 연속으로 동작합니다.")
    input("Enter를 누르면 시작합니다...")

    # 모든 모터 전진
    for motor in ["LF", "RF", "LR", "RR"]:
        control_single_motor(motor, "forward", 70)

    start_time = time.time()
    while time.time() - start_time < 30 and test_running:
        elapsed = int(time.time() - start_time)
        print(f"\r연속 동작 중... {elapsed}/30초", end="", flush=True)
        time.sleep(1)

    stop_all_motors()
    print("\n✅ 연속 동작 테스트 완료")

    # 급속 방향 전환 테스트
    print("\n2. 급속 방향 전환 테스트")
    print("   모터들이 빠르게 방향을 전환합니다.")

    for i in range(10):
        if not test_running:
            break

        print(f"전환 {i+1}/10")

        # 전진
        for motor in ["LF", "RF", "LR", "RR"]:
            control_single_motor(motor, "forward", 80)
        time.sleep(0.5)

        # 후진
        for motor in ["LF", "RF", "LR", "RR"]:
            control_single_motor(motor, "backward", 80)
        time.sleep(0.5)

    stop_all_motors()
    print("✅ 급속 방향 전환 테스트 완료")


def run_interactive_motor_test():
    """대화형 모터 테스트"""
    print("\n🎮 === 대화형 모터 테스트 ===")
    print("명령어:")
    print("  w - 전진")
    print("  s - 후진")
    print("  a - 좌회전")
    print("  d - 우회전")
    print("  x - 정지")
    print("  q - 종료")

    while test_running:
        try:
            command = input("\n명령 입력: ").strip().lower()

            if command == "w":
                print("🔼 전진")
                for motor in ["LF", "RF", "LR", "RR"]:
                    control_single_motor(motor, "forward", 70)

            elif command == "s":
                print("🔽 후진")
                for motor in ["LF", "RF", "LR", "RR"]:
                    control_single_motor(motor, "backward", 70)

            elif command == "a":
                print("◀️ 좌회전")
                control_single_motor("LF", "backward", 70)
                control_single_motor("RF", "forward", 70)
                control_single_motor("LR", "backward", 70)
                control_single_motor("RR", "forward", 70)

            elif command == "d":
                print("▶️ 우회전")
                control_single_motor("LF", "forward", 70)
                control_single_motor("RF", "backward", 70)
                control_single_motor("LR", "forward", 70)
                control_single_motor("RR", "backward", 70)

            elif command == "x":
                print("⏹️ 정지")
                stop_all_motors()

            elif command == "q":
                print("👋 대화형 테스트 종료")
                break

            else:
                print("❓ 알 수 없는 명령입니다.")

        except (EOFError, KeyboardInterrupt):
            break

    stop_all_motors()


def show_test_menu():
    """테스트 메뉴 표시"""
    print("\n📋 기어 모터 테스트 메뉴:")
    print("  1 - 개별 모터 동작 테스트")
    print("  2 - 모터 속도 제어 테스트")
    print("  3 - 로봇 움직임 조합 테스트")
    print("  4 - 모터 방향 확인 테스트")
    print("  5 - 모터 성능 벤치마크")
    print("  6 - 대화형 모터 테스트")
    print("  7 - 모든 테스트 실행")
    print("  0 - 프로그램 종료")


def run_all_tests():
    """모든 테스트를 순서대로 실행"""
    print("\n🚀 모든 기어 모터 테스트 실행")
    print("=" * 50)

    try:
        test_individual_motors()
        if test_running:
            test_motor_speed_control()
        if test_running:
            test_robot_movements()
        if test_running:
            test_motor_direction_verification()
        if test_running:
            test_motor_performance_benchmark()

        print("\n🎉 모든 기어 모터 테스트 완료!")

    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 테스트 중단")
    except Exception as error:
        print(f"\n❌ 테스트 중 오류 발생: {error}")
    finally:
        stop_all_motors()


def main():
    """메인 함수"""
    global test_running

    print("🤖 기어 모터 4개 단계별 테스트 프로그램")
    print("=" * 50)

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)

    # GPIO 초기화
    if not initialize_gpio_for_motors():
        print("⚠️ GPIO 초기화 실패. 시뮬레이션 모드로 진행합니다.")

    test_running = True

    try:
        while test_running:
            show_test_menu()
            choice = input("\n선택: ").strip()

            if choice == "1":
                test_individual_motors()
            elif choice == "2":
                test_motor_speed_control()
            elif choice == "3":
                test_robot_movements()
            elif choice == "4":
                test_motor_direction_verification()
            elif choice == "5":
                test_motor_performance_benchmark()
            elif choice == "6":
                run_interactive_motor_test()
            elif choice == "7":
                run_all_tests()
            elif choice == "0":
                break
            else:
                print("❓ 잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C로 프로그램 종료")
    finally:
        test_running = False
        stop_all_motors()
        cleanup_gpio_resources()
        print("👋 기어 모터 테스트 프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
