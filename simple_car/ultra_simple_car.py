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
FORWARD_SPEED = 80  # 직진 속도
LOW_TURN_SPEED = 50  # 약한 회전 속도
HIGH_TURN_SPEED = 80  # 강한 회전 속도
SAFE_DISTANCE = 15  # 장애물 안전 거리 (cm)
AVOID_TIME = 0.6  # 회피 동작 시간 (초)
AUTO_LOOP_INTERVAL = 0.01  # 자동 주행 루프 간격(초) - 반응 속도 향상
SLIGHT_TURN_THRESHOLD = 2  # 약한 조향 유지 횟수 임계(지속 감지 시 강한 조향)
SLOW_FORWARD_DIVISOR = 2  # 양쪽 감지 시 전진 속도 나눔 값

MOTOR_SLEEP_TIME = 0.3

# 하드웨어 객체들
line_sensor = None
motor = None
ultrasonic = None

# 도로폭 기반 라인 추적을 위한 방향 상태 추적
last_turn_direction = "none"  # "left", "right", "none"
turn_recovery_count = 0  # 턴 후 복구 카운터
last_line_status = "none"  # 자동 주행 상태 변화 감지용

# 모터 캐시(불필요한 반복 전송 방지로 반응성 향상)
_last_right_speed = None
_last_left_speed = None

# 감지 지속 카운터(히스테리시스)
_cnt_left = 0
_cnt_right = 0
_cnt_center = 0
_cnt_none = 0
_cnt_both = 0

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


def set_motor_speeds_quiet(right_speed: int, left_speed: int):
    """중복 설정을 피하며 모터 속도를 설정 (반응성 향상)"""
    global _last_right_speed, _last_left_speed
    try:
        if not motor:
            return
        # 변경이 없으면 전송 생략
        if right_speed == _last_right_speed and left_speed == _last_left_speed:
            return
        motor.set_motor_speed("A", right_speed)
        motor.set_motor_speed("B", left_speed)
        _last_right_speed = right_speed
        _last_left_speed = left_speed
    except Exception as _:
        pass


def read_line():
    """
    단순 차선 유지용 감지 결과 반환
    - 센서 의미: HIGH(1)=검은 바닥, LOW(0)=노란 라인
    - 반환값: left_line | right_line | center_line | both_lines | none
    """
    if line_sensor:
        try:
            line_info = line_sensor.get_line_position()

            # 센서 데이터가 딕셔너리 형태로 반환되는지 확인
            if isinstance(line_info, dict):
                sensors = line_info.get("sensors", {})
                left = int(sensors.get("left", 1))
                middle = int(sensors.get("middle", 1))
                right = int(sensors.get("right", 1))

                # LOW(0) = 노란 라인 감지
                if middle == 0:
                    return "center_line"
                if left == 0 and right == 0:
                    return "both_lines"
                if left == 0:
                    return "left_line"
                if right == 0:
                    return "right_line"
                return "none"

            # fallback: 위치 기반(-1=좌, 0=중앙, 1=우)
            position = (
                getattr(line_info, "position", None) or line_info.get("position")
                if hasattr(line_info, "get")
                else None
            )
            if position is None:
                return "none"
            if position <= -0.25:
                return "left_line"
            if position >= 0.25:
                return "right_line"
            return "center_line"

        except Exception as e:
            print(f"라인 센서 읽기 오류: {e}")
            return "none"
    else:
        # 시뮬레이션
        import random

        return random.choice(["none", "left_line", "right_line", "center_line"])


