#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
단순한 모터 제어 모듈 (고등학생용)
Simple Motor Control Module for High School Students

이 모듈은 자동차의 바퀴를 쉽게 움직일 수 있게 해줍니다.
"""

import time

# 하드웨어 모듈 가져오기
try:
    from ..hardware.test_gear_motors import GearMotorController

    HARDWARE_AVAILABLE = True
    print("✓ 실제 모터 사용")
except ImportError:
    HARDWARE_AVAILABLE = False
    print("⚠️ 시뮬레이션 모드")

# 전역 변수
motor_controller = None

# 속도 설정 (고등학생이 쉽게 바꿀 수 있음)
SPEED_SLOW = 30  # 느린 속도
SPEED_NORMAL = 50  # 보통 속도
SPEED_FAST = 70  # 빠른 속도


def setup_motors():
    """모터를 준비합니다"""
    global motor_controller

    if HARDWARE_AVAILABLE:
        try:
            motor_controller = GearMotorController()
            print("✓ 모터 준비 완료!")
            return True
        except Exception as e:
            print(f"❌ 모터 준비 실패: {e}")
            return False
    else:
        print("✓ 시뮬레이션 모터 준비 완료!")
        return True


def stop():
    """자동차를 멈춥니다"""
    if motor_controller:
        motor_controller.motor_stop()
        print("⏹️ 정지")
    else:
        print("시뮬레이션: 정지")


def go_forward(speed=SPEED_NORMAL):
    """앞으로 갑니다"""
    if motor_controller:
        motor_controller.set_motor_speed("A", speed)  # 오른쪽 바퀴
        motor_controller.set_motor_speed("B", speed)  # 왼쪽 바퀴
        print(f"⬆️ 직진 (속도: {speed})")
    else:
        print(f"시뮬레이션: 직진 (속도: {speed})")


def go_backward(speed=SPEED_NORMAL):
    """뒤로 갑니다"""
    if motor_controller:
        motor_controller.set_motor_speed("A", -speed)  # 오른쪽 바퀴
        motor_controller.set_motor_speed("B", -speed)  # 왼쪽 바퀴
        print(f"⬇️ 후진 (속도: {speed})")
    else:
        print(f"시뮬레이션: 후진 (속도: {speed})")


def turn_left(speed=SPEED_NORMAL):
    """왼쪽으로 돕니다 (오른쪽 바퀴는 앞으로, 왼쪽 바퀴는 뒤로)"""
    if motor_controller:
        motor_controller.set_motor_speed("A", speed)  # 오른쪽 바퀴: 앞으로
        motor_controller.set_motor_speed("B", -speed)  # 왼쪽 바퀴: 뒤로
        print(f"⬅️ 좌회전 (속도: {speed})")
    else:
        print(f"시뮬레이션: 좌회전 (속도: {speed})")


def turn_right(speed=SPEED_NORMAL):
    """오른쪽으로 돕니다 (왼쪽 바퀴는 앞으로, 오른쪽 바퀴는 뒤로)"""
    if motor_controller:
        motor_controller.set_motor_speed("A", -speed)  # 오른쪽 바퀴: 뒤로
        motor_controller.set_motor_speed("B", speed)  # 왼쪽 바퀴: 앞으로
        print(f"➡️ 우회전 (속도: {speed})")
    else:
        print(f"시뮬레이션: 우회전 (속도: {speed})")


def turn_left_gentle(speed=SPEED_SLOW):
    """부드럽게 왼쪽으로 돕니다 (오른쪽 바퀴만 빠르게)"""
    if motor_controller:
        motor_controller.set_motor_speed("A", speed)  # 오른쪽 바퀴: 빠르게
        motor_controller.set_motor_speed("B", speed // 2)  # 왼쪽 바퀴: 느리게
        print(f"↖️ 부드러운 좌회전 (속도: {speed})")
    else:
        print(f"시뮬레이션: 부드러운 좌회전 (속도: {speed})")


def turn_right_gentle(speed=SPEED_SLOW):
    """부드럽게 오른쪽으로 돕니다 (왼쪽 바퀴만 빠르게)"""
    if motor_controller:
        motor_controller.set_motor_speed("A", speed // 2)  # 오른쪽 바퀴: 느리게
        motor_controller.set_motor_speed("B", speed)  # 왼쪽 바퀴: 빠르게
        print(f"↗️ 부드러운 우회전 (속도: {speed})")
    else:
        print(f"시뮬레이션: 부드러운 우회전 (속도: {speed})")


def cleanup_motors():
    """모터를 정리합니다"""
    global motor_controller

    try:
        if motor_controller:
            motor_controller.cleanup()
        print("✓ 모터 정리 완료")
    except Exception as e:
        print(f"모터 정리 중 오류: {e}")


# 테스트 함수
def test_motors():
    """모터들을 테스트합니다"""
    print("\n🚗 모터 테스트")

    if not setup_motors():
        print("❌ 모터 준비 실패")
        return

    print("\n다양한 움직임 테스트...")

    # 직진
    print("1. 직진")
    go_forward()
    time.sleep(1)

    # 좌회전
    print("2. 좌회전")
    turn_left()
    time.sleep(1)

    # 우회전
    print("3. 우회전")
    turn_right()
    time.sleep(1)

    # 부드러운 좌회전
    print("4. 부드러운 좌회전")
    turn_left_gentle()
    time.sleep(1)

    # 부드러운 우회전
    print("5. 부드러운 우회전")
    turn_right_gentle()
    time.sleep(1)

    # 후진
    print("6. 후진")
    go_backward()
    time.sleep(1)

    # 정지
    print("7. 정지")
    stop()

    cleanup_motors()
    print("테스트 완료!")


def show_speed_settings():
    """현재 속도 설정을 보여줍니다"""
    print("\n⚙️ 현재 속도 설정:")
    print(f"  느린 속도: {SPEED_SLOW}")
    print(f"  보통 속도: {SPEED_NORMAL}")
    print(f"  빠른 속도: {SPEED_FAST}")
    print("\n💡 속도를 바꾸려면:")
    print("  파일 상단의 SPEED_SLOW, SPEED_NORMAL, SPEED_FAST 값을 수정하세요!")


if __name__ == "__main__":
    show_speed_settings()
    test_motors()
