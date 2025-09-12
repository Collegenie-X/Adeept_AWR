#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
고성능 자율주행 로봇 - 빠른 반응속도 버전
- 멀티스레드 기반 센서 데이터 처리
- 0.2초 단위 빠른 판단 및 제어
- 실시간 키보드 제어 및 설정 조절
- 세밀한 반응속도 조절 기능

주요 기능:
1. 멀티스레드 센서 데이터 수집 (라인센서, 초음파센서)
2. 0.2초 단위 빠른 의사결정 및 모터 제어
3. 논블로킹 키보드 입력으로 실시간 설정 변경
4. 반응속도 세밀 조절 (0.05초 ~ 1.0초)
"""

import time
import threading
import os
import sys
import select
import termios
import tty
from queue import Queue, Empty
import signal

# 하드웨어 가져오기
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hardware.test_line_sensors import LineSensorController
    from hardware.test_gear_motors import GearMotorController
    from hardware.test_ultrasonic_sensor import UltrasonicSensor

    print("✓ 하드웨어 모듈 로드 성공")
except ImportError:
    print("⚠️ 하드웨어 모듈 없음 - 시뮬레이션 모드")
    LineSensorController = None
    GearMotorController = None
    UltrasonicSensor = None

# ============================================================================
# 고성능 설정값 - 빠른 반응을 위한 조정
# ============================================================================

# 기본 속도 설정 (더 빠른 반응을 위해 조정)
FORWARD_SPEED = 75  # 전진 속도 (%)
LOW_TURN_SPEED = 45  # 약한 회전 속도 (%)
HIGH_TURN_SPEED = 85  # 강한 회전 속도 (%)
SAFE_DISTANCE = 12  # 장애물 안전 거리 (cm) - 더 가까운 거리에서 반응
AVOID_TIME = 0.4  # 회피 동작 시간 (초) - 더 빠른 회피

# 반응속도 설정
DECISION_INTERVAL = 0.2  # 의사결정 주기 (초) - 0.2초마다 판단
SENSOR_READ_INTERVAL = 0.05  # 센서 읽기 주기 (초) - 0.05초마다 센서 데이터 수집
MOTOR_SLEEP_TIME = 0.3  # 수동 조작 시 동작 시간

# 센서 데이터 스무딩을 위한 설정
SENSOR_HISTORY_SIZE = 3  # 센서 데이터 이력 크기 (노이즈 필터링용)
DISTANCE_THRESHOLD = 3  # 거리 변화 임계값 (cm)

# ============================================================================
# 전역 변수
# ============================================================================

# 하드웨어 객체들
line_sensor = None
motor = None
ultrasonic = None

# 현재 설정값 (실시간 조절 가능)
current_forward_speed = FORWARD_SPEED
current_low_turn_speed = LOW_TURN_SPEED
current_high_turn_speed = HIGH_TURN_SPEED
current_safe_distance = SAFE_DISTANCE
current_avoid_time = int(AVOID_TIME * 10)
current_decision_interval = DECISION_INTERVAL
current_sensor_interval = SENSOR_READ_INTERVAL

# 제어 플래그
running = True
autonomous_mode = False
manual_control_active = False

# 라인 추적 상태
last_turn_direction = "none"
turn_recovery_count = 0

# 멀티스레드용 데이터 큐
sensor_data_queue = Queue()
ultrasonic_data_queue = Queue()

# 센서 데이터 이력 (스무딩용)
line_sensor_history = []
ultrasonic_history = []

# 스레드 락
data_lock = threading.Lock()

# ============================================================================
# 센서 데이터 수집 스레드
# ============================================================================


def line_sensor_thread():
    """라인 센서 데이터 수집 스레드"""
    global running, line_sensor_history

    print("📡 라인 센서 스레드 시작")

    while running:
        try:
            if line_sensor:
                raw_data = line_sensor.get_line_position()
                # 실제 하드웨어의 형식에 맞게 변환
                sensors = raw_data.get("sensors", {})
                line_data = {
                    "left_sensor": sensors.get("left", False),
                    "center_sensor": sensors.get(
                        "middle", False
                    ),  # middle -> center_sensor
                    "right_sensor": sensors.get("right", False),
                }
            else:
                # 시뮬레이션 모드
                import random

                line_data = {
                    "left_sensor": random.choice([True, False]),
                    "center_sensor": random.choice([True, False]),
                    "right_sensor": random.choice([True, False]),
                }

            # 데이터 히스토리 관리
            with data_lock:
                line_sensor_history.append(line_data)
                if len(line_sensor_history) > SENSOR_HISTORY_SIZE:
                    line_sensor_history.pop(0)

            # 큐에 데이터 추가
            try:
                sensor_data_queue.put(line_data, timeout=0.01)
            except:
                pass  # 큐가 꽉 찬 경우 무시

            time.sleep(current_sensor_interval)

        except Exception as e:
            if running:
                print(f"라인 센서 스레드 오류: {e}")
            time.sleep(0.1)

    print("📡 라인 센서 스레드 종료")


def ultrasonic_sensor_thread():
    """초음파 센서 데이터 수집 스레드"""
    global running, ultrasonic_history

    print("📡 초음파 센서 스레드 시작")

    while running:
        try:
            if ultrasonic:
                distance = ultrasonic.measure_distance()
                # None 값 처리 (측정 실패 시)
                if distance is None:
                    distance = 50.0  # 기본값으로 안전한 거리 설정
            else:
                # 시뮬레이션 모드
                import random

                distance = random.uniform(5, 50)

            # 데이터 히스토리 관리 (스무딩)
            with data_lock:
                ultrasonic_history.append(distance)
                if len(ultrasonic_history) > SENSOR_HISTORY_SIZE:
                    ultrasonic_history.pop(0)

                # 평균값 계산 (노이즈 필터링)
                if len(ultrasonic_history) >= 2:
                    avg_distance = sum(ultrasonic_history) / len(ultrasonic_history)
                else:
                    avg_distance = distance

            # 큐에 데이터 추가
            try:
                ultrasonic_data_queue.put(avg_distance, timeout=0.01)
            except:
                pass  # 큐가 꽉 찬 경우 무시

            time.sleep(current_sensor_interval)

        except Exception as e:
            if running:
                print(f"초음파 센서 스레드 오류: {e}")
            time.sleep(0.1)

    print("📡 초음파 센서 스레드 종료")


# ============================================================================
# 스무딩된 센서 데이터 읽기
# ============================================================================


def get_smoothed_line_data():
    """스무딩된 라인 센서 데이터 반환"""
    with data_lock:
        if not line_sensor_history:
            return {"left_sensor": False, "center_sensor": False, "right_sensor": False}

        # 최근 데이터들의 다수결로 결정 (노이즈 제거)
        left_votes = sum(
            1 for data in line_sensor_history if data.get("left_sensor", False)
        )
        center_votes = sum(
            1 for data in line_sensor_history if data.get("center_sensor", False)
        )
        right_votes = sum(
            1 for data in line_sensor_history if data.get("right_sensor", False)
        )

        threshold = len(line_sensor_history) // 2

        return {
            "left_sensor": left_votes > threshold,
            "center_sensor": center_votes > threshold,
            "right_sensor": right_votes > threshold,
        }


def get_smoothed_distance():
    """스무딩된 거리 데이터 반환"""
    try:
        return ultrasonic_data_queue.get_nowait()
    except Empty:
        with data_lock:
            if ultrasonic_history:
                return sum(ultrasonic_history) / len(ultrasonic_history)
            else:
                return 50.0  # 기본값


# ============================================================================
# 모터 제어 함수 (빠른 반응을 위한 최적화)
# ============================================================================


def stop():
    """모터 정지"""
    if motor:
        motor.motor_stop()
    # print("⏹️ 정지")  # 로그 최소화로 성능 개선


def go_forward():
    """전진 (현재 설정값 사용)"""
    if motor:
        motor.set_motor_speed("A", current_forward_speed)
        motor.set_motor_speed("B", current_forward_speed)
    # print(f"🔼 전진 {current_forward_speed}%")  # 로그 최소화


def turn_left():
    """좌회전 (강한 회전)"""
    if motor:
        motor.set_motor_speed("A", current_high_turn_speed)
        motor.set_motor_speed("B", -current_high_turn_speed)
    # print(f"◀️ 좌회전 {current_high_turn_speed}%")  # 로그 최소화


def turn_right():
    """우회전 (강한 회전)"""
    if motor:
        motor.set_motor_speed("A", -current_high_turn_speed)
        motor.set_motor_speed("B", current_high_turn_speed)
    # print(f"▶️ 우회전 {current_high_turn_speed}%")  # 로그 최소화


def slight_left():
    """약간 좌회전 (미세 조정)"""
    if motor:
        motor.set_motor_speed("A", current_low_turn_speed)
        motor.set_motor_speed("B", current_forward_speed)
    # print(f"↖️ 약간 좌회전 (L:{current_low_turn_speed}%, R:{current_forward_speed}%)")  # 로그 최소화


def slight_right():
    """약간 우회전 (미세 조정)"""
    if motor:
        motor.set_motor_speed("A", current_forward_speed)
        motor.set_motor_speed("B", current_low_turn_speed)
    # print(f"↗️ 약간 우회전 (L:{current_forward_speed}%, R:{current_low_turn_speed}%)")  # 로그 최소화


def avoid_obstacle():
    """장애물 회피 (빠른 회피 후 즉시 라인 추적 재개)"""
    global last_turn_direction, turn_recovery_count

    avoid_time = current_avoid_time / 10.0

    # 빠른 회피 패턴 - 더 짧은 시간으로 빠른 회피
    turn_left()
    time.sleep(avoid_time * 0.2)  # 회피 시간의 20% (더 짧게)

    go_forward()
    time.sleep(avoid_time * 0.3)  # 회피 시간의 30% (더 짧게)

    turn_right()
    time.sleep(avoid_time * 0.2)  # 회피 시간의 20% (더 짧게)

    # 회피 완료 후 즉시 전진하며 라인 탐색 재개
    go_forward()

    # 회피 후 라인 추적 상태 리셋
    turn_recovery_count = 0
    last_turn_direction = "none"


# ============================================================================
# 수동 조작 함수 (테스트용)
# ============================================================================


def manual_forward():
    """수동 전진 (빠른 테스트용)"""
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


# def manual_backward():
#     """수동 후진 (사용 안함 - w,a,d 키만 사용)"""
#     pass


def manual_turn_left():
    """수동 좌회전 (빠른 테스트용)"""
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
    """수동 우회전 (빠른 테스트용)"""
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


# ============================================================================
# 고성능 라인 추적 알고리즘
# ============================================================================


def analyze_line_position():
    """라인 위치 분석 (빠른 판단)"""
    line_data = get_smoothed_line_data()

    left_sensor = line_data.get("left_sensor", False)
    center_sensor = line_data.get("center_sensor", False)
    right_sensor = line_data.get("right_sensor", False)

    # 빠른 판단을 위한 우선순위 기반 로직
    if left_sensor and not center_sensor and not right_sensor:
        return "left"
    elif not left_sensor and not center_sensor and right_sensor:
        return "right"
    elif not left_sensor and center_sensor and not right_sensor:
        return "center"
    elif left_sensor and center_sensor and not right_sensor:
        return "left"  # 좌측 우선
    elif not left_sensor and center_sensor and right_sensor:
        return "right"  # 우측 우선
    elif left_sensor and not center_sensor and right_sensor:
        return "center"  # 양쪽 감지 시 중앙으로 간주
    elif left_sensor and center_sensor and right_sensor:
        return "center"  # 모든 센서 감지 시 중앙 유지
    else:
        return "none"  # 라인 없음


def fast_drive_decision():
    """빠른 주행 의사결정"""
    global last_turn_direction, turn_recovery_count

    # 장애물 체크 (우선순위 1)
    distance = get_smoothed_distance()
    if distance < current_safe_distance:
        avoid_obstacle()
        return "obstacle_avoided"

    # 라인 추적 (우선순위 2)
    line_position = analyze_line_position()

    if line_position == "left":
        turn_left()
        last_turn_direction = "left"
        turn_recovery_count = 0
        return "turn_left"

    elif line_position == "right":
        turn_right()
        last_turn_direction = "right"
        turn_recovery_count = 0
        return "turn_right"

    elif line_position == "center":
        # 중앙 감지 시 마지막 방향의 반대로 미세 조정
        if last_turn_direction == "left":
            slight_right()
            return "slight_right"
        elif last_turn_direction == "right":
            slight_left()
            return "slight_left"
        else:
            go_forward()
            return "forward"

    elif line_position == "none":
        # 라인 없음 - 마지막 방향으로 복구 시도하되 계속 주행
        turn_recovery_count += 1

        if turn_recovery_count < 5:  # 복구 시도 횟수 증가 (3→5)
            if last_turn_direction == "left":
                turn_left()
                return "recovery_left"
            elif last_turn_direction == "right":
                turn_right()
                return "recovery_right"
            else:
                go_forward()
                return "search_forward"
        elif turn_recovery_count < 10:  # 추가 복구 시도 (넓은 서치)
            # 더 넓은 범위에서 라인 탐색 - 교대로 좌우 회전
            if turn_recovery_count % 2 == 0:
                turn_left()
                return "wide_search_left"
            else:
                turn_right()
                return "wide_search_right"
        else:
            # 장시간 라인을 찾지 못한 경우 - 직진하며 탐색 계속
            go_forward()
            turn_recovery_count = 0  # 카운터 리셋하여 다시 시도
            last_turn_direction = "none"  # 방향 기록 리셋
            return "continue_search"

    else:
        go_forward()
        return "forward"


# ============================================================================
# 키보드 입력 처리 (논블로킹)
# ============================================================================


def get_single_key():
    """논블로킹 단일 키 입력"""
    try:
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                char = sys.stdin.read(1)
                return char.lower()
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        else:
            return None
    except:
        return None


def print_performance_menu():
    """고성능 제어 메뉴 출력"""
    print("\n" + "=" * 75)
    print("⚡ 고성능 자율주행 제어 메뉴")
    print("=" * 75)

    # 현재 설정값 상세 정보
    print("📊 현재 성능 및 설정 정보:")
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
    print(
        f"  🏃 의사결정 주기: {current_decision_interval:4.2f}s (범위: 0.05-1.0s, 기본값: {DECISION_INTERVAL:.2f}s)"
    )
    print(
        f"  📡 센서 읽기 주기: {current_sensor_interval:4.2f}s (범위: 0.01-0.5s, 기본값: {SENSOR_READ_INTERVAL:.2f}s)"
    )
    print(f"  🕐 수동 동작시간: {MOTOR_SLEEP_TIME:4.1f}s")

    print("\n🚦 주행 제어:")
    print("  s + Enter: 자동 주행 시작 (고성능 모드)")
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

    print("\n⚡ 반응속도 조절 (고성능 기능):")
    print("  z,c: 의사결정 주기 -0.05s/+0.05s (빠른 판단/느린 판단)")
    print("  v,b: 센서 읽기 주기 -0.01s/+0.01s (빠른 센싱/느린 센싱)")

    print("\n💡 고성능 팁:")
    print("  • 멀티스레드로 센서 데이터 병렬 수집")
    print("  • 센서 데이터 스무딩으로 노이즈 제거")
    print("  • 의사결정 주기 조절로 반응속도 최적화")
    print("  • 지속적인 자율주행 - 라인 없어도 계속 탐색")
    print("  • 장애물 회피 후 즉시 라인 추적 재개")
    print("  • 모든 키는 Enter 없이 즉시 반응 (s 제외)")
    print("  • q 키 또는 Ctrl+C로 설정값 표시 후 안전 종료")
    print("  h: 이 메뉴 다시 보기")
    print("=" * 75)


def handle_fast_keyboard_input():
    """빠른 키보드 입력 처리"""
    global current_forward_speed, current_low_turn_speed, current_high_turn_speed
    global current_safe_distance, current_avoid_time, current_decision_interval, current_sensor_interval
    global autonomous_mode, manual_control_active, running

    print("\n⚡ 고성능 키보드 제어 활성화 - 멀티스레드 기반 빠른 반응")
    print("'s' 명령만 Enter 키 필요, 나머지는 키만 누르면 즉시 반응")
    print("Ctrl+C로 안전하게 종료 가능")

    while running:
        try:
            # 현재 상태를 한 줄로 표시
            if autonomous_mode:
                status = "🚗 자동"
            elif manual_control_active:
                status = "🎮 수동"
            else:
                status = "⏸️ 대기"

            print(
                f"\r상태: {status} | 의사결정: {current_decision_interval:.2f}s | 센서: {current_sensor_interval:.2f}s | h=도움말",
                end="",
                flush=True,
            )

            # 단일 키 입력 받기
            key = get_single_key()

            if key is None:
                time.sleep(0.01)  # CPU 사용률 최적화
                continue

            # 키 처리 (즉시 반응)
            if key == "h":
                print("\n")
                print_performance_menu()
            elif key == "q":
                print("\n🚪 프로그램 종료 요청")
                show_final_settings()
                running = False
                break
            elif key == "s":
                print(
                    f"\n's' 입력됨. 고성능 자동 주행을 시작하려면 Enter를 누르세요: ",
                    end="",
                    flush=True,
                )
                confirm = input().strip().lower()
                if confirm == "":
                    if not autonomous_mode:
                        print("⚡ 고성능 자동 주행 시작")
                        autonomous_mode = True
                        manual_control_active = False
                    else:
                        print("이미 자동 주행 중")
                else:
                    print("취소됨")
            elif key == "p":
                print("\n🛑 즉시 정지 - 모든 동작 중단")
                emergency_stop()
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
            # 속도 조절 키들
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
            # 반응속도 조절 키들 (고성능 기능)
            elif key == "z":
                current_decision_interval = max(0.05, current_decision_interval - 0.05)
                print(
                    f"\n⚡ 의사결정 주기: {current_decision_interval:.2f}s (더 빠른 판단)"
                )
            elif key == "c":
                current_decision_interval = min(1.0, current_decision_interval + 0.05)
                print(
                    f"\n⚡ 의사결정 주기: {current_decision_interval:.2f}s (더 신중한 판단)"
                )
            elif key == "v":
                current_sensor_interval = max(0.01, current_sensor_interval - 0.01)
                print(
                    f"\n📡 센서 읽기 주기: {current_sensor_interval:.2f}s (더 빠른 센싱)"
                )
            elif key == "b":
                current_sensor_interval = min(0.5, current_sensor_interval + 0.01)
                print(
                    f"\n📡 센서 읽기 주기: {current_sensor_interval:.2f}s (더 안정적 센싱)"
                )
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


# ============================================================================
# 초기화 및 정리 함수
# ============================================================================


def setup():
    """하드웨어 초기화"""
    global line_sensor, motor, ultrasonic

    try:
        if LineSensorController:
            line_sensor = LineSensorController()
            print("✓ 라인 센서 초기화")

        if GearMotorController:
            motor = GearMotorController()
            print("✓ 모터 컨트롤러 초기화")

        if UltrasonicSensor:
            ultrasonic = UltrasonicSensor()
            print("✓ 초음파 센서 초기화")

        if not (LineSensorController and GearMotorController and UltrasonicSensor):
            print("Simulation mode")

        return True

    except Exception as e:
        print(f"Setup error: {e}")
        return False


def emergency_stop():
    """긴급 정지"""
    try:
        if motor:
            motor.motor_stop()
            print("✓ 모터 긴급 정지")
    except:
        pass


def show_final_settings():
    """종료 시 현재 설정값 표시"""
    print("\n" + "=" * 60)
    print("📊 고성능 자율주행 - 종료 시점 설정값 요약")
    print("=" * 60)
    print(f"🚗 전진 속도:     {current_forward_speed:3d}% (기본값: {FORWARD_SPEED}%)")
    print(f"🔄 약한 회전:     {current_low_turn_speed:3d}% (기본값: {LOW_TURN_SPEED}%)")
    print(
        f"⚡ 강한 회전:     {current_high_turn_speed:3d}% (기본값: {HIGH_TURN_SPEED}%)"
    )
    print(f"🛡️ 안전 거리:     {current_safe_distance:3d}cm (기본값: {SAFE_DISTANCE}cm)")
    print(f"⏱️ 회피 시간:     {current_avoid_time/10:4.1f}s (기본값: {AVOID_TIME:.1f}s)")
    print(
        f"🏃 의사결정 주기: {current_decision_interval:4.2f}s (기본값: {DECISION_INTERVAL:.2f}s)"
    )
    print(
        f"📡 센서 읽기 주기: {current_sensor_interval:4.2f}s (기본값: {SENSOR_READ_INTERVAL:.2f}s)"
    )
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
    if abs(current_decision_interval - DECISION_INTERVAL) > 0.01:
        changed_settings.append(
            f"의사결정주기: {DECISION_INTERVAL:.2f}s → {current_decision_interval:.2f}s"
        )
    if abs(current_sensor_interval - SENSOR_READ_INTERVAL) > 0.005:
        changed_settings.append(
            f"센서읽기주기: {SENSOR_READ_INTERVAL:.2f}s → {current_sensor_interval:.2f}s"
        )

    if changed_settings:
        print("\n🔄 기본값에서 변경된 설정:")
        for change in changed_settings:
            print(f"  • {change}")
    else:
        print("\n✅ 모든 설정이 기본값과 동일")

    print("=" * 60)


def cleanup():
    """안전한 종료"""
    global running, autonomous_mode, manual_control_active

    try:
        print("\n⚡ 고성능 자율주행 안전한 종료 중...")

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

        print("✅ 고성능 자율주행 안전한 종료 완료")

    except Exception as e:
        print(f"⚠️ 종료 중 오류: {e}")
    finally:
        print("\n")


def signal_handler(signum, frame):
    """시그널 핸들러 (Ctrl+C 처리)"""
    global running
    print("\n시그널 감지 - 안전 종료 중...")
    running = False


# ============================================================================
# 메인 함수
# ============================================================================


def main():
    """메인 함수 - 고성능 멀티스레드 자율주행"""
    global running, autonomous_mode

    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)

    print("⚡ 고성능 자율주행 로봇 시작")
    print("=" * 60)
    print("특징:")
    print("- 멀티스레드 센서 데이터 수집")
    print("- 0.2초 단위 빠른 의사결정")
    print("- 실시간 반응속도 조절")
    print("- 센서 데이터 스무딩 (노이즈 제거)")
    print("=" * 60)

    if not setup():
        print("Setup failed")
        return

    try:
        print("\n⚡ 고성능 키보드 제어 모드 시작")
        print("'h' 키를 눌러 제어 방법을 확인하세요")

        # 제어 가이드 출력
        print_performance_menu()

        # 센서 데이터 수집 스레드 시작
        line_thread = threading.Thread(target=line_sensor_thread, daemon=True)
        ultrasonic_thread = threading.Thread(
            target=ultrasonic_sensor_thread, daemon=True
        )

        line_thread.start()
        ultrasonic_thread.start()

        # 키보드 입력 스레드 시작
        keyboard_thread = threading.Thread(
            target=handle_fast_keyboard_input, daemon=True
        )
        keyboard_thread.start()

        # 메인 루프 - 고성능 의사결정
        last_decision_time = time.time()
        decision_count = 0

        while running:
            try:
                current_time = time.time()

                if (
                    autonomous_mode
                    and (current_time - last_decision_time) >= current_decision_interval
                ):
                    # 고성능 의사결정 실행
                    decision = fast_drive_decision()
                    last_decision_time = current_time
                    decision_count += 1

                    # 주기적으로 성능 정보 출력 (10초마다)
                    if decision_count % (10.0 / current_decision_interval) == 0:
                        decisions_per_sec = 1.0 / current_decision_interval
                        print(
                            f"\n⚡ 성능: {decisions_per_sec:.1f} 결정/초, 마지막 결정: {decision}, 총 결정: {decision_count}"
                        )

                else:
                    # 수동 모드 - CPU 사용률 최적화
                    time.sleep(0.01)

            except KeyboardInterrupt:
                print("\n\n⚠️ Ctrl+C 감지 - 긴급 정지 중...")
                emergency_stop()
                running = False
                break

    except KeyboardInterrupt:
        print("\n\n⚠️ Ctrl+C 감지 - 안전 종료 중...")
        emergency_stop()
        running = False
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        emergency_stop()
        running = False
    finally:
        cleanup()
        print("🏁 고성능 자율주행 프로그램 완전 종료")


if __name__ == "__main__":
    main()