def get_single_key():
    """Enter 키 없이 단일 키 입력 받기"""
    try:
        # 터미널 설정 저장
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            # raw 모드로 설정 (Enter 키 없이 바로 반응)
            tty.setcbreak(sys.stdin.fileno())

            # 키 입력 대기 (논블로킹)
            if select.select([sys.stdin], [], [], 0.02) == ([sys.stdin], [], []):
                char = sys.stdin.read(1)

                # 스페이스 키 처리
                if char == " ":
                    return "space"

                # 화살표/특수키 이스케이프 시퀀스 처리 (견고한 3바이트 파싱)
                if char == "\x1b":
                    # 두 번째 바이트 시도
                    second = None
                    if select.select([sys.stdin], [], [], 0.02)[0]:
                        second = sys.stdin.read(1)
                    if not second:
                        return "esc"

                    # 세 번째 바이트 시도
                    if second in ("[", "O"):
                        if select.select([sys.stdin], [], [], 0.02)[0]:
                            third = sys.stdin.read(1)
                        else:
                            return "esc"

                        if third == "A":
                            return "up"
                        if third == "B":
                            return "down"
                        if third == "C":
                            return "right"
                        if third == "D":
                            return "left"

                        return "esc"

                    return "esc"

                # 기본 문자 처리
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
    print("  Enter: 자동 주행 시작")
    print("  스페이스(또는 p): 즉시 정지 (모든 동작 중단, 수동 모드로 전환)")
    print("  q: 프로그램 종료")

    print(f"\n🎮 수동 조작 (정지 상태에서만, {MOTOR_SLEEP_TIME}초 동작 후 자동 정지):")
    print("  ↑ 또는 w: 전진 (현재 전진 속도로)")
    print("  ↓ 또는 s: 후진 (현재 전진 속도로)")
    print("  ← 또는 a: 좌회전 (현재 강한 회전 속도로)")
    print("  → 또는 d: 우회전 (현재 강한 회전 속도로)")

    print("\n⚙️ 속도 조절 (실시간, Enter 키 불필요):")
    print("  1,2: 전진 속도 -10%/+10%")
    print("  3,4: 약한 회전 속도 -10%/+10%")
    print("  5,6: 강한 회전 속도 -10%/+10%")
    print("  7,8: 안전 거리 -5cm/+5cm")
    print("  9,0: 회피 시간 -0.1s/+0.1s")

    print("\n🔍 디버깅 기능:")
    print("  x: 라인 센서 상태 실시간 확인")
    print("  z: 거리 센서 상태 확인")
    print("  t: 조향 테스트 시퀀스 실행")

    print("\n💡 팁:")
    print("  • 대부분의 키는 Enter 없이 즉시 반응, 자동 시작은 Enter 키")
    print("  • 자동 주행 중에도 속도 실시간 조절 가능")
    print(
        f"  • 수동 조작은 {MOTOR_SLEEP_TIME}초 동작 후 자동 정지 (속도/각도 테스트용)"
    )
    print("  • 스페이스(또는 p) 키로 언제든 모든 동작 즉시 중단")
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
                f"\r상태: {status} | h=도움말, Enter=자동시작, 스페이스=정지, q=종료",
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
            elif key == "\n":
                if not autonomous_mode:
                    print("\n🚗 자동 주행 시작")
                    autonomous_mode = True
                    manual_control_active = False
                else:
                    print("\n이미 자동 주행 중")
            elif key in ["p", "space"]:
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
            elif (
                key in ["w", "a", "d", "s", "up", "down", "left", "right"]
                and not autonomous_mode
            ):
                manual_control_active = True
                if key in ["w", "up"]:
                    print("\n🔼 수동 전진")
                    manual_forward()
                elif key in ["s", "down"]:
                    print("\n🔽 수동 후진")
                    manual_backward()
                elif key in ["a", "left"]:
                    print("\n◀️ 수동 좌회전")
                    manual_turn_left()
                elif key in ["d", "right"]:
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
                print("\n🔍 라인 센서 상태 확인 중 (20초)...")
                show_line_sensor_status(20)
            elif key == "z":
                print("\n🔍 거리 센서 상태 확인 중...")
                show_distance_sensor_status()
            elif key == "t":
                print("\n🧪 조향 테스트 시퀀스 시작")
                test_steering_sequence()
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


def show_line_sensor_status(duration_seconds: int = 20):
    """라인 센서 상태 실시간 표시 (기본 20초)"""
    print("=" * 50)
    print(f"📍 라인 센서 상태 모니터링 ({duration_seconds}초간)")
    print("=" * 50)

    if line_sensor:
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
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


def test_steering_sequence():
    """조향 테스트: 좌→우→약좌→약우→전진→후진 순서로 각각 0.5s 동작"""
    seq = [
        ("left", 0.5),
        ("right", 0.5),
        ("slight_left", 0.5),
        ("slight_right", 0.5),
        ("forward", 0.5),
        ("backward", 0.5),
        ("stop", 0.0),
    ]
    for action, dur in seq:
        if dur > 0:
            drive_motion(action, dur, label="테스트")
        else:
            drive_motion(action)
        time.sleep(0.2)


