#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
기어 모터 테스트 모듈 (개선버전)
- L298N 모터 드라이버를 통한 DC 모터 제어
- 간결한 함수형 접근법으로 재작성
- 핀 매핑 문제 해결
"""

import RPi.GPIO as GPIO
import time

# BCM 모드 GPIO 핀 정의 (pinout.md 기준)
ENA, ENB = 4, 17  # PWM 활성화 핀
A1, A2 = 26, 21  # 모터A(우측) 방향 제어핀
B1, B2 = 27, 18  # 모터B(좌측) 방향 제어핀


def setup():
    """GPIO 초기 설정 및 PWM 객체 생성"""
    global pwmA, pwmB

    # 이전 GPIO 설정 정리
    GPIO.cleanup()
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # 모든 핀을 OUTPUT으로 설정
    for pin in [ENA, ENB, A1, A2, B1, B2]:
        GPIO.setup(pin, GPIO.OUT)

    # PWM 객체 생성 (1kHz 주파수)
    pwmA = GPIO.PWM(ENA, 1000)
    pwmB = GPIO.PWM(ENB, 1000)

    # PWM 시작 (초기 듀티비 0%)
    pwmA.start(0)
    pwmB.start(0)

    # 초기 상태로 모터 정지
    motor_stop()
    print("GPIO setup completed.")


def set_speed(pwm, duty):
    """PWM 속도 설정 (0~100%)"""
    duty = max(0, min(100, duty))  # 범위 제한
    pwm.ChangeDutyCycle(duty)


def motor_a_control(direction, speed):
    """
    모터A(우측) 개별 제어
    :param direction: +1(전진), -1(후진), 0(정지)
    :param speed: 0~100 (PWM 듀티비 %)
    """
    if direction > 0:
        GPIO.output(A1, GPIO.HIGH)
        GPIO.output(A2, GPIO.LOW)
    elif direction < 0:
        GPIO.output(A1, GPIO.LOW)
        GPIO.output(A2, GPIO.HIGH)
    else:
        GPIO.output(A1, GPIO.LOW)
        GPIO.output(A2, GPIO.LOW)

    set_speed(pwmA, abs(speed) if direction != 0 else 0)


def motor_b_control(direction, speed):
    """
    모터B(좌측) 개별 제어
    :param direction: +1(전진), -1(후진), 0(정지)
    :param speed: 0~100 (PWM 듀티비 %)
    """
    if direction > 0:
        GPIO.output(B1, GPIO.HIGH)
        GPIO.output(B2, GPIO.LOW)
    elif direction < 0:
        GPIO.output(B1, GPIO.LOW)
        GPIO.output(B2, GPIO.HIGH)
    else:
        GPIO.output(B1, GPIO.LOW)
        GPIO.output(B2, GPIO.LOW)

    set_speed(pwmB, abs(speed) if direction != 0 else 0)


def drive(right_speed, left_speed):
    """
    양쪽 모터 동시 제어 (수정됨: 올바른 모터 매핑)
    :param right_speed: 우측 모터 속도 (-100~+100)
    :param left_speed: 좌측 모터 속도 (-100~+100)
    """
    # 모터A = 우측, 모터B = 좌측 (pinout.md 기준)
    motor_a_control(+1 if right_speed >= 0 else -1, abs(right_speed))
    motor_b_control(+1 if left_speed >= 0 else -1, abs(left_speed))


def motor_stop():
    """모든 모터 정지"""
    motor_a_control(0, 0)
    motor_b_control(0, 0)


def individual_motor_test():
    """개별 모터 테스트 (디버깅용)"""
    print("\nIndividual motor test started.")

    print("Motor A (right) test - 2s")
    motor_a_control(+1, 70)
    time.sleep(2)
    motor_stop()
    time.sleep(1)

    print("Motor B (left) test - 2s")
    motor_b_control(+1, 70)
    time.sleep(2)
    motor_stop()
    time.sleep(1)

    print("Individual test completed.\n")


def comprehensive_test_sequence():
    """종합 동작 테스트"""
    print("Comprehensive motor test started.\n")

    # 개별 모터 테스트 먼저 실행
    individual_motor_test()

    print("Forward test (3s)")
    drive(70, 70)  # 우측70%, 좌측70%
    time.sleep(3)
    motor_stop()
    time.sleep(1)

    print("Backward test (3s)")
    drive(-70, -70)  # 양쪽 후진
    time.sleep(3)
    motor_stop()
    time.sleep(1)

    print("Left turn in place (3s)")
    drive(60, -60)  # 우측 전진, 좌측 후진
    time.sleep(3)
    motor_stop()
    time.sleep(1)

    print("Right turn in place (3s)")
    drive(-60, 60)  # 우측 후진, 좌측 전진
    time.sleep(3)
    motor_stop()
    time.sleep(1)

    print("Soft left turn (right motor only, 3s)")
    drive(50, 0)  # 우측만 전진
    time.sleep(3)
    motor_stop()
    time.sleep(1)

    print("Soft right turn (left motor only, 3s)")
    drive(0, 50)  # 좌측만 전진
    time.sleep(3)
    motor_stop()

    print("All tests completed!")


def cleanup():
    """정리 작업"""
    try:
        motor_stop()
        pwmA.stop()
        pwmB.stop()
    except:
        pass
    GPIO.cleanup()
    print("GPIO cleanup completed.")


if __name__ == "__main__":
    try:
        print("Gear motor test program started.")
        print("=" * 40)
        setup()
        comprehensive_test_sequence()

    except KeyboardInterrupt:
        print("\nUser interrupted the program.")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        cleanup()
