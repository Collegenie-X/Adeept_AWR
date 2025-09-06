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

# 하드웨어 가져오기
import sys
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

# 설정값 (여기만 바꾸면 됩니다!)
FORWARD_SPEED = 100  # 직진 속도
LOW_TURN_SPEED = 40  # 회전 속도
HIGH_TURN_SPEED = 100  # 회전 속도
SAFE_DISTANCE = 10  # 장애물 안전 거리 (cm)
AVOID_TIME = 0.8  # 회피 동작 시간 (초)

# 하드웨어 객체들
line_sensor = None
motor = None
ultrasonic = None


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
            return "center"
        elif position < -0.3:
            return "left"
        elif position > 0.3:
            return "right"
        else:
            return "center"
    else:
        # 시뮬레이션
        import random

        return random.choice(["left", "center", "right", "none"])


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
    """직진"""
    if motor:
        motor.set_motor_speed("A", FORWARD_SPEED)  # 오른쪽
        motor.set_motor_speed("B", FORWARD_SPEED)  # 왼쪽
        print("Forward")
    else:
        print("Simulation: Forward")


def turn_left():
    """좌회전"""
    if motor:
        motor.set_motor_speed("A", HIGH_TURN_SPEED)  # 오른쪽: 앞으로
        motor.set_motor_speed("B", -LOW_TURN_SPEED)  # 왼쪽: 뒤로
        print("Turn left")
    else:
        print("Simulation: Turn left")


def turn_right():
    """우회전"""
    if motor:
        motor.set_motor_speed("A", -LOW_TURN_SPEED)  # 오른쪽: 뒤로
        motor.set_motor_speed("B", HIGH_TURN_SPEED)  # 왼쪽: 앞으로
        print("Turn right")
    else:
        print("Simulation: Turn right")


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


def drive():
    """메인 주행 함수"""
    # 1단계: 장애물 확인
    distance = read_distance()

    if distance < SAFE_DISTANCE:
        # 장애물이 가까우면 피하기
        avoid_obstacle()
        return

    # 2단계: 라인 추적
    line_position = read_line()
    print(f"Line position: {line_position}")

    if line_position == "center":
        go_forward()
    elif line_position == "left":
        turn_right()  # 라인이 왼쪽에 있으니 오른쪽으로
    elif line_position == "right":
        turn_left()  # 라인이 오른쪽에 있으니 왼쪽으로
    else:  # none
        turn_left()  # 라인을 찾기 위해 천천히 회전


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


def main():
    """메인 함수"""
    print("Ultra Simple Autonomous Car")
    print("=" * 30)
    print("Features: Line following + Obstacle avoidance")
    print("Settings:")
    print(f"  Forward speed: {FORWARD_SPEED}")
    print(f"  Turn speeds: {LOW_TURN_SPEED}, {HIGH_TURN_SPEED}")
    print(f"  Safe distance: {SAFE_DISTANCE}cm")
    print("=" * 30)

    if not setup():
        print("Setup failed")
        return

    print("\nAutonomous driving started!")
    print("Press Ctrl+C to stop")

    try:
        while True:
            drive()
            time.sleep(0.1)  # 잠시 대기

    except KeyboardInterrupt:
        print("\n\nUser interrupted")
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        cleanup()
        print("Program exited")


if __name__ == "__main__":
    main()