def get_line_sensor_snapshot(prefix: str = "센서") -> str:
    """라인 센서 스냅샷을 한 줄 텍스트로 반환 (수동 디버깅용)"""
    try:
        if line_sensor:
            info = line_sensor.get_line_position()
            if isinstance(info, dict):
                sensors = info.get("sensors", {})
                left = int(sensors.get("left", 1))
                middle = int(sensors.get("middle", 1))
                right = int(sensors.get("right", 1))
                pattern = info.get("pattern", f"{left}{middle}{right}")
                position = info.get("position")
            else:
                left = middle = right = 1
                pattern = "N/A"
                position = None

            simple = read_line()
            return (
                f"{prefix}: 상태={simple} | "
                f"L[{'●' if left else '○'}] M[{'●' if middle else '○'}] R[{'●' if right else '○'}] | "
                f"패턴:{pattern} | 위치:{position if position is not None else 'None'}"
            )
        else:
            return f"{prefix}: 시뮬레이션 - 실제 센서 없음"
    except Exception as e:
        return f"{prefix}: 센서 오류: {e}"


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


def drive_motion(action: str, duration_seconds: float = None, label: str = "수동"):
    """자동/수동 공용 모터 제어 함수
    - action: forward | backward | left | right | slight_left | slight_right | stop
    - duration_seconds: 지정 시 해당 시간 동작 후 정지 및 스냅샷 출력
    - label: 로그용 접두사
    """
    try:
        if action == "forward":
            go_forward()
        elif action == "backward":
            if motor:
                set_motor_speeds_quiet(-current_forward_speed, -current_forward_speed)
            else:
                print(f"Simulation: Backward at {current_forward_speed}%")
        elif action == "left":
            turn_left()
        elif action == "right":
            turn_right()
        elif action == "slight_left":
            slight_left()
        elif action == "slight_right":
            slight_right()
        elif action == "stop":
            set_motor_speeds_quiet(0, 0)
        else:
            print(f"알 수 없는 동작: {action}")
            return

        if duration_seconds is not None:
            print(get_line_sensor_snapshot(f"[{label} {action}-이전]"))
            time.sleep(duration_seconds)
            set_motor_speeds_quiet(0, 0)
            print(f"⏹️ {label} {action} 정지")
            print(get_line_sensor_snapshot(f"[{label} {action}-이후]"))

    except Exception as e:
        print(f"모터 제어 오류({action}): {e}")


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


def print_runtime_status(context: str):
    """수동/자동 동작 시점의 런타임 상태 요약 출력"""
    try:
        distance = None
        if ultrasonic:
            try:
                distance = ultrasonic.measure_distance()
            except:
                distance = None

        print("-" * 60)
        print(
            f"[{context}] 속도 설정: FWD={current_forward_speed}% | TURN_LOW={current_low_turn_speed}% | TURN_HIGH={current_high_turn_speed}%"
        )
        print(
            f"안전거리={current_safe_distance}cm | 회피시간={current_avoid_time/10:.1f}s | 자동모드={autonomous_mode}"
        )
        if distance is not None:
            print(f"현재 거리={distance:.1f}cm (안전기준 {current_safe_distance}cm)")
        else:
            print("현재 거리=알수없음")
        print("-" * 60)
    except Exception as _:
        pass


def go_forward():
    """직진 (현재 설정값 사용)"""
    if motor:
        set_motor_speeds_quiet(current_forward_speed, current_forward_speed)
        print(f"Forward at {current_forward_speed}%")
    else:
        print(f"Simulation: Forward at {current_forward_speed}%")


def turn_left():
    """좌회전 (오른쪽 경계선에서 벗어나기) - 현재 설정값 사용"""
    global last_turn_direction, turn_recovery_count

    if motor:
        set_motor_speeds_quiet(current_high_turn_speed, -20)
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
        set_motor_speeds_quiet(0, current_high_turn_speed + 10)
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
    global last_turn_direction
    if motor:
        set_motor_speeds_quiet(current_forward_speed, current_low_turn_speed)
        print(f"Slight left (R:{current_forward_speed}%, L:{current_low_turn_speed}%)")
    else:
        print(
            f"Simulation: Slight left (R:{current_forward_speed}%, L:{current_low_turn_speed}%)"
        )
    last_turn_direction = "left"


def slight_right():
    """약한 우회전 (중앙선 회피용) - 현재 설정값 사용"""
    global last_turn_direction
    if motor:
        set_motor_speeds_quiet(current_low_turn_speed, current_forward_speed)
        print(f"Slight right (R:{current_low_turn_speed}%, L:{current_forward_speed}%)")
    else:
        print(
            f"Simulation: Slight right (R:{current_low_turn_speed}%, L:{current_forward_speed}%)"
        )
    last_turn_direction = "right"


