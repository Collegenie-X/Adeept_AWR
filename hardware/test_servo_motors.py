#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
서보모터 테스트 모듈 (PCA9685)
- Motor HAT의 PCA9685 PWM 컨트롤러를 사용한 서보모터 제어
- I2C 통신을 통한 16채널 PWM 제어
- 카메라 팬/틸트, 로봇 암 등의 서보모터 제어

연결 방법:
- Motor HAT의 서보 포트에 서보모터 연결
- I2C 통신: SDA(GPIO 2), SCL(GPIO 3)
- PWM 주파수: 50Hz (서보모터 표준)
"""

import time
from typing import Optional, List

try:
    import Adafruit_PCA9685

    PCA9685_AVAILABLE = True
except ImportError:
    print("경고: Adafruit_PCA9685 라이브러리를 찾을 수 없습니다.")
    print("설치 명령어: sudo pip3 install adafruit-pca9685")
    PCA9685_AVAILABLE = False


class ServoMotorController:
    def __init__(self, i2c_address: int = 0x40):
        # PCA9685 설정
        self.i2c_address = i2c_address
        self.pwm_frequency = 50  # 서보모터 표준 주파수 (50Hz)

        # 서보모터 PWM 값 범위 (일반적인 서보모터 기준)
        self.servo_min = 150  # 최소 PWM 값 (0도)
        self.servo_max = 600  # 최대 PWM 값 (180도)
        self.servo_center = 375  # 중앙 PWM 값 (90도)

        # PCA9685 객체
        self.pwm: Optional[Adafruit_PCA9685.PCA9685] = None

        # 서보모터 현재 위치 저장 (채널별)
        self.current_positions = {}

        self.setup()

    def setup(self):
        """PCA9685 초기화"""
        if not PCA9685_AVAILABLE:
            print("PCA9685 라이브러리가 없어 시뮬레이션 모드로 실행됩니다.")
            return False

        try:
            # PCA9685 객체 생성
            self.pwm = Adafruit_PCA9685.PCA9685(address=self.i2c_address)

            # PWM 주파수 설정
            self.pwm.set_pwm_freq(self.pwm_frequency)

            print("PCA9685 서보모터 컨트롤러 초기화 완료")
            print(f"I2C 주소: 0x{self.i2c_address:02X}")
            print(f"PWM 주파수: {self.pwm_frequency}Hz")
            return True

        except Exception as e:
            print(f"PCA9685 초기화 오류: {e}")
            print("I2C가 활성화되어 있는지 확인하세요: sudo raspi-config")
            return False

    def set_servo_angle(self, channel: int, angle: float):
        """
        서보모터를 특정 각도로 이동
        :param channel: 서보모터 채널 (0-15)
        :param angle: 목표 각도 (0-180도)
        """
        if not (0 <= channel <= 15):
            print(f"잘못된 채널 번호: {channel} (0-15 범위)")
            return

        if not (0 <= angle <= 180):
            print(f"잘못된 각도: {angle} (0-180도 범위)")
            return

        # 각도를 PWM 값으로 변환
        pwm_value = int(
            self.servo_min + (angle / 180.0) * (self.servo_max - self.servo_min)
        )

        if PCA9685_AVAILABLE and self.pwm:
            try:
                self.pwm.set_pwm(channel, 0, pwm_value)
                self.current_positions[channel] = angle
                print(f"서보 {channel}: {angle:.1f}도 (PWM: {pwm_value})")
            except Exception as e:
                print(f"서보 제어 오류: {e}")
        else:
            print(f"시뮬레이션: 서보 {channel} → {angle:.1f}도 (PWM: {pwm_value})")

    def set_servo_pwm(self, channel: int, pwm_value: int):
        """
        서보모터를 직접 PWM 값으로 제어 (문서 예제 방식)
        :param channel: 서보모터 채널 (0-15)
        :param pwm_value: PWM 값 (150-600 권장)
        """
        if not (0 <= channel <= 15):
            print(f"잘못된 채널 번호: {channel}")
            return

        if PCA9685_AVAILABLE and self.pwm:
            try:
                self.pwm.set_pwm(channel, 0, pwm_value)
                # PWM 값을 각도로 역계산
                angle = (
                    (pwm_value - self.servo_min) / (self.servo_max - self.servo_min)
                ) * 180
                angle = max(0, min(180, angle))  # 0-180도 범위로 제한
                self.current_positions[channel] = angle
                print(f"서보 {channel}: PWM {pwm_value} (약 {angle:.1f}도)")
            except Exception as e:
                print(f"서보 제어 오류: {e}")
        else:
            print(f"시뮬레이션: 서보 {channel} → PWM {pwm_value}")

    def move_servo_smooth(
        self, channel: int, target_angle: float, duration: float = 1.0
    ):
        """
        서보모터를 부드럽게 이동
        :param channel: 서보모터 채널
        :param target_angle: 목표 각도
        :param duration: 이동 시간 (초)
        """
        if channel not in self.current_positions:
            self.current_positions[channel] = 90  # 기본 중앙 위치

        start_angle = self.current_positions[channel]
        angle_diff = target_angle - start_angle
        steps = int(duration * 20)  # 20Hz로 업데이트

        if steps <= 0:
            self.set_servo_angle(channel, target_angle)
            return

        for i in range(steps + 1):
            current_angle = start_angle + (angle_diff * i / steps)
            self.set_servo_angle(channel, current_angle)
            time.sleep(duration / steps)

    def set_multiple_servos(self, servo_angles: dict):
        """
        여러 서보모터를 동시에 제어
        :param servo_angles: {채널: 각도} 딕셔너리
        """
        for channel, angle in servo_angles.items():
            self.set_servo_angle(channel, angle)

    def center_servo(self, channel: int):
        """서보모터를 중앙 위치(90도)로 이동"""
        self.set_servo_angle(channel, 90)

    def center_all_servos(self):
        """모든 서보모터를 중앙 위치로 이동"""
        print("모든 서보모터를 중앙 위치로 이동합니다...")
        for channel in range(16):
            self.center_servo(channel)
            time.sleep(0.1)

    def sweep_servo(
        self,
        channel: int,
        start_angle: float = 0,
        end_angle: float = 180,
        sweep_time: float = 2.0,
        cycles: int = 1,
    ):
        """
        서보모터를 스윕(왕복) 동작
        :param channel: 서보모터 채널
        :param start_angle: 시작 각도
        :param end_angle: 끝 각도
        :param sweep_time: 한 방향 이동 시간
        :param cycles: 왕복 횟수
        """
        print(f"서보 {channel} 스윕 동작: {start_angle}도 ↔ {end_angle}도 ({cycles}회)")

        for cycle in range(cycles):
            print(f"  사이클 {cycle + 1}/{cycles}")
            # 시작 → 끝
            self.move_servo_smooth(channel, end_angle, sweep_time)
            # 끝 → 시작
            self.move_servo_smooth(channel, start_angle, sweep_time)

    def test_servo_range(self, channel: int):
        """서보모터 동작 범위 테스트"""
        print(f"서보 {channel} 동작 범위 테스트")

        angles = [0, 45, 90, 135, 180, 90]  # 테스트 각도 시퀀스

        for angle in angles:
            print(f"  → {angle}도")
            self.set_servo_angle(channel, angle)
            time.sleep(1)

    def document_example_test(self):
        """문서 예제 테스트 (채널 3 서보모터 왕복)"""
        print("문서 예제 테스트: 채널 3 서보모터 왕복 동작")

        if not PCA9685_AVAILABLE or not self.pwm:
            print("시뮬레이션 모드에서 문서 예제 실행")
            for i in range(5):
                print(f"시뮬레이션: PWM(3, 0, 300) - 사이클 {i+1}")
                time.sleep(1)
                print(f"시뮬레이션: PWM(3, 0, 400) - 사이클 {i+1}")
                time.sleep(1)
            return

        try:
            for i in range(5):  # 5회 왕복
                print(f"  사이클 {i+1}: PWM 300")
                self.pwm.set_pwm(3, 0, 300)
                time.sleep(1)

                print(f"  사이클 {i+1}: PWM 400")
                self.pwm.set_pwm(3, 0, 400)
                time.sleep(1)

        except KeyboardInterrupt:
            print("테스트가 중단되었습니다.")

    def calibrate_servo(self, channel: int):
        """서보모터 캘리브레이션"""
        print(f"서보 {channel} 캘리브레이션")
        print("각 위치에서 서보모터 동작을 확인하세요.")

        positions = [
            (150, "최소 위치 (0도)"),
            (375, "중앙 위치 (90도)"),
            (600, "최대 위치 (180도)"),
        ]

        for pwm_val, description in positions:
            print(f"{description} - PWM: {pwm_val}")
            self.set_servo_pwm(channel, pwm_val)
            input("Enter를 눌러 다음 위치로...")

    def cleanup(self):
        """정리 및 종료"""
        print("서보모터 컨트롤러를 정리합니다...")
        # 모든 서보를 중앙 위치로 이동 후 PWM 신호 중단
        if PCA9685_AVAILABLE and self.pwm:
            try:
                for channel in range(16):
                    self.pwm.set_pwm(channel, 0, 0)  # PWM 신호 중단
            except:
                pass
        print("서보모터 정리 완료")


def test_servo_motors():
    """서보모터 종합 테스트"""
    controller = ServoMotorController()

    try:
        print("서보모터 테스트를 시작합니다...")
        print("=" * 50)

        # 1. 기본 각도 제어 테스트
        print("\n1. 기본 각도 제어 테스트 (채널 0)")
        angles = [0, 45, 90, 135, 180]
        for angle in angles:
            print(f"  → {angle}도")
            controller.set_servo_angle(0, angle)
            time.sleep(1)

        # 2. 부드러운 이동 테스트
        print("\n2. 부드러운 이동 테스트 (채널 1)")
        controller.move_servo_smooth(1, 180, 2.0)
        controller.move_servo_smooth(1, 0, 2.0)
        controller.move_servo_smooth(1, 90, 1.0)

        # 3. 다중 서보 제어 테스트
        print("\n3. 다중 서보 제어 테스트 (채널 0, 1, 2)")
        servo_positions = {0: 45, 1: 90, 2: 135}
        controller.set_multiple_servos(servo_positions)
        time.sleep(2)

        # 4. 스윕 동작 테스트
        print("\n4. 스윕 동작 테스트 (채널 2)")
        controller.sweep_servo(2, 30, 150, 1.5, 2)

        # 5. 문서 예제 테스트
        print("\n5. 문서 예제 테스트 (채널 3)")
        controller.document_example_test()

        # 6. PWM 직접 제어 테스트
        print("\n6. PWM 직접 제어 테스트 (채널 4)")
        pwm_values = [200, 300, 400, 500]
        for pwm_val in pwm_values:
            print(f"  → PWM {pwm_val}")
            controller.set_servo_pwm(4, pwm_val)
            time.sleep(1)

        print("\n서보모터 테스트 완료!")

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    finally:
        controller.cleanup()


def test_single_servo():
    """단일 서보모터 대화형 테스트"""
    controller = ServoMotorController()

    try:
        channel = int(input("테스트할 서보 채널 (0-15): "))

        print(f"서보 {channel} 대화형 테스트")
        print("명령어: angle <각도> | pwm <값> | center | sweep | calibrate | quit")

        while True:
            command = input("명령 입력: ").strip().split()

            if not command:
                continue

            cmd = command[0].lower()

            if cmd == "quit" or cmd == "q":
                break
            elif cmd == "angle" and len(command) == 2:
                try:
                    angle = float(command[1])
                    controller.set_servo_angle(channel, angle)
                except ValueError:
                    print("올바른 각도 값을 입력하세요.")
            elif cmd == "pwm" and len(command) == 2:
                try:
                    pwm_val = int(command[1])
                    controller.set_servo_pwm(channel, pwm_val)
                except ValueError:
                    print("올바른 PWM 값을 입력하세요.")
            elif cmd == "center":
                controller.center_servo(channel)
            elif cmd == "sweep":
                controller.sweep_servo(channel, 0, 180, 1.0, 1)
            elif cmd == "calibrate":
                controller.calibrate_servo(channel)
            else:
                print("알 수 없는 명령어입니다.")

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except ValueError:
        print("올바른 채널 번호를 입력하세요.")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        # 단일 서보 대화형 테스트
        test_single_servo()
    else:
        # 종합 테스트
        test_servo_motors()
