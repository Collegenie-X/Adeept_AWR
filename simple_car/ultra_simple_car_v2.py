#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
초간단 자율 주행차 v2 (고등학생용 - 단계별 수업)
Ultra Simple Autonomous Car v2 for High School Students - Step by Step Learning

새로운 기능:
1. LEFT/RIGHT 개별 속도 설정
2. 로터리(회전교차로) 감지 및 안전 주행
3. 단계별 학습 모드
"""

import time
import sys
import select
import termios
import tty

# 하드웨어 가져오기
import os

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

# 하드웨어 객체들
line_sensor = None
motor = None
ultrasonic = None

# 로터리 감지용 변수들
line_change_count = 0
last_line_position = "center"
rotary_mode = False
rotary_start_time = 0


def check_quit_key():
    """'q' 키가 눌렸는지 확인 (논블로킹)"""
    try:
        # stdin이 준비되어 있는지 확인
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            # 터미널 설정 저장
            old_settings = termios.tcgetattr(sys.stdin)
            try:
                # raw 모드로 설정
                tty.setraw(sys.stdin.fileno())
                # 키 읽기
                char = sys.stdin.read(1)
                # 'q' 키 확인
                if char.lower() == "q":
                    return True
            finally:
                # 터미널 설정 복구
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        return False
    except:
        # 에러 발생 시 False 반환 (Windows 등에서)
        return False


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
            print(f"Sim obstacle: {distance}cm")
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
        print(f"  Line change detected: {line_change_count} times")

    # 로터리 감지 조건: 짧은 시간에 많은 라인 변화
    if line_change_count >= ROTARY_LINE_CHANGE_THRESHOLD and not rotary_mode:
        rotary_mode = True
        rotary_start_time = time.time()
        line_change_count = 0  # 카운트 리셋
        print("Rotary detected! Switching to safe mode")
        return True

    # 로터리 모드에서 일정 시간 경과 시 해제
    if rotary_mode and (time.time() - rotary_start_time) > ROTARY_DETECTION_TIME:
        rotary_mode = False
        print("Rotary passed! Returning to normal mode")
        return False

    return rotary_mode


def stop():
    """정지"""
    if motor:
        motor.motor_stop()
        print("Stop")
    else:
        print("Simulation: Stop")


def go_forward(speed=None):
    """직진"""
    speed = speed or FORWARD_SPEED
    if motor:
        motor.set_motor_speed("A", speed)  # 오른쪽
        motor.set_motor_speed("B", speed)  # 왼쪽
        print(f"Forward (speed: {speed})")
    else:
        print(f"Simulation: Forward (speed: {speed})")


def turn_left():
    """좌회전 (개별 속도 설정)"""
    if motor:
        motor.set_motor_speed("A", LEFT_TURN_RIGHT_MOTOR)  # 오른쪽: 높은 속도
        motor.set_motor_speed("B", -LEFT_TURN_LEFT_MOTOR)  # 왼쪽: 낮은 속도 후진
        print(f"Turn left (R:{LEFT_TURN_RIGHT_MOTOR}, L:-{LEFT_TURN_LEFT_MOTOR})")
    else:
        print(
            f"Simulation: Turn left (R:{LEFT_TURN_RIGHT_MOTOR}, L:-{LEFT_TURN_LEFT_MOTOR})"
        )


def turn_right():
    """우회전 (개별 속도 설정)"""
    if motor:
        motor.set_motor_speed("A", -RIGHT_TURN_RIGHT_MOTOR)  # 오른쪽: 낮은 속도 후진
        motor.set_motor_speed("B", RIGHT_TURN_LEFT_MOTOR)  # 왼쪽: 높은 속도
        print(f"Turn right (R:-{RIGHT_TURN_RIGHT_MOTOR}, L:{RIGHT_TURN_LEFT_MOTOR})")
    else:
        print(
            f"Simulation: Turn right (R:-{RIGHT_TURN_RIGHT_MOTOR}, L:{RIGHT_TURN_LEFT_MOTOR})"
        )


def avoid_obstacle():
    """장애물 피하기 (좌회전 → 직진 → 우회전)"""
    print("Obstacle avoidance started!")

    # 1단계: 좌회전
    print("  1. Avoid by turning left")
    turn_left()
    time.sleep(AVOID_TIME)

    # 2단계: 직진으로 지나가기
    print("  2. Go straight to pass")
    go_forward()
    time.sleep(AVOID_TIME)

    # 3단계: 우회전으로 원래 방향
    print("  3. Turn right to return")
    turn_right()
    time.sleep(AVOID_TIME)

    print("Obstacle avoidance completed!")


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
        print(f"Rotary safe driving: {line_position}")
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


def show_settings():
    """현재 설정 표시"""
    print("=" * 50)
    print("Ultra Simple Car v2 Settings")
    print("=" * 50)
    print("Base speed:")
    print(f"  Forward: {FORWARD_SPEED}")
    print()
    print("Turn speeds (per side):")
    print(
        f"  Left  - Right motor: {LEFT_TURN_RIGHT_MOTOR}, Left motor: {LEFT_TURN_LEFT_MOTOR}"
    )
    print(
        f"  Right - Right motor: {RIGHT_TURN_RIGHT_MOTOR}, Left motor: {RIGHT_TURN_LEFT_MOTOR}"
    )
    print()
    print("Obstacle avoidance:")
    print(f"  Safe distance: {SAFE_DISTANCE}cm")
    print(f"  Avoid time: {AVOID_TIME}s")
    print()
    print("Rotary detection:")
    print(f"  Detect time: {ROTARY_DETECTION_TIME}s")
    print(f"  Safe speed: {ROTARY_SAFE_SPEED}")
    print(f"  Line change threshold: {ROTARY_LINE_CHANGE_THRESHOLD}")
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
        print("Cleanup completed")
    except:
        pass


def step1_basic_line_following():
    """Step 1: 기본 라인 추적 수업"""
    print("\n" + "=" * 50)
    print("Step 1: Basic line following lesson")
    print("=" * 50)
    print("Topics:")
    print("- Detect line position with sensors")
    print("- Control LEFT/RIGHT motor speeds")
    print("- Use basic if-else conditions")
    print("=" * 50)

    if not setup():
        return

    print("Step 1 started! (press 'q' to return to menu)")

    try:
        while True:
            # 'q' 키 체크
            if check_quit_key():
                print("\n'q' detected! Returning to menu")
                break

            drive_basic()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nCtrl+C pressed")
    finally:
        cleanup()


def step2_obstacle_avoidance():
    """Step 2: 장애물 회피 수업"""
    print("\n" + "=" * 50)
    print("Step 2: Obstacle avoidance lesson")
    print("=" * 50)
    print("Topics:")
    print("- 초음파 센서로 거리 측정")
    print("- 3단계 장애물 회피 알고리즘")
    print("- 우선순위 기반 의사결정")
    print("=" * 50)

    if not setup():
        return

    print("Step 2 started! (press 'q' to return to menu)")

    try:
        while True:
            # 'q' 키 체크
            if check_quit_key():
                print("\n'q' detected! Returning to menu")
                break

            drive_with_obstacle()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nCtrl+C pressed")
    finally:
        cleanup()


def step3_rotary_detection():
    """Step 3: 로터리 감지 수업 (고급)"""
    print("\n" + "=" * 50)
    print("Step 3: Rotary detection lesson (advanced)")
    print("=" * 50)
    print("Topics:")
    print("- 패턴 인식을 통한 로터리 감지")
    print("- 상태 관리 (rotary_mode)")
    print("- 적응형 속도 제어")
    print("- 복합 센서 데이터 처리")
    print("=" * 50)

    if not setup():
        return

    print("Step 3 started! (press 'q' to return to menu)")

    try:
        while True:
            # 'q' 키 체크
            if check_quit_key():
                print("\n'q' detected! Returning to menu")
                break

            drive_with_rotary()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nCtrl+C pressed")
    finally:
        cleanup()


def show_menu():
    """메뉴 표시"""
    print("\n" + "=" * 60)
    print("Ultra Simple Car v2 - Step-by-step Learning")
    print("=" * 60)
    print("1. Step 1: Basic line following (beginner) - press 'q' to return")
    print("2. Step 2: Add obstacle avoidance (intermediate) - press 'q' to return")
    print("3. Step 3: Add rotary detection (advanced) - press 'q' to return")
    print("4. Show settings")
    print("5. Run all features (unlimited) - press 'q' to return")
    print("0. Exit")
    print("=" * 60)
    print("Tip: Press 'q' in any step to return to the menu!")


def main():
    """메인 함수"""
    while True:
        show_menu()

        try:
            choice = input("Choose (0-5): ").strip()

            if choice == "1":
                step1_basic_line_following()

            elif choice == "2":
                step2_obstacle_avoidance()

            elif choice == "3":
                step3_rotary_detection()

            elif choice == "4":
                show_settings()

            elif choice == "5":
                print("\nRun all features!")
                print("Press 'q' to return, Ctrl+C to exit")

                if not setup():
                    continue

                try:
                    while True:
                        # 'q' 키 체크
                        if check_quit_key():
                            print("\n'q' detected! Returning to menu")
                            break

                        drive_with_rotary()
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\nCtrl+C exit")
                    break
                finally:
                    cleanup()

            elif choice == "0":
                print("Program exited")
                break

            else:
                print("Invalid choice")

        except KeyboardInterrupt:
            print("\n\nProgram terminated")
            break


if __name__ == "__main__":
    main()