def manual_forward():
    """수동 전진 (1초 동작 후 자동 정지)"""
    if motor:
        drive_motion("forward", MOTOR_SLEEP_TIME, label="수동")
    else:
        print(
            f"Simulation: Forward at {current_forward_speed}% for {MOTOR_SLEEP_TIME} second"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        print("Simulation: Forward stopped")


def manual_backward():
    """수동 후진 (1초 동작 후 자동 정지)"""
    if motor:
        drive_motion("backward", MOTOR_SLEEP_TIME, label="수동")
    else:
        print(
            f"Simulation: Backward at {current_forward_speed}% for {MOTOR_SLEEP_TIME} second"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        print("Simulation: Backward stopped")


def manual_turn_left():
    """수동 좌회전 (1초 동작 후 자동 정지)"""
    if motor:
        drive_motion("left", MOTOR_SLEEP_TIME, label="수동")
    else:
        print(
            f"Simulation: Turn left at {current_high_turn_speed}% for {MOTOR_SLEEP_TIME} second"
        )
        time.sleep(MOTOR_SLEEP_TIME)
        print("Simulation: Turn left stopped")


def manual_turn_right():
    """수동 우회전 (1초 동작 후 자동 정지)"""
    if motor:
        drive_motion("right", MOTOR_SLEEP_TIME, label="수동")
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
    차선 유지 주행 (가이드 반영)
    - 왼쪽 센서 라인 감지 → 우측 조향(벗어나지 않도록)
    - 오른쪽 센서 라인 감지 → 좌측 조향
    - 중앙 센서 라인 감지 → 선 이탈 직전 → 직전 조향의 반대로 복귀
    - 양쪽 감지 → 차선 사이 직진(감속)
    - 미감지 → 직진 유지
    """
    global last_turn_direction, turn_recovery_count
    global _cnt_left, _cnt_right, _cnt_center, _cnt_none, _cnt_both

    # 1) 장애물 확인
    distance = read_distance()
    if distance < current_safe_distance:
        print(f"🚫 장애물 감지 {distance}cm (안전거리: {current_safe_distance}cm)")
        avoid_obstacle()
        return

    # 2) 차선 유지 로직
    status = read_line()
    global last_line_status
    if status != last_line_status:
        print(f"🛣️ 라인 상태: {status}, 이전 방향: {last_turn_direction}")
        last_line_status = status

    # 카운터 업데이트 (히스테리시스)
    _cnt_left = _cnt_left + 1 if status == "left_line" else 0
    _cnt_right = _cnt_right + 1 if status == "right_line" else 0
    _cnt_center = _cnt_center + 1 if status == "center_line" else 0
    _cnt_both = _cnt_both + 1 if status == "both_lines" else 0
    _cnt_none = _cnt_none + 1 if status == "none" else 0

    # 동작 결정
    if status == "left_line":
        # 직진하면 좌측 차선을 밟으므로 우측으로 이동
        if _cnt_left >= SLIGHT_TURN_THRESHOLD:
            turn_right()
        else:
            slight_right()
        return

    if status == "right_line":
        if _cnt_right >= SLIGHT_TURN_THRESHOLD:
            turn_left()
        else:
            slight_left()
        return

    if status == "center_line":
        # 선 이탈 직전, '직전 조향'이 아니라 '직전 감지 상태'의 반대 방향으로 복귀
        # last_line_status 기준: left_line 감지 후 중앙이면 우측, right_line 감지 후 중앙이면 좌측
        if last_line_status == "left_line":
            turn_right()
        elif last_line_status == "right_line":
            turn_left()
        else:
            # 불확실하면 마지막 조향의 반대로 시도
            if last_turn_direction == "left":
                turn_right()
            elif last_turn_direction == "right":
                turn_left()
            else:
                slight_right()
        return

    if status == "both_lines":
        # 차선 사이 중앙. 속도를 낮춰 안정 직진
        if motor:
            set_motor_speeds_quiet(
                current_forward_speed // SLOW_FORWARD_DIVISOR,
                current_forward_speed // SLOW_FORWARD_DIVISOR,
            )
        else:
            pass
        return

    # none: 둘 다 감지되지 않음 → 직진 유지
    go_forward()
    last_turn_direction = "none"
    turn_recovery_count = 0


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

    print("Ultra Simple Autonomous Car - 노란선 추적 주행 버전")
    print("=" * 60)
    print("🛣️ 도로: 검정색 / 라인: 노란색")
    print("🎯 기능: 노란선 추적 + 장애물 회피 + 키보드 제어")
    print("🔧 센서: test_line_sensors.py 로직 기반 정확한 라인 감지")
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
                    # 자동 주행 모드 (더 빠른 루프)
                    drive()
                    time.sleep(AUTO_LOOP_INTERVAL)
                else:
                    # 수동 모드 - 키보드 입력만 처리
                    time.sleep(0.02)
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
