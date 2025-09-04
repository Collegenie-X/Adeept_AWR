#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
기어 모터 테스트 모듈
- L298N 모터 드라이버를 통한 DC 모터 제어
- PWM을 통한 속도 제어 지원
"""

import RPi.GPIO as GPIO
import time


class GearMotorController:
    def __init__(self):
        # 모터 A (우측) GPIO 핀 정의
        self.MOTOR_A_EN = 4  # PWM 속도 제어
        self.MOTOR_A_PIN1 = 14  # 방향 제어 1
        self.MOTOR_A_PIN2 = 15  # 방향 제어 2

        # 모터 B (좌측) GPIO 핀 정의
        self.MOTOR_B_EN = 17  # PWM 속도 제어
        self.MOTOR_B_PIN1 = 27  # 방향 제어 1
        self.MOTOR_B_PIN2 = 18  # 방향 제어 2

        self.setup()

    def setup(self):
        """GPIO 초기화 및 PWM 설정"""
        # GPIO 설정 초기화
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # 모터 A 핀 설정
        GPIO.setup(self.MOTOR_A_EN, GPIO.OUT)
        GPIO.setup(self.MOTOR_A_PIN1, GPIO.OUT)
        GPIO.setup(self.MOTOR_A_PIN2, GPIO.OUT)

        # 모터 B 핀 설정
        GPIO.setup(self.MOTOR_B_EN, GPIO.OUT)
        GPIO.setup(self.MOTOR_B_PIN1, GPIO.OUT)
        GPIO.setup(self.MOTOR_B_PIN2, GPIO.OUT)

        # PWM 객체 생성 (주파수: 1000Hz)
        self.pwm_A = GPIO.PWM(self.MOTOR_A_EN, 1000)
        self.pwm_B = GPIO.PWM(self.MOTOR_B_EN, 1000)

        # PWM 시작 (초기 듀티비: 0%)
        self.pwm_A.start(0)
        self.pwm_B.start(0)

    def motor_stop(self):
        """모든 모터 정지"""
        # 모터 A 정지
        GPIO.output(self.MOTOR_A_PIN1, GPIO.LOW)
        GPIO.output(self.MOTOR_A_PIN2, GPIO.LOW)
        self.pwm_A.ChangeDutyCycle(0)

        # 모터 B 정지
        GPIO.output(self.MOTOR_B_PIN1, GPIO.LOW)
        GPIO.output(self.MOTOR_B_PIN2, GPIO.LOW)
        self.pwm_B.ChangeDutyCycle(0)

    def set_motor_speed(self, motor, speed):
        """
        모터 속도 설정
        :param motor: 'A' 또는 'B' (우측/좌측 모터)
        :param speed: -100 ~ 100 (음수: 후진, 양수: 전진)
        """
        if motor == "A":
            pwm = self.pwm_A
            pin1 = self.MOTOR_A_PIN1
            pin2 = self.MOTOR_A_PIN2
        else:
            pwm = self.pwm_B
            pin1 = self.MOTOR_B_PIN1
            pin2 = self.MOTOR_B_PIN2

        # 속도 범위 제한
        speed = max(-100, min(100, speed))

        if speed > 0:  # 전진
            GPIO.output(pin1, GPIO.HIGH)
            GPIO.output(pin2, GPIO.LOW)
            pwm.ChangeDutyCycle(speed)
        elif speed < 0:  # 후진
            GPIO.output(pin1, GPIO.LOW)
            GPIO.output(pin2, GPIO.HIGH)
            pwm.ChangeDutyCycle(-speed)
        else:  # 정지
            GPIO.output(pin1, GPIO.LOW)
            GPIO.output(pin2, GPIO.LOW)
            pwm.ChangeDutyCycle(0)

    def cleanup(self):
        """GPIO 설정 초기화"""
        self.motor_stop()
        GPIO.cleanup()


def test_motors():
    """모터 테스트 함수"""
    controller = GearMotorController()

    try:
        print("모터 테스트를 시작합니다...")

        SPEED = 100

        # 전진 테스트
        print("전진 테스트 (3초)")
        controller.set_motor_speed("A", 100)
        controller.set_motor_speed("B", 100)
        time.sleep(3)

        # 후진 테스트
        print("후진 테스트 (3초)")
        controller.set_motor_speed("A", -100)
        controller.set_motor_speed("B", -100)
        time.sleep(3)

        # 우회전 테스트
        print("우회전 테스트 (3초)")
        controller.set_motor_speed("A", 100)
        controller.set_motor_speed("B", 0)
        time.sleep(3)

        # 좌회전 테스트
        print("좌회전 테스트 (3초)")
        controller.set_motor_speed("A", 0)
        controller.set_motor_speed("B", 100)
        time.sleep(3)

        # 정지
        print("정지")
        controller.motor_stop()

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    test_motors()
