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
    노란색 도로선 감지 및 회피 주행 - 검정색 도로 위에서 노란색 선을 피해 주행
    - left: 왼쪽 노란선 감지 → 우측으로 회피 (도로 중앙으로)
    - center: 중앙 노란선 감지 → 위험! 즉시 회피 (선을 밟고 있음)
    - right: 오른쪽 노란선 감지 → 좌측으로 회피 (도로 중앙으로)
    - none: 노란선 없음 → 검정 도로 위 안전, 직진
    - mixed: 복합 상황 (교차점, 코너 등)

    센서 동작:
    - HIGH(1): 노란선 감지 (밝은 색)
    - LOW(0): 검정 도로 감지 (어두운 색)
    """
    if line_sensor:
        try:
            line_info = line_sensor.get_line_position()

            # 센서 데이터가 딕셔너리 형태로 반환되는지 확인
            if isinstance(line_info, dict):
                sensors = line_info.get("sensors", {})
                left_detected = sensors.get("left", False)
                middle_detected = sensors.get("middle", False)
                right_detected = sensors.get("right", False)
                position = line_info.get("position")

                # 디버깅 정보 출력 (현재 설정값과 함께)
                if hasattr(read_line, "debug_counter"):
                    read_line.debug_counter += 1
                else:
                    read_line.debug_counter = 1

                # 10번마다 한 번씩 센서 상태 출력
                if read_line.debug_counter % 10 == 0:
                    print(
                        f"  [센서] L:{left_detected} M:{middle_detected} R:{right_detected} | Pos:{position} | Pattern:{line_info.get('pattern', 'N/A')}"
                    )

                # 노란색 도로선 회피 판단 (노란선을 피해서 검정 도로 위 주행)
                if not left_detected and not middle_detected and not right_detected:
                    return "safe_black_road"  # 노란선 없음 = 검정 도로 위 (안전)
                elif not left_detected and middle_detected and not right_detected:
                    return "yellow_center_danger"  # 중앙 노란선 밟음 = 위험! 즉시 회피
                elif left_detected and not middle_detected and not right_detected:
                    return "yellow_left_line"  # 왼쪽 노란선 감지 = 우측으로 회피
                elif not left_detected and not middle_detected and right_detected:
                    return "yellow_right_line"  # 오른쪽 노란선 감지 = 좌측으로 회피
                elif left_detected and middle_detected and not right_detected:
                    return "yellow_left_corner"  # 왼쪽 노란선 코너 = 강한 우회전
                elif not left_detected and middle_detected and right_detected:
                    return "yellow_right_corner"  # 오른쪽 노란선 코너 = 강한 좌회전
                elif left_detected and not middle_detected and right_detected:
                    return "narrow_road_yellow"  # 양쪽 노란선 = 좁은 도로, 신중히 직진
                elif left_detected and middle_detected and right_detected:
                    return "yellow_intersection"  # 모든 센서에 노란선 = 교차점
                else:
                    return "unknown"  # 알 수 없는 상태
            else:
                # 기존 position 기반 방식으로 fallback
                position = (
                    getattr(line_info, "position", None) or line_info.get("position")
                    if hasattr(line_info, "get")
                    else None
                )
                if position is None:
                    return "safe_black_road"
                elif position < -0.5:
                    return "yellow_left_line"
                elif position > 0.5:
                    return "yellow_right_line"
                else:
                    return "yellow_center_danger"

        except Exception as e:
            print(f"라인 센서 읽기 오류: {e}")
            return "safe_black_road"
    else:
        # 시뮬레이션
        import random

        return random.choice(
            [
                "safe_black_road",
                "yellow_left_line",
                "yellow_right_line",
                "yellow_center_danger",
            ]
        )


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
    print("  • 약한 회전: 라인 센서 center_left/center_right 감지 시 미세 조정")
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

    print("\n🔍 디버깅 기능:")
    print("  x: 라인 센서 상태 실시간 확인")
    print("  z: 거리 센서 상태 확인")

    print("\n💡 팁:")
    print("  • 모든 키는 Enter 없이 즉시 반응 (s 제외)")
    print("  • 자동 주행 중에도 속도 실시간 조절 가능")
    print(
        f"  • 수동 조작은 {MOTOR_SLEEP_TIME}초 동작 후 자동 정지 (속도/각도 테스트용)"
    )
    print("  • p 키로 언제든 모든 동작 즉시 중단")
    print("  • q 키 또는 Ctrl+C로 설정값 표시 후 안전 종료")
    print("  • x, z 키로 센서 상태 실시간 확인 가능")
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
            elif key == "x":
                print("\n🔍 라인 센서 상태 확인 중...")
                show_line_sensor_status()
            elif key == "z":
                print("\n🔍 거리 센서 상태 확인 중...")
                show_distance_sensor_status()
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


def show_line_sensor_status():
    """라인 센서 상태 실시간 표시"""
    print("=" * 50)
    print("📍 라인 센서 상태 모니터링 (10초간)")
    print("=" * 50)

    if line_sensor:
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                line_info = line_sensor.get_line_position()
                if isinstance(line_info, dict):
                    sensors = line_info.get("sensors", {})
                    left = sensors.get("left", False)
                    middle = sensors.get("middle", False)
                    right = sensors.get("right", False)
                    position = line_info.get("position")
                    pattern = line_info.get("pattern", "N/A")
                    description = line_info.get("description", "N/A")

                    print(
                        f"\r센서: L[{'●' if left else '○'}] M[{'●' if middle else '○'}] R[{'●' if right else '○'}] | "
                        f"위치: {position if position is not None else 'None':>5} | "
                        f"패턴: {pattern} | {description:15s}",
                        end="",
                        flush=True,
                    )
                else:
                    print(
                        f"\r센서 데이터 형식 오류: {type(line_info)}",
                        end="",
                        flush=True,
                    )
                time.sleep(0.2)
            except Exception as e:
                print(f"\r센서 읽기 오류: {e}", end="", flush=True)
                break
    else:
        print("시뮬레이션 모드 - 실제 센서 없음")

    print("\n" + "=" * 50)


def show_distance_sensor_status():
    """거리 센서 상태 실시간 표시"""
    print("=" * 50)
    print("📏 거리 센서 상태 모니터링 (10초간)")
    print("=" * 50)

    if ultrasonic:
        start_time = time.time()
        distances = []
        while time.time() - start_time < 10:
            try:
                distance = ultrasonic.measure_distance()
                if distance:
                    distances.append(distance)
                    avg_distance = sum(distances[-10:]) / len(
                        distances[-10:]
                    )  # 최근 10개 평균
                    status = (
                        "🚫 장애물!" if distance < current_safe_distance else "✅ 안전"
                    )

                    print(
                        f"\r현재 거리: {distance:5.1f}cm | 평균: {avg_distance:5.1f}cm | "
                        f"안전거리: {current_safe_distance}cm | {status}",
                        end="",
                        flush=True,
                    )
                else:
                    print(f"\r거리 측정 실패", end="", flush=True)
                time.sleep(0.3)
            except Exception as e:
                print(f"\r거리 센서 오류: {e}", end="", flush=True)
                break
    else:
        print("시뮬레이션 모드 - 실제 센서 없음")

    print("\n" + "=" * 50)


def read_distance():
    """앞의 거리 읽기"""
    if ultrasonic:
        distance = ultrasonic.measure_distance()
        return distance if distance else 999
    else:
        # 시뮬레이션
        import random

        if random.random() < 0.1:  # 10% obstacle chance
            distance = random.randint(5, current_safe_distance - 1)
            return distance
        else:
            distance = random.randint(current_safe_distance + 10, 100)
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
    노란색 도로선 회피 주행 함수
    - 노란색 선(도로선)을 피해서 검정색 도로 위를 안전하게 주행
    - 노란선 감지 시 즉시 회피, 노란선 없으면 검정 도로에서 안전하게 직진
    """
    global last_turn_direction, turn_recovery_count

    # 1단계: 장애물 확인 (현재 안전거리 사용)
    distance = read_distance()
    if distance < current_safe_distance:
        print(f"🚫 장애물 감지 {distance}cm (안전거리: {current_safe_distance}cm)")
        avoid_obstacle()
        return

    # 2단계: 노란색 도로선 회피 주행
    road_status = read_line()
    print(f"🛣️ 도로 상태: {road_status}, 이전 방향: {last_turn_direction}")

    if road_status == "safe_black_road":
        # 노란선 없음 = 검정 도로 위 안전 구간
        print("  ✅ 검정 도로 위 안전 - 직진")
        go_forward()
        last_turn_direction = "none"
        turn_recovery_count = 0

    elif road_status == "yellow_center_danger":
        # 중앙 노란선 밟음 = 매우 위험! 즉시 회피
        print("  ⚠️ 노란선 밟음! 즉시 검정 도로로 회피")
        if last_turn_direction == "left":
            print("    → 이전 좌회전 기록 - 우측으로 강한 회피")
            turn_right()
        elif last_turn_direction == "right":
            print("    → 이전 우회전 기록 - 좌측으로 강한 회피")
            turn_left()
        else:
            print("    → 기본 우측 회피 (검정 도로로)")
            turn_right()
        turn_recovery_count = 0

    elif road_status == "yellow_left_line":
        # 왼쪽 노란선 감지 = 우측으로 회피 (검정 도로 중앙으로)
        print("  ↪️ 왼쪽 노란선 감지 - 우측으로 회피")
        turn_right()

    elif road_status == "yellow_right_line":
        # 오른쪽 노란선 감지 = 좌측으로 회피 (검정 도로 중앙으로)
        print("  ↩️ 오른쪽 노란선 감지 - 좌측으로 회피")
        turn_left()

    elif road_status == "yellow_left_corner":
        # 왼쪽 노란선 코너 = 강한 우회전으로 검정 도로 중앙 복귀
        print("  🔄 왼쪽 노란선 코너 - 강한 우회전")
        turn_right()
        last_turn_direction = "right"
        turn_recovery_count = 0

    elif road_status == "yellow_right_corner":
        # 오른쪽 노란선 코너 = 강한 좌회전으로 검정 도로 중앙 복귀
        print("  🔄 오른쪽 노란선 코너 - 강한 좌회전")
        turn_left()
        last_turn_direction = "left"
        turn_recovery_count = 0

    elif road_status == "narrow_road_yellow":
        # 양쪽 노란선 = 좁은 검정 도로, 신중하게 직진
        print("  🚧 좁은 검정 도로 - 천천히 중앙으로 직진")
        # 속도를 줄여서 안전하게 직진
        if motor:
            motor.set_motor_speed("A", current_forward_speed // 2)
            motor.set_motor_speed("B", current_forward_speed // 2)
            print(f"    → 속도 감소: {current_forward_speed // 2}%")
        else:
            print(f"    → 시뮬레이션: 속도 감소 {current_forward_speed // 2}%")
        turn_recovery_count = 0

    elif road_status == "yellow_intersection":
        # 모든 센서에 노란선 = 교차점
        print("  🚦 노란선 교차점 감지 - 신중하게 직진")
        # 교차점에서는 속도를 줄이고 직진
        if motor:
            motor.set_motor_speed("A", current_forward_speed // 3)
            motor.set_motor_speed("B", current_forward_speed // 3)
            print(f"    → 교차점 속도: {current_forward_speed // 3}%")
        else:
            print(f"    → 시뮬레이션: 교차점 속도 {current_forward_speed // 3}%")
        turn_recovery_count = 0

    else:
        # 알 수 없는 상태
        print(f"  ❓ 알 수 없는 도로 상태: {road_status} - 정지")
        stop()
        time.sleep(0.5)


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

    print("Ultra Simple Autonomous Car - 노란선 회피 주행 버전")
    print("=" * 60)
    print("🛣️ 도로: 검정색 / 도로선: 노란색")
    print("🎯 기능: 노란선 회피 + 장애물 회피 + 키보드 제어")
    print("=" * 60)
    print("초기 설정:")
    print(f"  🚗 전진 속도: {FORWARD_SPEED}%")
    print(f"  🔄 회전 속도: 약함={LOW_TURN_SPEED}%, 강함={HIGH_TURN_SPEED}%")
    print(f"  🛡️ 안전 거리: {SAFE_DISTANCE}cm")
    print(f"  ⏱️ 회피 시간: {AVOID_TIME}s")
    print("=" * 60)

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
