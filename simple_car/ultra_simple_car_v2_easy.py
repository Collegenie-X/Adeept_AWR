#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
초간단 자율 주행차 v2 Easy (고등학생용)
Ultra Simple Autonomous Car v2 Easy for High School Students

개선 사항:
1. 각 단계 실행 후 자동으로 메뉴로 돌아가기
2. 시간 제한으로 간단하게 구현
3. LEFT/RIGHT 개별 속도 설정
4. 로터리 감지 기능
"""

import time

# 하드웨어 가져오기
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hardware.test_line_sensors import LineSensorController
    from hardware.test_gear_motors import GearMotorController
    from hardware.test_ultrasonic_sensor import UltrasonicSensor

    print("✓ 실제 하드웨어 사용")
    SIMULATION = False
except ImportError:
    print("⚠️ 시뮬레이션 모드")
    SIMULATION = True

# ==================== 설정값 (단계별 학습용) ====================
# 기본 주행 속도
FORWARD_SPEED = 80  # 직진 속도

# 좌회전 세부 설정
LEFT_TURN_RIGHT_MOTOR = 100  # 좌회전시 우측 모터 (높은 속도)
LEFT_TURN_LEFT_MOTOR = 30  # 좌회전시 좌측 모터 (낮은 속도)

# 우회전 세부 설정
RIGHT_TURN_LEFT_MOTOR = 100  # 우회전시 좌측 모터 (높은 속도)
RIGHT_TURN_RIGHT_MOTOR = 30  # 우회전시 우측 모터 (낮은 속도)

# 장애물 회피 설정
SAFE_DISTANCE = 15  # 장애물 안전 거리 (cm)
AVOID_TIME = 0.8  # 회피 동작 시간 (초)

# 로터리 감지 설정 (새로운 기능!)
ROTARY_DETECTION_TIME = 2.0  # 로터리 감지 시간 (초)
ROTARY_SAFE_SPEED = 40  # 로터리에서 안전 속도
ROTARY_LINE_CHANGE_THRESHOLD = 5  # 라인 변화 임계값 (횟수)

# 단계별 실행 시간
STEP1_TIME = 15  # Step 1 실행 시간 (초)
STEP2_TIME = 20  # Step 2 실행 시간 (초)
STEP3_TIME = 25  # Step 3 실행 시간 (초)

# 하드웨어 객체들
line_sensor = None
motor = None
ultrasonic = None

# 로터리 감지용 변수들
line_change_count = 0
last_line_position = "center"
rotary_mode = False
rotary_start_time = 0


def setup():
    """하드웨어 준비"""
    global line_sensor, motor, ultrasonic

    if not SIMULATION:
        try:
            line_sensor = LineSensorController()
            motor = GearMotorController()
            ultrasonic = UltrasonicSensor()
            print("✓ 하드웨어 준비 완료")
            return True
        except Exception as e:
            print(f"❌ 하드웨어 오류: {e}")
            return False
    else:
        print("✓ 시뮬레이션 준비 완료")
        return True


def read_line():
    """라인 위치 읽기"""
    if line_sensor:
        line_info = line_sensor.get_line_position()
        position = line_info["position"]

        if position is None:
            return "none"
        elif position < -0.3:
            return "left"
        elif position > 0.3:
            return "right"
        else:
            return "center"
    else:
        # 시뮬레이션 (로터리 시뮬레이션 포함)
        import random

        # 로터리 시뮬레이션: 가끔 빠른 라인 변화 생성
        if random.random() < 0.05:  # 5% 확률로 로터리 시뮬레이션
            return random.choice(["left", "right", "center", "none", "left", "right"])
        else:
            return random.choice(["left", "center", "right", "none"])


def read_distance():
    """앞의 거리 읽기"""
    if ultrasonic:
        distance = ultrasonic.measure_distance()
        return distance if distance else 999
    else:
        # 시뮬레이션
        import random

        if random.random() < 0.08:  # 8% 확률로 장애물
            distance = random.randint(5, SAFE_DISTANCE - 1)
            print(f"🚨 시뮬레이션 장애물: {distance}cm")
            return distance
        else:
            distance = random.randint(SAFE_DISTANCE + 10, 100)
            return distance


def check_rotary(current_line):
    """로터리(회전교차로) 감지 함수 - 새로운 기능!"""
    global line_change_count, last_line_position, rotary_mode, rotary_start_time

    # 라인 위치가 변경되었는지 확인
    if current_line != last_line_position:
        line_change_count += 1
        last_line_position = current_line
        print(f"  📊 라인 변화 감지: {line_change_count}회")

    # 로터리 감지 조건: 짧은 시간에 많은 라인 변화
    if line_change_count >= ROTARY_LINE_CHANGE_THRESHOLD and not rotary_mode:
        rotary_mode = True
        rotary_start_time = time.time()
        line_change_count = 0  # 카운트 리셋
        print("🌀 로터리 감지! 안전 모드로 전환")
        return True

    # 로터리 모드에서 일정 시간 경과 시 해제
    if rotary_mode and (time.time() - rotary_start_time) > ROTARY_DETECTION_TIME:
        rotary_mode = False
        print("✅ 로터리 통과 완료! 정상 모드로 복귀")
        return False

    return rotary_mode


def stop():
    """정지"""
    if motor:
        motor.motor_stop()
        print("⏹️ 정지")
    else:
        print("시뮬레이션: 정지")


def go_forward(speed=None):
    """직진"""
    speed = speed or FORWARD_SPEED
    if motor:
        motor.set_motor_speed("A", speed)  # 오른쪽
        motor.set_motor_speed("B", speed)  # 왼쪽
        print(f"⬆️ 직진 (속도: {speed})")
    else:
        print(f"시뮬레이션: 직진 (속도: {speed})")


def turn_left():
    """좌회전 (개별 속도 설정)"""
    if motor:
        motor.set_motor_speed("A", LEFT_TURN_RIGHT_MOTOR)  # 오른쪽: 높은 속도
        motor.set_motor_speed("B", -LEFT_TURN_LEFT_MOTOR)  # 왼쪽: 낮은 속도 후진
        print(f"⬅️ 좌회전 (우측:{LEFT_TURN_RIGHT_MOTOR}, 좌측:-{LEFT_TURN_LEFT_MOTOR})")
    else:
        print(
            f"시뮬레이션: 좌회전 (우측:{LEFT_TURN_RIGHT_MOTOR}, 좌측:-{LEFT_TURN_LEFT_MOTOR})"
        )


def turn_right():
    """우회전 (개별 속도 설정)"""
    if motor:
        motor.set_motor_speed("A", -RIGHT_TURN_RIGHT_MOTOR)  # 오른쪽: 낮은 속도 후진
        motor.set_motor_speed("B", RIGHT_TURN_LEFT_MOTOR)  # 왼쪽: 높은 속도
        print(
            f"➡️ 우회전 (우측:-{RIGHT_TURN_RIGHT_MOTOR}, 좌측:{RIGHT_TURN_LEFT_MOTOR})"
        )
    else:
        print(
            f"시뮬레이션: 우회전 (우측:-{RIGHT_TURN_RIGHT_MOTOR}, 좌측:{RIGHT_TURN_LEFT_MOTOR})"
        )


def avoid_obstacle():
    """장애물 피하기 (좌회전 → 직진 → 우회전)"""
    print("🚨 장애물 회피 시작!")

    # 1단계: 좌회전
    print("  1. 좌회전으로 피하기")
    turn_left()
    time.sleep(AVOID_TIME)

    # 2단계: 직진으로 지나가기
    print("  2. 직진으로 지나가기")
    go_forward()
    time.sleep(AVOID_TIME)

    # 3단계: 우회전으로 원래 방향
    print("  3. 우회전으로 복귀")
    turn_right()
    time.sleep(AVOID_TIME)

    print("✅ 장애물 회피 완료!")


def drive_basic():
    """기본 주행 모드 (Step 1)"""
    line_position = read_line()

    if line_position == "center":
        go_forward()
    elif line_position == "left":
        turn_right()
    elif line_position == "right":
        turn_left()
    else:  # none
        turn_left()  # 라인 찾기


def drive_with_obstacle():
    """장애물 회피 포함 주행 (Step 2)"""
    # 1단계: 장애물 확인
    distance = read_distance()

    if distance < SAFE_DISTANCE:
        avoid_obstacle()
        return

    # 2단계: 기본 라인 추적
    drive_basic()


def drive_with_rotary():
    """로터리 감지 포함 주행 (Step 3 - 최고급)"""
    # 1단계: 장애물 확인
    distance = read_distance()
    if distance < SAFE_DISTANCE:
        avoid_obstacle()
        return

    # 2단계: 라인 읽기
    line_position = read_line()

    # 3단계: 로터리 감지
    is_rotary = check_rotary(line_position)

    # 4단계: 주행 모드 결정
    if is_rotary:
        # 로터리 모드: 안전하게 천천히
        print(f"🌀 로터리 안전 주행: {line_position}")
        if line_position == "center":
            go_forward(ROTARY_SAFE_SPEED)
        elif line_position == "left":
            go_forward(ROTARY_SAFE_SPEED // 2)  # 더 천천히
        elif line_position == "right":
            go_forward(ROTARY_SAFE_SPEED // 2)  # 더 천천히
        else:  # none
            go_forward(ROTARY_SAFE_SPEED // 3)  # 매우 천천히
    else:
        # 일반 모드: 정상 속도
        drive_basic()


def show_progress_bar(current_time, total_time, step_name):
    """진행 상황 바 표시"""
    progress = min(current_time / total_time, 1.0)
    bar_length = 30
    filled = int(bar_length * progress)
    bar = "█" * filled + "░" * (bar_length - filled)
    remaining = total_time - current_time
    print(
        f"\r{step_name} │{bar}│ {progress*100:.0f}% ({remaining:.0f}초 남음)",
        end="",
        flush=True,
    )


def step1_basic_line_following():
    """Step 1: 기본 라인 추적 수업 (시간 제한)"""
    print("\n" + "=" * 50)
    print("📚 Step 1: 기본 라인 추적 수업")
    print("=" * 50)
    print("학습 내용:")
    print("- 라인 센서로 선의 위치 감지")
    print("- LEFT/RIGHT 개별 모터 속도 제어")
    print("- 기본적인 if-else 조건문 사용")
    print("=" * 50)

    if not setup():
        return

    print(f"🚀 Step 1 시작! ({STEP1_TIME}초간 실행)")
    start_time = time.time()

    try:
        while True:
            current_time = time.time() - start_time

            # 시간 종료 체크
            if current_time >= STEP1_TIME:
                print(f"\n⏰ {STEP1_TIME}초 완료! 메뉴로 돌아갑니다")
                break

            # 진행 상황 표시 (2초마다)
            if int(current_time) % 2 == 0:
                show_progress_bar(current_time, STEP1_TIME, "Step 1")

            drive_basic()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n⌨️ Ctrl+C로 중단")
    finally:
        cleanup()


def step2_obstacle_avoidance():
    """Step 2: 장애물 회피 수업 (시간 제한)"""
    print("\n" + "=" * 50)
    print("📚 Step 2: 장애물 회피 수업")
    print("=" * 50)
    print("학습 내용:")
    print("- 초음파 센서로 거리 측정")
    print("- 3단계 장애물 회피 알고리즘")
    print("- 우선순위 기반 의사결정")
    print("=" * 50)

    if not setup():
        return

    print(f"🚀 Step 2 시작! ({STEP2_TIME}초간 실행)")
    start_time = time.time()

    try:
        while True:
            current_time = time.time() - start_time

            # 시간 종료 체크
            if current_time >= STEP2_TIME:
                print(f"\n⏰ {STEP2_TIME}초 완료! 메뉴로 돌아갑니다")
                break

            # 진행 상황 표시 (2초마다)
            if int(current_time) % 2 == 0:
                show_progress_bar(current_time, STEP2_TIME, "Step 2")

            drive_with_obstacle()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n⌨️ Ctrl+C로 중단")
    finally:
        cleanup()


def step3_rotary_detection():
    """Step 3: 로터리 감지 수업 (시간 제한)"""
    print("\n" + "=" * 50)
    print("📚 Step 3: 로터리 감지 수업 (고급)")
    print("=" * 50)
    print("학습 내용:")
    print("- 패턴 인식을 통한 로터리 감지")
    print("- 상태 관리 (rotary_mode)")
    print("- 적응형 속도 제어")
    print("- 복합 센서 데이터 처리")
    print("=" * 50)

    if not setup():
        return

    print(f"🚀 Step 3 시작! ({STEP3_TIME}초간 실행)")
    start_time = time.time()

    try:
        while True:
            current_time = time.time() - start_time

            # 시간 종료 체크
            if current_time >= STEP3_TIME:
                print(f"\n⏰ {STEP3_TIME}초 완료! 메뉴로 돌아갑니다")
                break

            # 진행 상황 표시 (2초마다)
            if int(current_time) % 2 == 0:
                show_progress_bar(current_time, STEP3_TIME, "Step 3")

            drive_with_rotary()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n⌨️ Ctrl+C로 중단")
    finally:
        cleanup()


def show_settings():
    """현재 설정 표시"""
    print("\n" + "=" * 50)
    print("🚗 초간단 자율 주행차 v2 Easy 설정")
    print("=" * 50)
    print("📈 기본 속도:")
    print(f"  직진 속도: {FORWARD_SPEED}")
    print()
    print("🔄 회전 속도 (개별 설정):")
    print(
        f"  좌회전 - 우측모터: {LEFT_TURN_RIGHT_MOTOR}, 좌측모터: {LEFT_TURN_LEFT_MOTOR}"
    )
    print(
        f"  우회전 - 우측모터: {RIGHT_TURN_RIGHT_MOTOR}, 좌측모터: {RIGHT_TURN_LEFT_MOTOR}"
    )
    print()
    print("🛡️ 장애물 회피:")
    print(f"  안전 거리: {SAFE_DISTANCE}cm")
    print(f"  회피 시간: {AVOID_TIME}초")
    print()
    print("🌀 로터리 감지:")
    print(f"  감지 시간: {ROTARY_DETECTION_TIME}초")
    print(f"  안전 속도: {ROTARY_SAFE_SPEED}")
    print(f"  라인 변화 임계값: {ROTARY_LINE_CHANGE_THRESHOLD}회")
    print()
    print("⏰ 단계별 실행 시간:")
    print(f"  Step 1: {STEP1_TIME}초")
    print(f"  Step 2: {STEP2_TIME}초")
    print(f"  Step 3: {STEP3_TIME}초")
    print("=" * 50)


def cleanup():
    """정리"""
    try:
        stop()
        if line_sensor:
            line_sensor.cleanup()
        if motor:
            motor.cleanup()
        if ultrasonic:
            ultrasonic.cleanup()
        print("✓ 정리 완료")
    except:
        pass


def show_menu():
    """메뉴 표시"""
    print("\n" + "=" * 60)
    print("🎓 초간단 자율 주행차 v2 Easy - 단계별 학습")
    print("=" * 60)
    print(f"1. Step 1: 기본 라인 추적 (초급) - {STEP1_TIME}초 자동 종료")
    print(f"2. Step 2: 장애물 회피 추가 (중급) - {STEP2_TIME}초 자동 종료")
    print(f"3. Step 3: 로터리 감지 추가 (고급) - {STEP3_TIME}초 자동 종료")
    print("4. 설정 보기")
    print("5. 전체 기능 실행 (무제한)")
    print("0. 종료")
    print("=" * 60)
    print("💡 팁: 각 단계는 자동으로 종료되어 메뉴로 돌아갑니다!")


def main():
    """메인 함수"""
    while True:
        show_menu()

        try:
            choice = input("선택하세요 (0-5): ").strip()

            if choice == "1":
                step1_basic_line_following()

            elif choice == "2":
                step2_obstacle_avoidance()

            elif choice == "3":
                step3_rotary_detection()

            elif choice == "4":
                show_settings()

            elif choice == "5":
                print("\n🚀 전체 기능 실행!")
                print("Ctrl+C로 중단할 수 있습니다")

                if not setup():
                    continue

                try:
                    while True:
                        drive_with_rotary()
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\n⌨️ Ctrl+C로 중단")
                finally:
                    cleanup()

            elif choice == "0":
                print("👋 프로그램 종료")
                break

            else:
                print("❌ 잘못된 선택입니다")

        except KeyboardInterrupt:
            print("\n\n⌨️ 프로그램 종료")
            break


if __name__ == "__main__":
    main()
