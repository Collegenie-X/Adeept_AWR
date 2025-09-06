#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
초음파 센서 테스트 모듈
- HC-SR04 초음파 센서를 사용한 거리 측정
- 측정 범위: 2cm ~ 400cm
"""

import RPi.GPIO as GPIO
import time


class UltrasonicSensor:
    def __init__(self):
        # 초음파 센서 GPIO 핀 정의
        self.TRIG_PIN = 11  # 트리거 핀
        self.ECHO_PIN = 8  # 에코 핀

        # 거리 측정 관련 상수
        self.SOUND_SPEED = 34300  # 음속 (cm/s)
        self.MAX_DISTANCE = 400  # 최대 측정 거리 (cm)
        self.TIMEOUT = self.MAX_DISTANCE * 2 / self.SOUND_SPEED  # 타임아웃 시간

        self.setup()

    def setup(self):
        """GPIO 초기화"""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # 핀 모드 설정
        GPIO.setup(self.TRIG_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.ECHO_PIN, GPIO.IN)

    def measure_distance(self):
        """
        거리 측정
        :return: 측정된 거리 (cm), 측정 실패시 None
        """
        # 트리거 신호 발생 (10us)
        GPIO.output(self.TRIG_PIN, GPIO.HIGH)
        time.sleep(0.00001)  # 10us
        GPIO.output(self.TRIG_PIN, GPIO.LOW)

        # 에코 신호 대기
        pulse_start = time.time()
        timeout_start = pulse_start

        # 에코 신호 시작 대기
        while GPIO.input(self.ECHO_PIN) == GPIO.LOW:
            pulse_start = time.time()
            if pulse_start - timeout_start > self.TIMEOUT:
                return None

        # 에코 신호 종료 대기
        pulse_end = time.time()
        timeout_start = pulse_end

        while GPIO.input(self.ECHO_PIN) == GPIO.HIGH:
            pulse_end = time.time()
            if pulse_end - timeout_start > self.TIMEOUT:
                return None

        # 거리 계산
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * self.SOUND_SPEED / 2

        # 유효 범위 확인
        if distance < 2 or distance > self.MAX_DISTANCE:
            return None

        return round(distance, 1)

    def get_status(self, distance):
        """
        거리에 따른 상태 반환
        :param distance: 측정된 거리 (cm)
        :return: (상태 문자열, LED 색상)
        """
        if distance is None:
            return "MEASURE_FAIL", "RED"
        elif distance < 10:
            return "EMERGENCY_STOP", "RED"
        elif distance < 20:
            return "AVOID_OBSTACLE", "ORANGE"
        elif distance < 40:
            return "SLOW_DOWN", "YELLOW"
        else:
            return "NORMAL", "GREEN"

    def cleanup(self):
        """GPIO 설정 초기화"""
        GPIO.cleanup()


def test_ultrasonic():
    """초음파 센서 테스트 함수"""
    sensor = UltrasonicSensor()

    try:
        print("Ultrasonic sensor test started...")
        print("Press Ctrl+C to exit.")

        while True:
            # 거리 측정
            distance = sensor.measure_distance()
            status, led_color = sensor.get_status(distance)

            # 상태 출력
            if distance is not None:
                print(
                    f"\rDistance: {distance:5.1f}cm | Status: {status:14s} | LED: {led_color}",
                    end="",
                )
            else:
                print("\rDistance: FAIL | Status: ERROR        | LED: RED", end="")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    finally:
        sensor.cleanup()


if __name__ == "__main__":
    test_ultrasonic()
