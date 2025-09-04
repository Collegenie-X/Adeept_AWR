#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
함수형 라인 추적 자율 주행차 (영어 코딩 + 한글 주석)
Functional Line Following Car with English Coding + Korean Comments

기능:
- 함수형 프로그래밍 방식 (영어 함수명 + 한글 주석)
- 라인 센서 기반 추적
- 초음파 센서 장애물 회피 (후진 금지)
- 자연스러운 회전 (한쪽 직진 + 반대쪽 후진)
- 전역 상수로 속도 조절
"""

import time
import threading
import sys
import random

# ==================== 전역 상수 (속도 조절) ====================
# 직진 속도 설정
FORWARD_SPEED = 50  # 직진 기본 속도 (0-100)

# 좌회전 속도 설정 (라인이 우측으로 치우쳤을 때 좌회전 필요)
# 자연스러운 좌회전: 오른쪽 직진 + 왼쪽 후진
LEFT_TURN_RIGHT_MOTOR_SPEED = 50  # 우측 모터 속도 (직진)
LEFT_TURN_LEFT_MOTOR_SPEED = -30  # 좌측 모터 속도 (후진)

# 우회전 속도 설정 (라인이 좌측으로 치우쳤을 때 우회전 필요)
# 자연스러운 우회전: 왼쪽 직진 + 오른쪽 후진
RIGHT_TURN_LEFT_MOTOR_SPEED = 50  # 좌측 모터 속도 (직진)
RIGHT_TURN_RIGHT_MOTOR_SPEED = -30  # 우측 모터 속도 (후진)

# 라인 탐색 속도 (라인을 잃었을 때)
LINE_SEARCH_ROTATION_SPEED = 30  # 탐색 회전 속도

# 장애물 회피 속도 설정 (후진 금지 - 좌회전→직진→우회전 패턴)
OBSTACLE_AVOID_LEFT_TURN_SPEED = 50  # 좌회전 회피 속도
OBSTACLE_AVOID_FORWARD_SPEED = 45  # 회피 중 직진 속도
OBSTACLE_AVOID_RIGHT_TURN_SPEED = 50  # 우회전 복귀 속도
OBSTACLE_AVOID_SLOW_DOWN_RATIO = 0.6  # 감속 비율 (0.0-1.0)

# 장애물 회피 시간 설정 (초)
OBSTACLE_AVOID_LEFT_TURN_TIME = 0.8  # 1단계: 좌회전 지속 시간
OBSTACLE_AVOID_FORWARD_TIME = 1.2  # 2단계: 직진 회피 지속 시간
OBSTACLE_AVOID_RIGHT_TURN_TIME = 0.8  # 3단계: 우회전 복귀 지속 시간

# 거리 임계값 설정 (cm)
DANGER_DISTANCE_THRESHOLD = 20  # 즉시 회피가 필요한 거리
WARNING_DISTANCE_THRESHOLD = 35  # 회피 준비가 필요한 거리
SAFE_DISTANCE_THRESHOLD = 50  # 정상 주행 가능한 거리

# 제어 주기
CONTROL_FREQUENCY = 20  # Hz (20Hz = 50ms)
# ================================================================

# 하드웨어 모듈 임포트
try:
    from hardware.test_line_sensors import LineSensorController
    from hardware.test_gear_motors import GearMotorController
    from hardware.test_ultrasonic_sensor import UltrasonicSensor

    hardware_available = True
    print("✓ 하드웨어 모듈 로드 완료")
except ImportError as e:
    print(f"하드웨어 모듈 없음: {e}")
    print("시뮬레이션 모드로 실행")
    hardware_available = False

# ==================== 전역 변수 ====================
line_sensor = None
motor_controller = None
ultrasonic_sensor = None
is_running = False
last_line_position = 0
line_lost_counter = 0

# 장애물 회피 상태 관리
obstacle_avoidance_active = False
avoidance_stage = 0  # 0:없음, 1:좌회전, 2:직진, 3:우회전
avoidance_start_time = 0

# 통계 정보
statistics = {
    "start_time": 0,
    "total_driving_time": 0,
    "left_turn_count": 0,
    "right_turn_count": 0,
    "line_lost_count": 0,
    "obstacle_detected_count": 0,
    "avoidance_action_count": 0,
}


# ==================== 하드웨어 초기화 함수 ====================
def initialize_hardware():
    """하드웨어 컨트롤러들을 초기화한다"""
    global line_sensor, motor_controller, ultrasonic_sensor

    print("하드웨어 초기화 중...")

    if hardware_available:
        try:
            # 라인 센서 초기화
            line_sensor = LineSensorController()
            print("✓ 라인 센서 초기화 완료")

            # 모터 컨트롤러 초기화
            motor_controller = GearMotorController()
            print("✓ 모터 컨트롤러 초기화 완료")

            # 초음파 센서 초기화
            ultrasonic_sensor = UltrasonicSensor()
            print("✓ 초음파 센서 초기화 완료")

            return True

        except Exception as e:
            print(f"하드웨어 초기화 실패: {e}")
            print("시뮬레이션 모드로 전환")
            return False
    else:
        print("시뮬레이션 모드로 실행")
        return False


def print_current_settings():
    """현재 설정된 속도 값들을 출력한다"""
    print("\n" + "=" * 60)
    print("🚗 함수형 라인 추적 자율 주행차 설정 (영어코딩+한글주석)")
    print("=" * 60)
    print(f"직진 속도: {FORWARD_SPEED}%")
    print(
        f"좌회전: 우측모터 {LEFT_TURN_RIGHT_MOTOR_SPEED}% (직진), 좌측모터 {LEFT_TURN_LEFT_MOTOR_SPEED}% (후진)"
    )
    print(
        f"우회전: 좌측모터 {RIGHT_TURN_LEFT_MOTOR_SPEED}% (직진), 우측모터 {RIGHT_TURN_RIGHT_MOTOR_SPEED}% (후진)"
    )
    print(f"라인 탐색 속도: {LINE_SEARCH_ROTATION_SPEED}%")
    print()
    print("🛡️ 장애물 회피 설정 (후진 금지)")
    print(f"위험 거리: {DANGER_DISTANCE_THRESHOLD}cm (즉시 회피)")
    print(f"경고 거리: {WARNING_DISTANCE_THRESHOLD}cm (회피 준비)")
    print(f"안전 거리: {SAFE_DISTANCE_THRESHOLD}cm (정상 주행)")
    print(
        f"회피 좌회전: {OBSTACLE_AVOID_LEFT_TURN_SPEED}% ({OBSTACLE_AVOID_LEFT_TURN_TIME}초)"
    )
    print(
        f"회피 직진: {OBSTACLE_AVOID_FORWARD_SPEED}% ({OBSTACLE_AVOID_FORWARD_TIME}초)"
    )
    print(
        f"회피 우회전: {OBSTACLE_AVOID_RIGHT_TURN_SPEED}% ({OBSTACLE_AVOID_RIGHT_TURN_TIME}초)"
    )
    print(f"감속 비율: {OBSTACLE_AVOID_SLOW_DOWN_RATIO}")
    print("=" * 60)


# ==================== 센서 읽기 함수 ====================
def read_line_sensor_data():
    """라인 센서 데이터를 읽어서 위치 정보를 반환한다"""
    if line_sensor:
        try:
            line_info = line_sensor.get_line_position()
            return line_info
        except Exception as e:
            print(f"라인 센서 읽기 오류: {e}")
            return {"position": None, "description": "센서 오류", "pattern": "---"}
    else:
        # 시뮬레이션 데이터
        scenarios = [
            (0, "중앙"),
            (-0.3, "좌측 약간"),
            (0.3, "우측 약간"),
            (-0.8, "좌측 많이"),
            (0.8, "우측 많이"),
            (None, "라인 없음"),
        ]
        position, description = random.choice(scenarios)
        pattern = "101" if position is None else "010"
        return {"position": position, "description": description, "pattern": pattern}


def measure_ultrasonic_distance():
    """초음파 센서로 전방 거리를 측정한다"""
    if ultrasonic_sensor:
        try:
            distance = ultrasonic_sensor.measure_distance()
            return distance if distance is not None else 999  # 측정 실패 시 안전한 거리
        except Exception as e:
            print(f"초음파 센서 읽기 오류: {e}")
            return 999
    else:
        # 시뮬레이션: 랜덤 거리 (대부분 안전거리)
        if random.random() < 0.1:  # 10% 확률로 장애물
            return random.randint(10, 40)
        else:
            return random.randint(60, 200)


# ==================== 모터 제어 함수 ====================
def stop_motors():
    """모터를 정지시킨다"""
    if motor_controller:
        motor_controller.motor_stop()
        print("⏹️ 모터 정지")
    else:
        print("시뮬레이션: 모터 정지")


def set_motor_speeds(right_speed, left_speed, action_description=""):
    """좌우 모터의 속도를 개별적으로 설정한다"""
    if motor_controller:
        motor_controller.set_motor_speed("A", right_speed)  # 우측 모터
        motor_controller.set_motor_speed("B", left_speed)  # 좌측 모터
        print(f"🚗 {action_description} (우측:{right_speed}%, 좌측:{left_speed}%)")
    else:
        print(
            f"시뮬레이션: {action_description} (우측:{right_speed}%, 좌측:{left_speed}%)"
        )


def drive_forward(speed=None):
    """직진으로 주행한다"""
    speed = speed or FORWARD_SPEED
    set_motor_speeds(speed, speed, f"직진 주행 (속도: {speed}%)")


def execute_left_turn():
    """좌회전을 실행한다 (라인이 우측으로 치우쳤을 때) - 우측 직진 + 좌측 후진"""
    global statistics
    statistics["left_turn_count"] += 1
    set_motor_speeds(
        LEFT_TURN_RIGHT_MOTOR_SPEED,  # 우측: 직진
        LEFT_TURN_LEFT_MOTOR_SPEED,  # 좌측: 후진
        "좌회전 실행 (우측직진+좌측후진)",
    )


def execute_right_turn():
    """우회전을 실행한다 (라인이 좌측으로 치우쳤을 때) - 좌측 직진 + 우측 후진"""
    global statistics
    statistics["right_turn_count"] += 1
    set_motor_speeds(
        RIGHT_TURN_RIGHT_MOTOR_SPEED,  # 우측: 후진
        RIGHT_TURN_LEFT_MOTOR_SPEED,  # 좌측: 직진
        "우회전 실행 (좌측직진+우측후진)",
    )


def search_line_by_rotation(direction="left"):
    """라인을 찾기 위해 제자리에서 회전한다"""
    if direction == "left":
        set_motor_speeds(
            LINE_SEARCH_ROTATION_SPEED, -LINE_SEARCH_ROTATION_SPEED, "좌측 라인 탐색"
        )
    else:
        set_motor_speeds(
            -LINE_SEARCH_ROTATION_SPEED, LINE_SEARCH_ROTATION_SPEED, "우측 라인 탐색"
        )


# ==================== 장애물 회피 함수 ====================
def evaluate_obstacle_danger_level(distance):
    """거리에 따른 장애물 위험도를 평가한다"""
    if distance <= DANGER_DISTANCE_THRESHOLD:
        return "danger"  # 즉시 회피 필요
    elif distance <= WARNING_DISTANCE_THRESHOLD:
        return "warning"  # 회피 준비 필요
    elif distance <= SAFE_DISTANCE_THRESHOLD:
        return "caution"  # 약간 감속
    else:
        return "safe"  # 정상 주행


def start_obstacle_avoidance():
    """3단계 장애물 회피를 시작한다 (좌회전→직진→우회전)"""
    global obstacle_avoidance_active, avoidance_stage, avoidance_start_time, statistics

    if not obstacle_avoidance_active:
        obstacle_avoidance_active = True
        avoidance_stage = 1  # 1단계: 좌회전 시작
        avoidance_start_time = time.time()
        statistics["avoidance_action_count"] += 1
        print("🚨 3단계 장애물 회피 시작!")


def execute_avoidance_stage1_left_turn():
    """1단계: 좌회전으로 장애물 회피 방향 전환"""
    set_motor_speeds(
        OBSTACLE_AVOID_LEFT_TURN_SPEED,
        -OBSTACLE_AVOID_LEFT_TURN_SPEED,
        "1단계: 좌회전 회피",
    )


def execute_avoidance_stage2_forward():
    """2단계: 직진으로 장애물 옆을 지나간다"""
    set_motor_speeds(
        OBSTACLE_AVOID_FORWARD_SPEED,
        OBSTACLE_AVOID_FORWARD_SPEED,
        "2단계: 직진 회피",
    )


def execute_avoidance_stage3_right_turn():
    """3단계: 우회전으로 원래 경로로 복귀한다"""
    set_motor_speeds(
        -OBSTACLE_AVOID_RIGHT_TURN_SPEED,
        OBSTACLE_AVOID_RIGHT_TURN_SPEED,
        "3단계: 우회전 복귀",
    )


def process_avoidance_stages():
    """현재 회피 단계에 따른 동작을 수행하고 다음 단계로 진행한다"""
    global avoidance_stage, avoidance_start_time, obstacle_avoidance_active

    if not obstacle_avoidance_active:
        return False

    current_time = time.time()
    elapsed_time = current_time - avoidance_start_time

    if avoidance_stage == 1:  # 좌회전 단계
        execute_avoidance_stage1_left_turn()
        if elapsed_time >= OBSTACLE_AVOID_LEFT_TURN_TIME:
            avoidance_stage = 2
            avoidance_start_time = current_time
            print("  → 2단계 시작: 직진 회피")

    elif avoidance_stage == 2:  # 직진 단계
        execute_avoidance_stage2_forward()
        if elapsed_time >= OBSTACLE_AVOID_FORWARD_TIME:
            avoidance_stage = 3
            avoidance_start_time = current_time
            print("  → 3단계 시작: 우회전 복귀")

    elif avoidance_stage == 3:  # 우회전 단계
        execute_avoidance_stage3_right_turn()
        if elapsed_time >= OBSTACLE_AVOID_RIGHT_TURN_TIME:
            # 회피 완료
            obstacle_avoidance_active = False
            avoidance_stage = 0
            print("✅ 장애물 회피 완료!")
            return False

    return True  # 회피 진행 중


def force_stop_obstacle_avoidance():
    """장애물 회피를 강제로 종료한다"""
    global obstacle_avoidance_active, avoidance_stage

    if obstacle_avoidance_active:
        obstacle_avoidance_active = False
        avoidance_stage = 0
        print("⚠️ 장애물 회피 강제 종료")


def apply_speed_reduction(base_speed, reduction_ratio):
    """주어진 감속 비율로 속도를 줄인다"""
    reduced_speed = int(base_speed * reduction_ratio)
    return reduced_speed


# ==================== 라인 추적 로직 함수 ====================
def execute_line_following_control_logic(line_position, line_description):
    """라인 위치에 따른 모터 제어 로직을 수행한다"""
    global last_line_position, line_lost_counter

    if line_position is None:
        # 라인 없음 - 탐색 모드
        handle_line_lost_situation()
    else:
        # 라인 감지됨 - 추적 모드
        line_lost_counter = 0
        last_line_position = line_position
        execute_line_following_drive(line_position, line_description)


def execute_line_following_drive(position, description):
    """감지된 라인 위치에 따라 주행한다"""
    if position == 0:
        # 중앙 - 직진
        drive_forward()
    elif position < 0:
        # 좌측으로 치우침 - 우회전 필요
        execute_right_turn()
    else:  # position > 0
        # 우측으로 치우침 - 좌회전 필요
        execute_left_turn()


def handle_line_lost_situation():
    """라인을 분실했을 때의 처리 로직을 수행한다"""
    global line_lost_counter, statistics

    line_lost_counter += 1

    if line_lost_counter > 5:  # 0.25초 동안 라인 분실
        if line_lost_counter == 6:  # 처음 분실 시에만 카운트
            statistics["line_lost_count"] += 1

        # 마지막 위치 기반으로 탐색 방향 결정
        if last_line_position <= 0:
            search_line_by_rotation("left")
        else:
            search_line_by_rotation("right")
    else:
        # 잠시 정지하고 대기
        stop_motors()


# ==================== 장애물 회피 로직 함수 ====================
def execute_obstacle_avoidance_control_logic(distance):
    """초음파 센서로 측정한 거리에 따른 장애물 회피 로직을 수행한다 (후진 금지)"""
    global statistics

    # 현재 회피 중이면 회피 단계 처리 우선
    if obstacle_avoidance_active:
        is_avoidance_in_progress = process_avoidance_stages()
        if is_avoidance_in_progress:
            return "avoiding"
        else:
            return "avoidance_completed"

    # 새로운 장애물 감지 시 처리
    danger_level = evaluate_obstacle_danger_level(distance)

    if danger_level == "danger":
        # 즉시 3단계 회피 시작
        statistics["obstacle_detected_count"] += 1
        start_obstacle_avoidance()
        return "avoidance_started"

    elif danger_level == "warning":
        # 준비 단계 - 다음 제어 주기에 회피 시작
        print(f"⚠️ 장애물 경고! 거리: {distance}cm - 회피 준비")
        return "avoidance_ready"

    elif danger_level == "caution":
        # 감속하여 주행
        reduced_speed = apply_speed_reduction(
            FORWARD_SPEED, OBSTACLE_AVOID_SLOW_DOWN_RATIO
        )
        drive_forward(reduced_speed)
        return "slowing_down"

    else:  # safe
        return "safe"


# ==================== 통합 제어 로직 함수 ====================
def execute_integrated_driving_control():
    """라인 추적과 장애물 회피를 통합한 주행 제어 함수 (후진 금지 회피 시스템)"""
    # 1. 초음파 센서로 전방 거리 측정
    front_distance = measure_ultrasonic_distance()

    # 2. 장애물 회피 우선 처리
    avoidance_status = execute_obstacle_avoidance_control_logic(front_distance)

    # 3. 회피 상태에 따른 제어
    if avoidance_status == "safe":
        # 정상 라인 추적
        line_info = read_line_sensor_data()
        line_position = line_info["position"]
        line_description = line_info["description"]
        line_pattern = line_info["pattern"]

        # 센서 상태 출력
        print(
            f"센서: [{line_pattern}] 위치: {line_position} - {line_description} | 거리: {front_distance}cm"
        )
        execute_line_following_control_logic(line_position, line_description)

    elif avoidance_status == "slowing_down":
        # 감속하면서 라인 추적
        line_info = read_line_sensor_data()
        line_position = line_info["position"]
        print(f"🔶 장애물 감속 주행 | 거리: {front_distance}cm | 라인: {line_position}")

    elif avoidance_status == "avoidance_ready":
        # 다음 주기에 회피 시작 예정
        print(f"⚠️ 장애물 회피 준비 | 거리: {front_distance}cm")

    elif avoidance_status == "avoidance_started":
        # 회피 시작됨
        print(f"🚨 3단계 장애물 회피 시작! | 거리: {front_distance}cm")

    elif avoidance_status == "avoiding":
        # 회피 진행 중 (좌회전→직진→우회전)
        print(
            f"🔄 장애물 회피 {avoidance_stage}단계 진행 중 | 거리: {front_distance}cm"
        )

    elif avoidance_status == "avoidance_completed":
        # 회피 완료, 다음 주기부터 정상 라인 추적
        print(f"✅ 장애물 회피 완료! 라인 추적 재개 | 거리: {front_distance}cm")


# ==================== 메인 제어 루프 함수 ====================
def execute_main_control_loop():
    """메인 제어 루프를 실행한다"""
    global is_running

    print("제어 루프 시작...")

    while is_running:
        try:
            # 통합 주행 제어
            execute_integrated_driving_control()

            # 제어 주기 대기
            time.sleep(1.0 / CONTROL_FREQUENCY)

        except Exception as e:
            print(f"❌ 제어 루프 오류: {e}")
            break

    # 안전 정지
    stop_motors()
    print("제어 루프 종료")


# ==================== 시작/정지 함수 ====================
def start_autonomous_driving():
    """자율 주행을 시작한다"""
    global is_running, statistics

    if is_running:
        print("⚠️ 이미 실행 중입니다!")
        return

    print("\n🚀 함수형 라인 추적 자율 주행 시작!")
    is_running = True
    statistics["start_time"] = time.time()

    # 제어 스레드 시작
    control_thread = threading.Thread(target=execute_main_control_loop, daemon=True)
    control_thread.start()


def stop_autonomous_driving():
    """자율 주행을 정지한다"""
    global is_running

    print("\n🛑 자율 주행 정지 중...")
    is_running = False

    # 모터 정지
    stop_motors()

    # 통계 업데이트
    update_statistics()
    print("✓ 정지 완료")


# ==================== 통계 및 모니터링 함수 ====================
def update_statistics():
    """주행 통계 정보를 업데이트한다"""
    if statistics["start_time"] > 0:
        statistics["total_driving_time"] = time.time() - statistics["start_time"]


def print_driving_statistics():
    """주행 통계를 출력한다"""
    update_statistics()

    print("\n" + "=" * 50)
    print("📊 주행 통계")
    print("=" * 50)
    print(f"총 주행 시간: {statistics['total_driving_time']:.1f}초")
    print(f"좌회전 횟수: {statistics['left_turn_count']}")
    print(f"우회전 횟수: {statistics['right_turn_count']}")
    print(f"라인 분실 횟수: {statistics['line_lost_count']}")
    print(f"장애물 감지 횟수: {statistics['obstacle_detected_count']}")
    print(f"회피 동작 횟수: {statistics['avoidance_action_count']}")

    if statistics["total_driving_time"] > 0:
        total_turns = statistics["left_turn_count"] + statistics["right_turn_count"]
        turn_frequency = total_turns / statistics["total_driving_time"]
        print(f"회전 빈도: {turn_frequency:.2f}회/초")

        if statistics["obstacle_detected_count"] > 0:
            avoidance_success_rate = (
                statistics["avoidance_action_count"]
                / statistics["obstacle_detected_count"]
            ) * 100
            print(f"회피 성공률: {avoidance_success_rate:.1f}%")

    print("=" * 50)


# ==================== 시스템 정리 함수 ====================
def cleanup_system():
    """시스템을 정리하고 하드웨어를 해제한다"""
    print("\n🧹 시스템 정리 중...")

    stop_autonomous_driving()

    # 하드웨어 정리
    try:
        if motor_controller:
            motor_controller.cleanup()
        if line_sensor:
            line_sensor.cleanup()
        if ultrasonic_sensor:
            ultrasonic_sensor.cleanup()
    except Exception as e:
        print(f"정리 중 오류: {e}")

    print("✓ 정리 완료")


# ==================== 도움말 및 사용자 인터페이스 ====================
def print_help():
    """사용법을 출력한다"""
    print("\n📋 사용법:")
    print("  s - 자율 주행 시작")
    print("  q - 정지 및 종료")
    print("  h - 도움말")
    print("  c - 현재 설정 보기")
    print("  stat - 통계 보기")
    print("  test_line - 라인 센서 테스트")
    print("  test_ultra - 초음파 센서 테스트")
    print("  test_avoid - 장애물 회피 테스트")
    print("\n💡 속도 조절:")
    print("  파일 상단의 전역 상수를 수정하세요:")
    print("  - FORWARD_SPEED: 직진 속도")
    print("  - LEFT_TURN_*: 좌회전 속도 (우측직진+좌측후진)")
    print("  - RIGHT_TURN_*: 우회전 속도 (좌측직진+우측후진)")
    print("  - OBSTACLE_AVOID_*: 장애물 회피 속도")


def test_line_sensor():
    """라인 센서를 테스트한다"""
    print("\n🧪 라인 센서 테스트 (5회)")
    for i in range(5):
        line_info = read_line_sensor_data()
        print(f"  {i+1}. {line_info}")
        time.sleep(0.5)


def test_ultrasonic_sensor():
    """초음파 센서를 테스트한다"""
    print("\n🧪 초음파 센서 테스트 (5회)")
    for i in range(5):
        distance = measure_ultrasonic_distance()
        danger_level = evaluate_obstacle_danger_level(distance)
        print(f"  {i+1}. 거리: {distance}cm - {danger_level}")
        time.sleep(0.5)


def test_obstacle_avoidance():
    """장애물 회피 시스템을 테스트한다"""
    print("\n🧪 장애물 회피 시스템 테스트")
    print("3단계 회피 동작을 시뮬레이션합니다...")

    # 회피 시작
    start_obstacle_avoidance()

    # 각 단계별 시뮬레이션
    for stage in range(1, 4):
        print(f"\n--- {stage}단계 테스트 ---")
        if stage == 1:
            execute_avoidance_stage1_left_turn()
        elif stage == 2:
            execute_avoidance_stage2_forward()
        elif stage == 3:
            execute_avoidance_stage3_right_turn()

        time.sleep(1)  # 1초간 시뮬레이션

    # 회피 완료
    force_stop_obstacle_avoidance()
    stop_motors()
    print("테스트 완료!")


def execute_interactive_control_mode():
    """대화형 제어 모드를 실행한다"""
    print("\n🎮 함수형 대화형 제어 모드 (영어코딩+한글주석)")
    print_help()

    try:
        while True:
            command = input("\n명령 입력 (h:도움말): ").strip().lower()

            if command == "s":
                start_autonomous_driving()
            elif command == "q":
                break
            elif command == "h":
                print_help()
            elif command == "c":
                print_current_settings()
            elif command == "stat":
                print_driving_statistics()
            elif command == "test_line":
                test_line_sensor()
            elif command == "test_ultra":
                test_ultrasonic_sensor()
            elif command == "test_avoid":
                test_obstacle_avoidance()
            elif command == "":
                continue
            else:
                print(
                    "❌ 알 수 없는 명령어입니다. 'h'를 입력하면 도움말을 볼 수 있습니다."
                )

    except KeyboardInterrupt:
        print("\n\n⌨️ Ctrl+C 감지됨")
    finally:
        cleanup_system()


def execute_auto_mode():
    """자동 실행 모드를 실행한다"""
    print("\n🤖 자동 실행 모드")
    print("5초 후 자동으로 라인 추적을 시작합니다...")
    print("Ctrl+C로 언제든지 중단할 수 있습니다.")

    try:
        # 5초 카운트다운
        for i in range(5, 0, -1):
            print(f"시작까지 {i}초...")
            time.sleep(1)

        start_autonomous_driving()

        # 무한 대기 (Ctrl+C까지)
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n⌨️ Ctrl+C 감지됨")
    finally:
        cleanup_system()


def main():
    """메인 함수 - 프로그램의 진입점"""
    print("🚗 함수형 라인 센서 기반 자율 주행차 (영어코딩+한글주석)")
    print("=" * 60)

    # 하드웨어 초기화
    initialize_hardware()
    print_current_settings()

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # 자동 모드
        execute_auto_mode()
    else:
        # 대화형 모드
        execute_interactive_control_mode()

    print("\n👋 프로그램 종료")


if __name__ == "__main__":
    main()
