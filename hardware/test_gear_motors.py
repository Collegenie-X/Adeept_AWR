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
    # 변경사항: 속도가 0이면 해당 바퀴를 완전 정지(방향핀 LOW, PWM 0)하여 잔류 상태 제거
    if right_speed == 0:
        motor_a_control(0, 0)
    else:
        motor_a_control(+1 if right_speed > 0 else -1, abs(right_speed))

    if left_speed == 0:
        motor_b_control(0, 0)
    else:
        motor_b_control(+1 if left_speed > 0 else -1, abs(left_speed))


def motor_stop():
    """모든 모터 정지"""

    motor_a_control(0, 0)
    motor_b_control(0, 0)


def comprehensive_test_sequence():
    """종합 동작 테스트"""
    print("Comprehensive motor test started.\n")

    print("Forward test (4s)")
    drive(100, 100)  # 우측100%, 좌측100%
    time.sleep(1)
    motor_stop()
    time.sleep(1)

    print("Backward test (4s)")
    drive(-100, -100)  # 양쪽 후진
    time.sleep(4)
    motor_stop()
    time.sleep(1)

    print("Left turn in place (4s)")
    drive(100, 0)  # 우측 전진, 좌측 후진
    time.sleep(3)
    motor_stop()
    time.sleep(1)

    print("Right turn in place (4s)")
    drive(0, 100)  # 우측 후진, 좌측 전진
    time.sleep(3)
    motor_stop()
    time.sleep(1)

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


class GearMotorController:
    """
    기어 모터 컨트롤러 클래스
    - simple_car 모듈에서 기대하는 API와 호환 (set_motor_speed, motor_stop, cleanup)
    - 채널 매핑: "A"=우측 모터, "B"=좌측 모터
    - 속도 범위: -100~+100 (부호는 방향)
    """

    def __init__(self):
        """GPIO 및 PWM을 초기화합니다."""
        import RPi.GPIO as GPIO

        # GPIO 초기화
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # 핀 설정
        for pin in [ENA, ENB, A1, A2, B1, B2]:
            GPIO.setup(pin, GPIO.OUT)

        # PWM 객체 생성 및 시작
        self.pwmA = GPIO.PWM(ENA, 1000)
        self.pwmB = GPIO.PWM(ENB, 1000)
        self.pwmA.start(0)
        self.pwmB.start(0)

        # 초기 정지 상태
        self._stop_all_motors()
        print("GearMotorController initialized.")

    def _stop_all_motors(self):
        """내부용 모터 정지 함수"""
        import RPi.GPIO as GPIO

        GPIO.output(A1, GPIO.LOW)
        GPIO.output(A2, GPIO.LOW)
        GPIO.output(B1, GPIO.LOW)
        GPIO.output(B2, GPIO.LOW)
        self.pwmA.ChangeDutyCycle(0)
        self.pwmB.ChangeDutyCycle(0)

    def set_motor_speed(self, channel: str, speed: int) -> None:
        """
        개별 모터 속도/방향 설정
        :param channel: "A"(우측) 또는 "B"(좌측)
        :param speed: -100~+100 (0이면 완전 정지)
        """
        import RPi.GPIO as GPIO

        if channel not in ("A", "B"):
            print(f"Invalid channel: {channel}")
            return

        speed = max(-100, min(100, int(speed)))

        if channel == "A":
            if speed == 0:
                GPIO.output(A1, GPIO.LOW)
                GPIO.output(A2, GPIO.LOW)
                self.pwmA.ChangeDutyCycle(0)
            elif speed > 0:
                GPIO.output(A1, GPIO.HIGH)
                GPIO.output(A2, GPIO.LOW)
                self.pwmA.ChangeDutyCycle(abs(speed))
            else:
                GPIO.output(A1, GPIO.LOW)
                GPIO.output(A2, GPIO.HIGH)
                self.pwmA.ChangeDutyCycle(abs(speed))

        elif channel == "B":
            if speed == 0:
                GPIO.output(B1, GPIO.LOW)
                GPIO.output(B2, GPIO.LOW)
                self.pwmB.ChangeDutyCycle(0)
            elif speed > 0:
                GPIO.output(B1, GPIO.HIGH)
                GPIO.output(B2, GPIO.LOW)
                self.pwmB.ChangeDutyCycle(abs(speed))
            else:
                GPIO.output(B1, GPIO.LOW)
                GPIO.output(B2, GPIO.HIGH)
                self.pwmB.ChangeDutyCycle(abs(speed))

    def motor_stop(self) -> None:
        """모든 모터를 완전 정지합니다."""
        self._stop_all_motors()

    def cleanup(self) -> None:
        """GPIO 리소스를 정리합니다."""
        try:
            self._stop_all_motors()
            self.pwmA.stop()
            self.pwmB.stop()
        except:
            pass

        import RPi.GPIO as GPIO

        GPIO.cleanup()
        print("GearMotorController cleanup completed.")


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
