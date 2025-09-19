#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
초간단 자율 주행차 (고등학생용)
Ultra Simple Autonomous Car for High School Students

기능:
1. 라인 센서로 검은 선 따라가기
2. 초음파 센서로 장애물 피하기
3. 그것뿐!
"""

import time
import threading
import os
import sys

# OpenCV 호환성 체크
try:
    import cv2
    import numpy as np

    CV2_AVAILABLE = True
    print("✓ OpenCV 사용 가능")
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ OpenCV 없음 - 터미널 기반 제어 사용")

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

# 설정값 (도로폭 20cm 기준 조정)
FORWARD_SPEED = 70  # 직진 속도 (안정성을 위해 증가)
LOW_TURN_SPEED = 40  # 약한 회전 속도 (중앙선 회피용)
HIGH_TURN_SPEED = 80  # 강한 회전 속도 (경계선 회피용)
SAFE_DISTANCE = 15  # 장애물 안전 거리 (cm)
AVOID_TIME = 0.6  # 회피 동작 시간 (초) - 짧게 조정

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
control_window = None  # OpenCV 제어 창
gui_mode = False  # GUI 모드 사용 가능 여부

# Trackbar 실시간 조절 값들 (전역 변수로 변경)
current_forward_speed = FORWARD_SPEED
current_low_turn_speed = LOW_TURN_SPEED
current_high_turn_speed = HIGH_TURN_SPEED
current_safe_distance = SAFE_DISTANCE
current_avoid_time = int(AVOID_TIME * 10)  # 0.1초 단위로 조절


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


def on_forward_speed_change(val):
    """전진 속도 trackbar 콜백"""
    global current_forward_speed
    current_forward_speed = val
    print(f"전진 속도: {val}%")


def on_low_turn_speed_change(val):
    """약한 회전 속도 trackbar 콜백"""
    global current_low_turn_speed
    current_low_turn_speed = val
    print(f"약한 회전 속도: {val}%")


def on_high_turn_speed_change(val):
    """강한 회전 속도 trackbar 콜백"""
    global current_high_turn_speed
    current_high_turn_speed = val
    print(f"강한 회전 속도: {val}%")


def on_safe_distance_change(val):
    """안전 거리 trackbar 콜백"""
    global current_safe_distance
    current_safe_distance = val
    print(f"안전 거리: {val}cm")


def on_avoid_time_change(val):
    """회피 시간 trackbar 콜백"""
    global current_avoid_time
    current_avoid_time = val
    print(f"회피 시간: {val/10:.1f}초")


def create_control_window():
    """OpenCV 제어 창과 trackbar 생성"""
    global control_window

    # 제어 패널 이미지 생성 (900x700)
    control_panel = np.zeros((700, 900, 3), dtype=np.uint8)

    # 배경색 설정 (어두운 회색)
    control_panel[:] = (50, 50, 50)

    # 제목 텍스트
    cv2.putText(
        control_panel,
        "Robot Control Panel with Trackbars",
        (180, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (255, 255, 255),
        2,
    )

    # 현재 모드 표시 영역
    cv2.rectangle(control_panel, (50, 60), (850, 100), (70, 70, 70), -1)

    # 섹션 구분선
    cv2.line(control_panel, (50, 120), (850, 120), (100, 100, 100), 2)

    # 제어 키 가이드
    instructions = [
        "=== Mode Control ===",
        "S: Start Auto Mode",
        "P: Stop (Manual Mode)",
        "Q: Quit Program",
        "",
        "=== Manual Control ===",
        "W: Forward",
        "A: Turn Left",
        "D: Turn Right",
        "X: Backward",
        "SPACE: Emergency Stop",
    ]

    y_offset = 150
    for instruction in instructions:
        if instruction == "":
            y_offset += 10
            continue

        color = (100, 255, 100) if instruction.startswith("===") else (255, 255, 255)
        font_scale = 0.7 if instruction.startswith("===") else 0.5

        cv2.putText(
            control_panel,
            instruction,
            (80, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            color,
            1,
        )
        y_offset += 25

    # Trackbar 설명 영역
    cv2.line(control_panel, (50, 420), (850, 420), (100, 100, 100), 2)
    cv2.putText(
        control_panel,
        "=== Real-time Speed Control (Use trackbars above) ===",
        (120, 450),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (100, 255, 100),
        1,
    )

    # 현재 값 표시 영역
    value_texts = [
        f"Forward Speed: {current_forward_speed}%",
        f"Low Turn Speed: {current_low_turn_speed}%",
        f"High Turn Speed: {current_high_turn_speed}%",
        f"Safe Distance: {current_safe_distance}cm",
        f"Avoid Time: {current_avoid_time/10:.1f}s",
    ]

    y_offset = 480
    for text in value_texts:
        cv2.putText(
            control_panel,
            text,
            (80, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 100),
            1,
        )
        y_offset += 25

    return control_panel


def print_terminal_control_menu():
    """터미널 기반 제어 메뉴 출력"""
    print("\n" + "=" * 60)
    print("🎛️ 터미널 기반 속도 제어 (OpenCV 대안)")
    print("=" * 60)
    print("현재 설정값:")
    print(f"  1. Forward Speed: {current_forward_speed}%")
    print(f"  2. Low Turn Speed: {current_low_turn_speed}%")
    print(f"  3. High Turn Speed: {current_high_turn_speed}%")
    print(f"  4. Safe Distance: {current_safe_distance}cm")
    print(f"  5. Avoid Time: {current_avoid_time/10:.1f}s")
    print("\n모드 제어:")
    print("  s: 자동 주행 시작")
    print("  p: 정지 (수동 모드)")
    print("  w,a,d,x: 수동 조작")
    print("  q: 프로그램 종료")
    print("\n값 변경 (숫자1-5 + 새값):")
    print("  예: '1 85' → 전진속도 85%로 변경")
    print("  예: '4 20' → 안전거리 20cm로 변경")
    print("=" * 60)


def handle_terminal_input():
    """터미널 입력 처리"""
    global current_forward_speed, current_low_turn_speed, current_high_turn_speed
    global current_safe_distance, current_avoid_time
    global autonomous_mode, manual_control_active, running

    while running:
        try:
            print(
                f"\n상태: {'🚗자동' if autonomous_mode else '🎮수동' if manual_control_active else '⏸️대기'}"
            )
            user_input = input("명령 입력 (help = 도움말): ").strip().lower()

            if not user_input:
                continue

            if user_input == "help":
                print_terminal_control_menu()
            elif user_input == "q":
                print("프로그램 종료")
                running = False
                break
            elif user_input == "s":
                if not autonomous_mode:
                    print("🚗 자동 주행 시작")
                    autonomous_mode = True
                    manual_control_active = False
                else:
                    print("이미 자동 주행 중")
            elif user_input == "p":
                if autonomous_mode:
                    print("⏸️ 정지 - 수동 모드로 전환")
                    autonomous_mode = False
                    manual_control_active = True
                    stop()
                else:
                    print("이미 수동 모드")
            elif user_input in ["w", "a", "d", "x"] and not autonomous_mode:
                manual_control_active = True
                if user_input == "w":
                    print("🔼 수동 전진")
                    manual_forward()
                elif user_input == "a":
                    print("◀️ 수동 좌회전")
                    manual_turn_left()
                elif user_input == "d":
                    print("▶️ 수동 우회전")
                    manual_turn_right()
                elif user_input == "x":
                    print("🔽 수동 후진")
                    manual_backward()
            elif " " in user_input:
                # 값 변경 명령 처리 (예: "1 85")
                try:
                    parts = user_input.split()
                    if len(parts) == 2:
                        setting_num = int(parts[0])
                        new_value = int(parts[1])

                        if setting_num == 1 and 0 <= new_value <= 100:
                            current_forward_speed = new_value
                            print(f"✓ 전진 속도: {new_value}%")
                        elif setting_num == 2 and 0 <= new_value <= 100:
                            current_low_turn_speed = new_value
                            print(f"✓ 약한 회전 속도: {new_value}%")
                        elif setting_num == 3 and 0 <= new_value <= 100:
                            current_high_turn_speed = new_value
                            print(f"✓ 강한 회전 속도: {new_value}%")
                        elif setting_num == 4 and 0 <= new_value <= 50:
                            current_safe_distance = new_value
                            print(f"✓ 안전 거리: {new_value}cm")
                        elif setting_num == 5 and 0 <= new_value <= 20:
                            current_avoid_time = new_value
                            print(f"✓ 회피 시간: {new_value/10:.1f}s")
                        else:
                            print("❌ 잘못된 설정 번호 또는 범위")
                    else:
                        print("❌ 형식: '설정번호 새값' (예: '1 85')")
                except ValueError:
                    print("❌ 숫자를 입력하세요")
            else:
                print("❌ 알 수 없는 명령. 'help' 입력으로 도움말 확인")

        except (EOFError, KeyboardInterrupt):
            print("\n프로그램 종료")
            running = False
            break
        except Exception as e:
            print(f"오류: {e}")


def setup_trackbars():
    """Trackbar 설정 (OpenCV GUI 안전 초기화)"""
    global gui_mode

    if not CV2_AVAILABLE:
        print("⚠️ OpenCV 없음 - GUI 모드 비활성화")
        return None

    try:
        window_name = "Robot Control"

        # 창 생성 시도
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 900, 700)

        # Trackbar 생성
        cv2.createTrackbar(
            "Forward Speed",
            window_name,
            current_forward_speed,
            100,
            on_forward_speed_change,
        )
        cv2.createTrackbar(
            "Low Turn Speed",
            window_name,
            current_low_turn_speed,
            100,
            on_low_turn_speed_change,
        )
        cv2.createTrackbar(
            "High Turn Speed",
            window_name,
            current_high_turn_speed,
            100,
            on_high_turn_speed_change,
        )
        cv2.createTrackbar(
            "Safe Distance",
            window_name,
            current_safe_distance,
            50,
            on_safe_distance_change,
        )
        cv2.createTrackbar(
            "Avoid Time x10", window_name, current_avoid_time, 20, on_avoid_time_change
        )

        gui_mode = True
        print("✓ OpenCV GUI 모드 활성화 - VNC를 통해 trackbar 조절 가능")
        return window_name

    except Exception as e:
        print(f"⚠️ OpenCV GUI 초기화 실패: {e}")
        print("→ 터미널 모드로 전환")
        gui_mode = False
        return None


def update_control_window():
    """제어 창 업데이트 (GUI 모드에서만)"""
    global control_window, autonomous_mode, manual_control_active

    if not gui_mode or not CV2_AVAILABLE:
        return

    try:
        if control_window is None:
            control_window = create_control_window()

        # 현재 모드 표시 영역 업데이트
        panel = control_window.copy()

        # 모드 상태 텍스트
        if autonomous_mode:
            mode_text = "Mode: AUTO DRIVING (Trackbar values active)"
            mode_color = (0, 255, 0)  # 녹색
        elif manual_control_active:
            mode_text = "Mode: MANUAL CONTROL (Use keys + trackbars)"
            mode_color = (0, 255, 255)  # 노란색
        else:
            mode_text = "Mode: STANDBY (Adjust trackbars, then press 's')"
            mode_color = (128, 128, 128)  # 회색

        # 모드 상태 배경 지우기
        cv2.rectangle(panel, (60, 70), (840, 95), (70, 70, 70), -1)

        # 모드 상태 텍스트 표시
        cv2.putText(
            panel, mode_text, (70, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, mode_color, 2
        )

        # 실시간 값 업데이트
        value_texts = [
            f"Forward Speed: {current_forward_speed}%",
            f"Low Turn Speed: {current_low_turn_speed}%",
            f"High Turn Speed: {current_high_turn_speed}%",
            f"Safe Distance: {current_safe_distance}cm",
            f"Avoid Time: {current_avoid_time/10:.1f}s",
        ]

        # 이전 값들 지우기
        cv2.rectangle(panel, (70, 470), (500, 600), (50, 50, 50), -1)

        y_offset = 480
        for text in value_texts:
            cv2.putText(
                panel,
                text,
                (80, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 100),
                1,
            )
            y_offset += 25

        cv2.imshow("Robot Control", panel)
    except Exception as e:
        print(f"GUI 업데이트 오류: {e}")
        # GUI 오류 시 터미널 모드로 전환


def handle_opencv_keyboard():
    """OpenCV 키보드 입력 처리 (GUI 모드에서만)"""
    global autonomous_mode, running, manual_control_active

    if not gui_mode or not CV2_AVAILABLE:
        return True

    try:
        # 제어 창 업데이트
        update_control_window()

        # 키 입력 대기 (30ms 타임아웃)
        key = cv2.waitKey(30) & 0xFF

        if key == 255:  # 키 입력 없음
            return True

        # 키 처리
        if key == ord("q"):
            print("\n프로그램 종료 요청")
            running = False
            autonomous_mode = False
            stop()
            return False
        elif key == ord("s"):
            if not autonomous_mode:
                print("\n🚗 자동 주행 모드 시작")
                autonomous_mode = True
                manual_control_active = False
            else:
                print("\n이미 자동 주행 중입니다")
        elif key == ord("p"):
            if autonomous_mode:
                print("\n⏸️ 정지 - 수동 모드로 전환")
                autonomous_mode = False
                manual_control_active = True
                stop()
            else:
                print("\n이미 수동 모드입니다")
        elif key == 32:  # 스페이스바
            print("\n⏹️ 즉시 정지")
            stop()
            manual_control_active = True
            autonomous_mode = False
        elif not autonomous_mode and manual_control_active:
            # 수동 제어 명령들
            if key == ord("w"):
                print("🔼 수동 전진")
                manual_forward()
            elif key == ord("a"):
                print("◀️ 수동 좌회전")
                manual_turn_left()
            elif key == ord("d"):
                print("▶️ 수동 우회전")
                manual_turn_right()
            elif key == ord("x"):
                print("🔽 수동 후진")
                manual_backward()

        return True
    except Exception as e:
        print(f"키보드 처리 오류: {e}")
        return True


def manual_forward():
    """수동 전진 (trackbar 값 사용)"""
    if motor:
        motor.set_motor_speed("A", current_forward_speed)
        motor.set_motor_speed("B", current_forward_speed)
        print(f"Manual: Forward at {current_forward_speed}%")
    else:
        print(f"Manual: Forward at {current_forward_speed}%")


def manual_backward():
    """수동 후진 (trackbar 값 사용)"""
    if motor:
        motor.set_motor_speed("A", -current_forward_speed)
        motor.set_motor_speed("B", -current_forward_speed)
        print(f"Manual: Backward at {current_forward_speed}%")
    else:
        print(f"Manual: Backward at {current_forward_speed}%")


def manual_turn_left():
    """수동 좌회전 (trackbar 값 사용)"""
    if motor:
        motor.set_motor_speed("A", current_high_turn_speed)
        motor.set_motor_speed("B", -current_high_turn_speed)
        print(f"Manual: Turn left at {current_high_turn_speed}%")
    else:
        print(f"Manual: Turn left at {current_high_turn_speed}%")


def manual_turn_right():
    """수동 우회전 (trackbar 값 사용)"""
    if motor:
        motor.set_motor_speed("A", -current_high_turn_speed)
        motor.set_motor_speed("B", current_high_turn_speed)
        print(f"Manual: Turn right at {current_high_turn_speed}%")
    else:
        print(f"Manual: Turn right at {current_high_turn_speed}%")


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
            distance = random.randint(5, SAFE_DISTANCE - 1)
            print(f"Sim obstacle distance: {distance}cm")
            return distance
        else:
            distance = random.randint(SAFE_DISTANCE + 10, 100)
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
    """직진 (trackbar 값 사용)"""
    if motor:
        motor.set_motor_speed("A", current_forward_speed)  # 오른쪽
        motor.set_motor_speed("B", current_forward_speed)  # 왼쪽
        print(f"Forward at {current_forward_speed}%")
    else:
        print(f"Simulation: Forward at {current_forward_speed}%")


def turn_left():
    """좌회전 (오른쪽 경계선에서 벗어나기) - trackbar 값 사용"""
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
    """우회전 (왼쪽 경계선에서 벗어나기) - trackbar 값 사용"""
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
    """약한 좌회전 (중앙선 회피용) - trackbar 값 사용"""
    if motor:
        motor.set_motor_speed("A", current_forward_speed)  # 오른쪽: 정상 속도
        motor.set_motor_speed("B", current_low_turn_speed)  # 왼쪽: 낮은 속도
        print(f"Slight left (R:{current_forward_speed}%, L:{current_low_turn_speed}%)")
    else:
        print(
            f"Simulation: Slight left (R:{current_forward_speed}%, L:{current_low_turn_speed}%)"
        )


def slight_right():
    """약한 우회전 (중앙선 회피용) - trackbar 값 사용"""
    if motor:
        motor.set_motor_speed("A", current_low_turn_speed)  # 오른쪽: 낮은 속도
        motor.set_motor_speed("B", current_forward_speed)  # 왼쪽: 정상 속도
        print(f"Slight right (R:{current_low_turn_speed}%, L:{current_forward_speed}%)")
    else:
        print(
            f"Simulation: Slight right (R:{current_low_turn_speed}%, L:{current_forward_speed}%)"
        )


def avoid_obstacle():
    """장애물 피하기 (좌회전 → 직진 → 우회전) - trackbar 값 사용"""
    avoid_time = current_avoid_time / 10.0  # trackbar 값을 초 단위로 변환
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

    # 1단계: 장애물 확인 (trackbar 안전거리 사용)
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


def cleanup():
    """정리"""
    global running

    try:
        # 프로그램 종료 플래그 설정
        running = False

        # 모터 정지
        stop()

        # OpenCV 창 닫기 (GUI 모드에서만)
        if gui_mode and CV2_AVAILABLE:
            try:
                cv2.destroyAllWindows()
            except:
                pass

        # 하드웨어 정리
        if line_sensor:
            line_sensor.cleanup()
        if motor:
            motor.cleanup()
        if ultrasonic:
            ultrasonic.cleanup()

        print("Cleanup completed")
    except:
        pass


def main():
    """메인 함수 (GUI/터미널 호환)"""
    global running, autonomous_mode

    print("Ultra Simple Autonomous Car with Real-time Control")
    print("=" * 55)
    print("Features: Line following + Obstacle avoidance + Real-time control")
    print("Initial Settings:")
    print(f"  Forward speed: {FORWARD_SPEED}%")
    print(f"  Turn speeds: Low={LOW_TURN_SPEED}%, High={HIGH_TURN_SPEED}%")
    print(f"  Safe distance: {SAFE_DISTANCE}cm")
    print(f"  Avoid time: {AVOID_TIME}s")
    print("=" * 55)

    if not setup():
        print("Setup failed")
        return

    try:
        # GUI 모드 시도
        window_name = setup_trackbars()

        if gui_mode:
            print("\n🎮 OpenCV GUI 모드 활성화")
            print("- VNC를 통해 trackbar로 실시간 조절")
            print("- 키보드로 모드 전환 (s=자동, p=수동, q=종료)")

            # 초기 제어 창 생성
            update_control_window()

            # GUI 메인 루프
            while running:
                if not handle_opencv_keyboard():
                    break

                if autonomous_mode:
                    drive()

                time.sleep(0.01)
        else:
            print("\n🖥️ 터미널 모드 활성화")
            print("- 명령어로 실시간 속도 조절")
            print("- 'help' 명령으로 사용법 확인")

            # 터미널 제어 가이드 출력
            print_terminal_control_menu()

            # 터미널 입력 스레드 시작
            import threading

            terminal_thread = threading.Thread(
                target=handle_terminal_input, daemon=True
            )
            terminal_thread.start()

            # 터미널 메인 루프
            while running:
                if autonomous_mode:
                    drive()
                    time.sleep(0.1)
                else:
                    time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\nCtrl+C 감지 - 프로그램 종료")
        running = False
    except Exception as e:
        print(f"\nError occurred: {e}")
        running = False
    finally:
        cleanup()
        print("Program exited")


if __name__ == "__main__":
    main()
