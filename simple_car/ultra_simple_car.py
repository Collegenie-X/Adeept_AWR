#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
초간단 자율 주행차 - 키보드 조절 버전 (고등학생용)
Ultra Simple Autonomous Car - Keyboard Control Version

기능:
1. 라인 센서로 검은 선 따라가기
2. 초음파 센서로 장애물 피하기
3. 키보드로 실시간 속도 조절
"""

import time
import threading
import os
import sys
import select
import termios
import tty

# 하드웨어 가져오기
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hardware.test_line_sensors import LineSensorController
    from hardware.test_gear_motors import GearMotorController
    from hardware.test_ultrasonic_sensor import UltrasonicSensor

    print("Using real hardware")
    SIMULATION = False
except ImportError:
    print("Simulation mode")
    SIMULATION = True

# 설정값 (키보드로 실시간 조절 가능)
FORWARD_SPEED = 70  # 직진 속도
LOW_TURN_SPEED = 40  # 약한 회전 속도
HIGH_TURN_SPEED = 80  # 강한 회전 속도
SAFE_DISTANCE = 15  # 장애물 안전 거리 (cm)
AVOID_TIME = 0.6  # 회피 동작 시간 (초)

MOTOR_SLEEP_TIME = 0.3

# 하드웨어 객체들
line_sensor = None
motor = None
ultrasonic = None

# 도로폭 기반 라인 추적을 위한 방향 상태 추적
last_turn_direction = "none"  # "left", "right", "none"
turn_recovery_count = 0  # 턴 후 복구 카운터

# 키보드 제어를 위한 전역 변수
autonomous_mode = False  # 자동 주행 모드 (False: 수동, True: 자동)
running = True  # 프로그램 실행 상태
manual_control_active = False  # 수동 제어 활성 상태

# 실시간 조절 값들 (키보드로 변경 가능)
current_forward_speed = FORWARD_SPEED
current_low_turn_speed = LOW_TURN_SPEED
current_high_turn_speed = HIGH_TURN_SPEED
current_safe_distance = SAFE_DISTANCE
current_avoid_time = int(AVOID_TIME * 10)  # 0.1초 단위


def setup():
    """하드웨어 준비"""
    global line_sensor, motor, ultrasonic

    if not SIMULATION:
        try:
            line_sensor = LineSensorController()
            motor = GearMotorController()
            ultrasonic = UltrasonicSensor()
            print("Hardware ready")
            return True
        except Exception as e:
            print(f"Hardware error: {e}")
            return False
    else:
        print("Simulation ready")
        return True


def read_line():
    """
    도로폭 기반 라인 센서 읽기
    - left: 왼쪽 경계선 감지 (오른쪽으로 이동 필요)
    - center: 중앙 경계선 감지 (위험! 반대 방향으로 회피)
    - right: 오른쪽 경계선 감지 (왼쪽으로 이동 필요)
    - none: 경계선 없음 (도로 중앙, 직진)
    """
    if line_sensor:
        line_info = line_sensor.get_line_position()

        # 개별 센서 상태 확인 (예상: left_sensor, center_sensor, right_sensor)
        if (
            hasattr(line_info, "left_sensor")
            and hasattr(line_info, "center_sensor")
            and hasattr(line_info, "right_sensor")
        ):
            left_detected = line_info.left_sensor
            center_detected = line_info.center_sensor
            right_detected = line_info.right_sensor
        else:
            # 기존 position 기반 방식으로 fallback
            position = line_info.get("position")
            if position is None:
                return "none"
            elif position < -0.3:
                left_detected, center_detected, right_detected = True, False, False
            elif position > 0.3:
                left_detected, center_detected, right_detected = False, False, True
            else:
                left_detected, center_detected, right_detected = False, True, False

        # 도로폭 기반 판단 로직
        if left_detected and not center_detected and not right_detected:
            return "left"  # 왼쪽 경계선만 감지
        elif not left_detected and center_detected and not right_detected:
            return "center"  # 중앙 경계선 감지 (위험!)
        elif not left_detected and not center_detected and right_detected:
            return "right"  # 오른쪽 경계선만 감지
        elif not left_detected and not center_detected and not right_detected:
            return "none"  # 경계선 없음 (도로 중앙)
        else:
            # 복수 센서 감지 시 우선순위: center > left > right
            if center_detected:
                return "center"
            elif left_detected:
                return "left"
            else:
                return "right"
    else:
        # 시뮬레이션
        import random

        return random.choice(["left", "center", "right", "none"])


def get_single_key():
    """Enter 키 없이 단일 키 입력 받기"""
    try:
        # 터미널 설정 저장
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            # raw 모드로 설정 (Enter 키 없이 바로 반응)
            tty.setcbreak(sys.stdin.fileno())

            # 키 입력 대기 (논블로킹)
            if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
                char = sys.stdin.read(1)
                return char.lower()
            else:
                return None
        finally:
            # 터미널 설정 복원
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    except:
        return None


def get_line_input():
    """Enter 키가 필요한 라인 입력 (s 명령용)"""
    try:
        return input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        return None


def print_control_menu():
    """키보드 제어 메뉴 출력"""
    print("\n" + "=" * 70)
    print("🎮 키보드 제어 메뉴 및 현재 설정")
    print("=" * 70)

    # 현재 설정값 상세 정보
    print("📊 현재 속도 및 설정 정보:")
    print(
        f"  🚗 전진 속도:     {current_forward_speed:3d}% (범위: 10-100%, 기본값: {FORWARD_SPEED}%)"
    )
    print(
        f"  🔄 약한 회전:     {current_low_turn_speed:3d}% (범위: 10-100%, 기본값: {LOW_TURN_SPEED}%)"
    )
    print(
        f"  ⚡ 강한 회전:     {current_high_turn_speed:3d}% (범위: 10-100%, 기본값: {HIGH_TURN_SPEED}%)"
    )
    print(
        f"  🛡️ 안전 거리:     {current_safe_distance:3d}cm (범위: 5-50cm, 기본값: {SAFE_DISTANCE}cm)"
    )
    print(
        f"  ⏱️ 회피 시간:     {current_avoid_time/10:4.1f}s (범위: 0.1-2.0s, 기본값: {AVOID_TIME:.1f}s)"
    )

    print("\n🎯 속도 설정 용도:")
    print("  • 전진 속도: 직선 주행 시 사용")
    print("  • 약한 회전: 라인 센서 center 감지 시 미세 조정")
    print("  • 강한 회전: 라인 센서 left/right 감지 시 빠른 회전")
    print("  • 안전 거리: 장애물 감지 최소 거리")
    print("  • 회피 시간: 장애물 회피 동작 지속 시간")

    print("\n🚦 주행 제어:")
    print("  s + Enter: 자동 주행 시작 (안전 확인)")
    print("  p: 즉시 정지 (모든 동작 중단, 수동 모드로 전환)")
    print("  q: 프로그램 종료")

    print(f"\n🎮 수동 조작 (정지 상태에서만, {MOTOR_SLEEP_TIME}초 동작 후 자동 정지):")
    print("  w: 전진 (현재 전진 속도로)")
    print("  a: 좌회전 (현재 강한 회전 속도로)")
    print("  d: 우회전 (현재 강한 회전 속도로)")

    print("\n⚙️ 속도 조절 (실시간, Enter 키 불필요):")
    print("  1,2: 전진 속도 -10%/+10%")
    print("  3,4: 약한 회전 속도 -10%/+10%")
    print("  5,6: 강한 회전 속도 -10%/+10%")
    print("  7,8: 안전 거리 -5cm/+5cm")
    print("  9,0: 회피 시간 -0.1s/+0.1s")

    print("\n💡 팁:")
    print("  • 모든 키는 Enter 없이 즉시 반응 (s 제외)")
    print("  • 자동 주행 중에도 속도 실시간 조절 가능")
    print(
        f"  • 수동 조작은 {MOTOR_SLEEP_TIME}초 동작 후 자동 정지 (속도/각도 테스트용)"
    )
    print("  • p 키로 언제든 모든 동작 즉시 중단")
    print("  • q 키 또는 Ctrl+C로 설정값 표시 후 안전 종료")
    print("  h: 이 메뉴 다시 보기")
    print("=" * 70)


def handle_keyboard_input():
    """키보드 입력 처리 (Enter 키 없이 바로 반응)"""
    global current_forward_speed, current_low_turn_speed, current_high_turn_speed
    global current_safe_distance, current_avoid_time
    global autonomous_mode, manual_control_active, running

    print("\n🎮 키보드 제어 활성화 - 키를 누르면 바로 반응합니다")
    print("'s' 명령만 Enter 키 필요, 나머지는 키만 누르면 즉시 반응")
    print("Ctrl+C로 안전하게 종료 가능")

    while running:
        try:
            # 현재 상태를 한 줄로 표시 (스크린 클리어 없이)
            if autonomous_mode:
                status = "🚗 자동"
            elif manual_control_active:
                status = "🎮 수동"
            else:
                status = "⏸️ 대기"

            print(
                f"\r상태: {status} | h=도움말, s=자동시작, p=정지, q=종료",
                end="",
                flush=True,
            )

            # 단일 키 입력 받기 (Enter 키 없이)
            key = get_single_key()

            if key is None:
                continue

            # 키 처리 (즉시 반응)
            if key == "h":
                print("\n")  # 새 줄로 이동
                print_control_menu()
            elif key == "q":
                print("\n🚪 프로그램 종료 요청")
                show_final_settings()
                running = False
                break
            elif key == "s":
                print(
                    f"\n's' 입력됨. 자동 주행을 시작하려면 Enter를 누르세요: ",
                    end="",
                    flush=True,
                )
                confirm = get_line_input()
                if confirm == "":  # Enter만 누른 경우
                    if not autonomous_mode:
                        print("🚗 자동 주행 시작")
                        autonomous_mode = True
                        manual_control_active = False
                    else:
                        print("이미 자동 주행 중")
                else:
                    print("취소됨")
            elif key == "p":
                print("\n🛑 즉시 정지 - 모든 동작 중단")
                # 모든 모터 즉시 정지
                emergency_stop()
                # 모드 전환
                if autonomous_mode:
                    autonomous_mode = False
                    manual_control_active = True
                    print("자동 모드 → 수동 모드로 전환")
                else:
                    manual_control_active = True
                    print("수동 모드에서 모든 동작 정지")
            elif key in ["w", "a", "d"] and not autonomous_mode:
                manual_control_active = True
                if key == "w":
                    print("\n🔼 수동 전진")
                    manual_forward()
                elif key == "a":
                    print("\n◀️ 수동 좌회전")
                    manual_turn_left()
                elif key == "d":
                    print("\n▶️ 수동 우회전")
                    manual_turn_right()
            # 속도 조절 키들 (즉시 반응)
            elif key == "1":
                current_forward_speed = max(10, current_forward_speed - 10)
                print(f"\n✓ 전진 속도: {current_forward_speed}%")
            elif key == "2":
                current_forward_speed = min(100, current_forward_speed + 10)
                print(f"\n✓ 전진 속도: {current_forward_speed}%")
            elif key == "3":
                current_low_turn_speed = max(10, current_low_turn_speed - 10)
                print(f"\n✓ 약한 회전 속도: {current_low_turn_speed}%")
            elif key == "4":
                current_low_turn_speed = min(100, current_low_turn_speed + 10)
                print(f"\n✓ 약한 회전 속도: {current_low_turn_speed}%")
            elif key == "5":
                current_high_turn_speed = max(10, current_high_turn_speed - 10)
                print(f"\n✓ 강한 회전 속도: {current_high_turn_speed}%")
            elif key == "6":
                current_high_turn_speed = min(100, current_high_turn_speed + 10)
                print(f"\n✓ 강한 회전 속도: {current_high_turn_speed}%")
            elif key == "7":
                current_safe_distance = max(5, current_safe_distance - 5)
                print(f"\n✓ 안전 거리: {current_safe_distance}cm")
            elif key == "8":
                current_safe_distance = min(50, current_safe_distance + 5)
                print(f"\n✓ 안전 거리: {current_safe_distance}cm")
            elif key == "9":
                current_avoid_time = max(1, current_avoid_time - 1)
                print(f"\n✓ 회피 시간: {current_avoid_time/10:.1f}s")
            elif key == "0":
                current_avoid_time = min(20, current_avoid_time + 1)
                print(f"\n✓ 회피 시간: {current_avoid_time/10:.1f}s")
            elif key == "\x03":  # Ctrl+C 감지
                print("\nCtrl+C 감지 - 안전 종료 중...")
                running = False
                break
            elif key and key.isprintable():
                print(f"\n❌ 알 수 없는 명령: '{key}'. 'h' 키로 도움말 확인")

        except KeyboardInterrupt:
            print("\nCtrl+C 감지 - 안전 종료 중...")
            running = False
            break
        except Exception as e:
            print(f"\n오류: {e}")
            time.sleep(0.1)


def read_distance():
    """앞의 거리 읽기"""
    if ultrasonic:
        distance = ultrasonic.measure_distance()
        print(f"Distance: {distance}")
        return distance if distance else 999
    else:
        # 시뮬레이션
        import random

        if random.random() < 0.1:  # 10% obstacle chance
            distance = random.randint(5, current_safe_distance - 1)
            print(f"Sim obstacle distance: {distance}cm")
            return distance
        else:
            distance = random.randint(current_safe_distance + 10, 100)
            print(f"Sim safe distance: {distance}cm")
            return distance


def stop():
    """정지"""
    if motor:
        motor.motor_stop()
        print("Stop")
    else:
        print("Simulation: Stop")


def go_forward():
    """직진 (현재 설정값 사용)"""
    if motor:
        motor.set_motor_speed("A", current_forward_speed)  # 오른쪽
        motor.set_motor_speed("B", current_forward_speed)  # 왼쪽
        print(f"Forward at {current_forward_speed}%")
    else:
        print(f"Simulation: Forward at {current_forward_speed}%")


def turn_left():
    """좌회전 (오른쪽 경계선에서 벗어나기) - 현재 설정값 사용"""
    global last_turn_direction, turn_recovery_count

    if motor:
        motor.set_motor_speed("A", current_high_turn_speed)  # 오른쪽: 앞으로
        motor.set_motor_speed("B", -current_low_turn_speed)  # 왼쪽: 뒤로
        print(f"Turn left (R:{current_high_turn_speed}%, L:-{current_low_turn_speed}%)")
    else:
        print(
            f"Simulation: Turn left (R:{current_high_turn_speed}%, L:-{current_low_turn_speed}%)"
        )

    last_turn_direction = "left"
    turn_recovery_count = 0


def turn_right():
    """우회전 (왼쪽 경계선에서 벗어나기) - 현재 설정값 사용"""
    global last_turn_direction, turn_recovery_count

    if motor:
        motor.set_motor_speed("A", -current_low_turn_speed)  # 오른쪽: 뒤로
        motor.set_motor_speed("B", current_high_turn_speed)  # 왼쪽: 앞으로
        print(
            f"Turn right (R:-{current_low_turn_speed}%, L:{current_high_turn_speed}%)"
        )
    else:
        print(
            f"Simulation: Turn right (R:-{current_low_turn_speed}%, L:{current_high_turn_speed}%)"
        )

    last_turn_direction = "right"
    turn_recovery_count = 0


def slight_left():
    """약한 좌회전 (중앙선 회피용) - 현재 설정값 사용"""
    if motor:
        motor.set_motor_speed("A", current_forward_speed)  # 오른쪽: 정상 속도
        motor.set_motor_speed("B", current_low_turn_speed)  # 왼쪽: 낮은 속도
        print(f"Slight left (R:{current_forward_speed}%, L:{current_low_turn_speed}%)")
    else:
        print(
            f"Simulation: Slight left (R:{current_forward_speed}%, L:{current_low_turn_speed}%)"
        )


def slight_right():
    """약한 우회전 (중앙선 회피용) - 현재 설정값 사용"""
    if motor:
        motor.set_motor_speed("A", current_low_turn_speed)  # 오른쪽: 낮은 속도
        motor.set_motor_speed("B", current_forward_speed)  # 왼쪽: 정상 속도
        print(f"Slight right (R:{current_low_turn_speed}%, L:{current_forward_speed}%)")
    else:
        print(
            f"Simulation: Slight right (R:{current_low_turn_speed}%, L:{current_forward_speed}%)"
        )


def manual_forward():
    """수동 전진 (1초 동작 후 자동 정지)"""
    if motor:
        motor.set_motor_speed("A", current_forward_speed)
        motor.set_motor_speed("B", current_forward_speed)
        print(f"🔼 전진 {current_forward_speed}% - {MOTOR_SLEEP_TIME}초 후 자동 정지")
        time.sleep(MOTOR_SLEEP_TIME)
        motor.motor_stop()
        print("⏹️ 전진 정지")
    else:
        print(
            f"Simulation: Forward at {current_forward_speed}% for {MOTOR_SLEEP_TIME} second"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        print("Simulation: Forward stopped")


def manual_backward():
    """수동 후진 (1초 동작 후 자동 정지)"""
    if motor:
        motor.set_motor_speed("A", -current_forward_speed)
        motor.set_motor_speed("B", -current_forward_speed)
        print(f"🔽 후진 {current_forward_speed}% - {MOTOR_SLEEP_TIME}초 후 자동 정지")
        time.sleep(MOTOR_SLEEP_TIME)
        motor.motor_stop()
        print("⏹️ 후진 정지")
    else:
        print(
            f"Simulation: Backward at {current_forward_speed}% for {MOTOR_SLEEP_TIME} second"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        print("Simulation: Backward stopped")


def manual_turn_left():
    """수동 좌회전 (1초 동작 후 자동 정지)"""
    if motor:
        motor.set_motor_speed("A", current_high_turn_speed)
        motor.set_motor_speed("B", -current_high_turn_speed)
        print(
            f"◀️ 좌회전 {current_high_turn_speed}% - {MOTOR_SLEEP_TIME}초 후 자동 정지"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        motor.motor_stop()
        print("⏹️ 좌회전 정지")
    else:
        print(
            f"Simulation: Turn left at {current_high_turn_speed}% for {MOTOR_SLEEP_TIME} second"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        print("Simulation: Turn left stopped")


def manual_turn_right():
    """수동 우회전 (1초 동작 후 자동 정지)"""
    if motor:
        motor.set_motor_speed("A", -current_high_turn_speed)
        motor.set_motor_speed("B", current_high_turn_speed)
        print(
            f"▶️ 우회전 {current_high_turn_speed}% - {MOTOR_SLEEP_TIME}초 후 자동 정지"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        motor.motor_stop()
        print("⏹️ 우회전 정지")
    else:
        print(
            f"Simulation: Turn right at {current_high_turn_speed}% for {MOTOR_SLEEP_TIME} second"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        print("Simulation: Turn right stopped")


def avoid_obstacle():
    """장애물 피하기 (좌회전 → 직진 → 우회전) - 현재 설정값 사용"""
    avoid_time = current_avoid_time / 10.0  # 현재 설정값을 초 단위로 변환
    print(f"Obstacle avoidance started! (avoid time: {avoid_time:.1f}s)")

    # 1단계: 좌회전
    print("  1. Avoid by turning left")
    turn_left()
    time.sleep(avoid_time)

    # 2단계: 직진으로 지나가기
    print("  2. Go straight to pass")
    go_forward()
    time.sleep(avoid_time)

    # 3단계: 우회전으로 원래 방향
    print("  3. Turn right to return")
    turn_right()
    time.sleep(avoid_time)

    print("Obstacle avoidance completed!")


def drive():
    """
    스마트 도로폭 기반 주행 함수
    - 20cm 도로폭에서 경계선을 피해 중앙 유지
    - center 센서 감지 시 이전 방향 기반 회피
    """
    global last_turn_direction, turn_recovery_count

    # 1단계: 장애물 확인 (현재 안전거리 사용)
    distance = read_distance()
    if distance < current_safe_distance:
        print(f"Obstacle detected at {distance}cm (safe: {current_safe_distance}cm)")
        avoid_obstacle()
        return

    # 2단계: 도로폭 기반 라인 추적
    line_position = read_line()
    print(f"Line position: {line_position}, Last turn: {last_turn_direction}")

    if line_position == "none":
        # 경계선 없음 = 도로 중앙 (이상적)
        go_forward()
        turn_recovery_count += 1

        # 복구 카운터가 5 이상이면 방향 상태 리셋
        if turn_recovery_count >= 5:
            last_turn_direction = "none"
            turn_recovery_count = 0

    elif line_position == "left":
        # 왼쪽 경계선 감지 → 오른쪽으로 회피 (잠깐 턴 후 중앙으로)
        turn_right()

    elif line_position == "right":
        # 오른쪽 경계선 감지 → 왼쪽으로 회피 (잠깐 턴 후 중앙으로)
        turn_left()

    elif line_position == "center":
        # 중앙 경계선 감지 (위험!) → 이전 방향 반대로 회피
        if last_turn_direction == "left":
            # 왼쪽에서 오다가 중앙선 감지 → 오른쪽으로 회피
            slight_right()
            print("Center detected after left turn - avoiding right")
        elif last_turn_direction == "right":
            # 오른쪽에서 오다가 중앙선 감지 → 왼쪽으로 회피
            slight_left()
            print("Center detected after right turn - avoiding left")
        else:
            # 방향 히스토리 없음 → 기본적으로 오른쪽 회피
            slight_right()
            print("Center detected with no history - default right avoidance")


def emergency_stop():
    """긴급 정지 - 모든 모터 즉시 정지"""
    try:
        if motor:
            motor.motor_stop()
            print("✓ 모터 긴급 정지")
    except:
        pass


def show_final_settings():
    """종료 시 현재 설정값 표시"""
    print("\n" + "=" * 50)
    print("📊 종료 시점 설정값 요약")
    print("=" * 50)
    print(f"🚗 전진 속도:     {current_forward_speed:3d}% (기본값: {FORWARD_SPEED}%)")
    print(f"🔄 약한 회전:     {current_low_turn_speed:3d}% (기본값: {LOW_TURN_SPEED}%)")
    print(
        f"⚡ 강한 회전:     {current_high_turn_speed:3d}% (기본값: {HIGH_TURN_SPEED}%)"
    )
    print(f"🛡️ 안전 거리:     {current_safe_distance:3d}cm (기본값: {SAFE_DISTANCE}cm)")
    print(f"⏱️ 회피 시간:     {current_avoid_time/10:4.1f}s (기본값: {AVOID_TIME:.1f}s)")
    print(f"🕐 수동 동작시간: {MOTOR_SLEEP_TIME:4.1f}s")

    # 변경된 설정값 표시
    changed_settings = []
    if current_forward_speed != FORWARD_SPEED:
        changed_settings.append(
            f"전진속도: {FORWARD_SPEED}% → {current_forward_speed}%"
        )
    if current_low_turn_speed != LOW_TURN_SPEED:
        changed_settings.append(
            f"약한회전: {LOW_TURN_SPEED}% → {current_low_turn_speed}%"
        )
    if current_high_turn_speed != HIGH_TURN_SPEED:
        changed_settings.append(
            f"강한회전: {HIGH_TURN_SPEED}% → {current_high_turn_speed}%"
        )
    if current_safe_distance != SAFE_DISTANCE:
        changed_settings.append(
            f"안전거리: {SAFE_DISTANCE}cm → {current_safe_distance}cm"
        )
    if current_avoid_time != int(AVOID_TIME * 10):
        changed_settings.append(
            f"회피시간: {AVOID_TIME:.1f}s → {current_avoid_time/10:.1f}s"
        )

    if changed_settings:
        print("\n🔄 기본값에서 변경된 설정:")
        for change in changed_settings:
            print(f"  • {change}")
    else:
        print("\n✅ 모든 설정이 기본값과 동일")

    print("=" * 50)


def cleanup():
    """완전 초기화 - Ctrl+C 시 안전한 종료"""
    global running, autonomous_mode, manual_control_active
    global current_forward_speed, current_low_turn_speed, current_high_turn_speed
    global current_safe_distance, current_avoid_time

    try:
        print("\n🛑 안전한 종료 중...")

        # 1. 프로그램 종료 플래그 설정
        running = False

        # 2. 모든 모드 비활성화
        autonomous_mode = False
        manual_control_active = False

        # 3. 긴급 정지
        emergency_stop()

        # 4. 현재 설정값 표시
        show_final_settings()

        # 5. 터미널 설정 복원
        try:
            # 터미널을 원래 상태로 복원
            import termios
            import sys

            termios.tcsetattr(
                sys.stdin, termios.TCSADRAIN, termios.tcgetattr(sys.stdin)
            )
        except:
            pass

        # 6. 하드웨어 정리
        if line_sensor:
            try:
                line_sensor.cleanup()
                print("✓ 라인 센서 정리")
            except:
                pass

        if motor:
            try:
                motor.cleanup()
                print("✓ 모터 컨트롤러 정리")
            except:
                pass

        if ultrasonic:
            try:
                ultrasonic.cleanup()
                print("✓ 초음파 센서 정리")
            except:
                pass

        print("✅ 안전한 종료 완료")

    except Exception as e:
        print(f"⚠️ 종료 중 오류: {e}")
    finally:
        # 커서 위치 복원
        print("\n")  # 새 줄 추가


def main():
    """메인 함수 (키보드 제어)"""
    global running, autonomous_mode

    print("Ultra Simple Autonomous Car - 키보드 제어 버전")
    print("=" * 50)
    print("Features: Line following + Obstacle avoidance + Keyboard control")
    print("Initial Settings:")
    print(f"  Forward speed: {FORWARD_SPEED}%")
    print(f"  Turn speeds: Low={LOW_TURN_SPEED}%, High={HIGH_TURN_SPEED}%")
    print(f"  Safe distance: {SAFE_DISTANCE}cm")
    print(f"  Avoid time: {AVOID_TIME}s")
    print("=" * 50)

    if not setup():
        print("Setup failed")
        return

    try:
        print("\n🎮 키보드 제어 모드 시작")
        print("'h' 키를 눌러 제어 방법을 확인하세요")

        # 제어 가이드 출력
        print_control_menu()

        # 키보드 입력 스레드 시작
        keyboard_thread = threading.Thread(target=handle_keyboard_input, daemon=True)
        keyboard_thread.start()

        # 메인 루프
        while running:
            try:
                if autonomous_mode:
                    # 자동 주행 모드 (현재 설정값 실시간 반영)
                    drive()
                    time.sleep(0.1)
                else:
                    # 수동 모드 - 키보드 입력만 처리
                    time.sleep(0.1)
            except KeyboardInterrupt:
                # 메인 루프에서 Ctrl+C 감지
                print("\n\n⚠️ Ctrl+C 감지 - 긴급 정지 중...")
                emergency_stop()
                running = False
                break

    except KeyboardInterrupt:
        # 최상위에서 Ctrl+C 감지
        print("\n\n⚠️ Ctrl+C 감지 - 안전 종료 중...")
        emergency_stop()
        running = False
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        emergency_stop()
        running = False
    finally:
        # 항상 완전 초기화 실행
        cleanup()
        print("🏁 프로그램 완전 종료")


if __name__ == "__main__":
    main()
