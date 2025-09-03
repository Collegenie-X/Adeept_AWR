#!/usr/bin/env python3
# 파일명: motor_controller.py
# 설명: 기어모터 4개 제어를 위한 모터 컨트롤러 클래스
# 작성일: 2024
"""
라즈베리파이 기반 4개 기어모터 제어 모듈
- 전진, 후진, 좌회전, 우회전 기능
- PWM 속도 제어
- 안전한 모터 정지 기능
"""

import time
import RPi.GPIO as GPIO
from typing import Optional, Tuple, Union


class MotorController:
    """기어모터 4개를 제어하는 컨트롤러 클래스"""
    
    def __init__(self):
        """모터 컨트롤러 초기화"""
        # 모터 핀 설정 (L298N 모터 드라이버 기준)
        self.motor_a_enable_pin = 7      # 우측 모터 Enable 핀
        self.motor_b_enable_pin = 11     # 좌측 모터 Enable 핀
        
        self.motor_a_pin1 = 8            # 우측 모터 방향 핀1
        self.motor_a_pin2 = 10           # 우측 모터 방향 핀2
        self.motor_b_pin1 = 13           # 좌측 모터 방향 핀1
        self.motor_b_pin2 = 12           # 좌측 모터 방향 핀2
        
        # 방향 상수 정의
        self.DIR_FORWARD = 1
        self.DIR_BACKWARD = 0
        
        # PWM 객체 초기화
        self.pwm_a: Optional[GPIO.PWM] = None
        self.pwm_b: Optional[GPIO.PWM] = None
        
        # 초기화 상태 플래그
        self.is_initialized = False
    
    def initialize_gpio(self) -> bool:
        """GPIO 핀 초기화 및 PWM 설정"""
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BOARD)
            
            # GPIO 핀 설정
            gpio_pins = [
                self.motor_a_enable_pin, self.motor_b_enable_pin,
                self.motor_a_pin1, self.motor_a_pin2,
                self.motor_b_pin1, self.motor_b_pin2
            ]
            
            for pin in gpio_pins:
                GPIO.setup(pin, GPIO.OUT)
            
            # 모터 정지 상태로 초기화
            self.stop_all_motors()
            
            # PWM 객체 생성 (1000Hz 주파수)
            self.pwm_a = GPIO.PWM(self.motor_a_enable_pin, 1000)
            self.pwm_b = GPIO.PWM(self.motor_b_enable_pin, 1000)
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            print(f"GPIO 초기화 오류: {e}")
            return False
    
    def _check_initialization(self) -> bool:
        """초기화 상태 확인"""
        if not self.is_initialized:
            print("경고: 모터 컨트롤러가 초기화되지 않았습니다.")
            return False
        return True
    
    def control_right_motor(self, enable: bool, direction: int, speed: int) -> None:
        """우측 모터 제어"""
        if not self._check_initialization():
            return
            
        if not enable:
            # 모터 정지
            GPIO.output(self.motor_a_pin1, GPIO.LOW)
            GPIO.output(self.motor_a_pin2, GPIO.LOW)
            GPIO.output(self.motor_a_enable_pin, GPIO.LOW)
        else:
            # 속도 범위 검증 (0-100)
            speed = max(0, min(100, speed))
            
            if direction == self.DIR_FORWARD:
                GPIO.output(self.motor_a_pin1, GPIO.HIGH)
                GPIO.output(self.motor_a_pin2, GPIO.LOW)
                self.pwm_a.start(100)
                self.pwm_a.ChangeDutyCycle(speed)
            elif direction == self.DIR_BACKWARD:
                GPIO.output(self.motor_a_pin1, GPIO.LOW)
                GPIO.output(self.motor_a_pin2, GPIO.HIGH)
                self.pwm_a.start(0)
                self.pwm_a.ChangeDutyCycle(speed)
    
    def control_left_motor(self, enable: bool, direction: int, speed: int) -> None:
        """좌측 모터 제어"""
        if not self._check_initialization():
            return
            
        if not enable:
            # 모터 정지
            GPIO.output(self.motor_b_pin1, GPIO.LOW)
            GPIO.output(self.motor_b_pin2, GPIO.LOW)
            GPIO.output(self.motor_b_enable_pin, GPIO.LOW)
        else:
            # 속도 범위 검증 (0-100)
            speed = max(0, min(100, speed))
            
            if direction == self.DIR_BACKWARD:
                GPIO.output(self.motor_b_pin1, GPIO.HIGH)
                GPIO.output(self.motor_b_pin2, GPIO.LOW)
                self.pwm_b.start(100)
                self.pwm_b.ChangeDutyCycle(speed)
            elif direction == self.DIR_FORWARD:
                GPIO.output(self.motor_b_pin1, GPIO.LOW)
                GPIO.output(self.motor_b_pin2, GPIO.HIGH)
                self.pwm_b.start(0)
                self.pwm_b.ChangeDutyCycle(speed)
    
    def move_forward(self, speed: int = 80) -> None:
        """전진 동작"""
        self.control_left_motor(True, self.DIR_FORWARD, speed)
        self.control_right_motor(True, self.DIR_FORWARD, speed)
    
    def move_backward(self, speed: int = 80) -> None:
        """후진 동작"""
        self.control_left_motor(True, self.DIR_BACKWARD, speed)
        self.control_right_motor(True, self.DIR_BACKWARD, speed)
    
    def turn_left(self, speed: int = 80, radius: float = 0.6) -> None:
        """좌회전 동작 (내측 바퀴 속도 조절)"""
        inner_speed = int(speed * radius)
        self.control_left_motor(True, self.DIR_FORWARD, inner_speed)
        self.control_right_motor(True, self.DIR_FORWARD, speed)
    
    def turn_right(self, speed: int = 80, radius: float = 0.6) -> None:
        """우회전 동작 (내측 바퀴 속도 조절)"""
        inner_speed = int(speed * radius)
        self.control_left_motor(True, self.DIR_FORWARD, speed)
        self.control_right_motor(True, self.DIR_FORWARD, inner_speed)
    
    def pivot_left(self, speed: int = 80) -> None:
        """제자리 좌회전 (좌측 바퀴 후진, 우측 바퀴 전진)"""
        self.control_left_motor(True, self.DIR_BACKWARD, speed)
        self.control_right_motor(True, self.DIR_FORWARD, speed)
    
    def pivot_right(self, speed: int = 80) -> None:
        """제자리 우회전 (좌측 바퀴 전진, 우측 바퀴 후진)"""
        self.control_left_motor(True, self.DIR_FORWARD, speed)
        self.control_right_motor(True, self.DIR_BACKWARD, speed)
    
    def stop_all_motors(self) -> None:
        """모든 모터 정지"""
        GPIO.output(self.motor_a_pin1, GPIO.LOW)
        GPIO.output(self.motor_a_pin2, GPIO.LOW)
        GPIO.output(self.motor_b_pin1, GPIO.LOW)
        GPIO.output(self.motor_b_pin2, GPIO.LOW)
        GPIO.output(self.motor_a_enable_pin, GPIO.LOW)
        GPIO.output(self.motor_b_enable_pin, GPIO.LOW)
    
    def cleanup(self) -> None:
        """GPIO 리소스 정리"""
        if self.is_initialized:
            self.stop_all_motors()
            GPIO.cleanup()
            self.is_initialized = False
            print("모터 컨트롤러 정리 완료")


def main():
    """모터 컨트롤러 테스트 함수"""
    motor = MotorController()
    
    if not motor.initialize_gpio():
        print("모터 초기화 실패")
        return
    
    try:
        print("모터 테스트 시작...")
        
        # 전진 테스트
        print("전진 테스트 (1초)")
        motor.move_forward(50)
        time.sleep(1)
        
        # 후진 테스트
        print("후진 테스트 (1초)")
        motor.move_backward(50)
        time.sleep(1)
        
        # 좌회전 테스트
        print("좌회전 테스트 (1초)")
        motor.turn_left(50)
        time.sleep(1)
        
        # 우회전 테스트
        print("우회전 테스트 (1초)")
        motor.turn_right(50)
        time.sleep(1)
        
        print("모터 테스트 완료")
        
    except KeyboardInterrupt:
        print("사용자에 의해 테스트 중단")
    finally:
        motor.cleanup()


if __name__ == '__main__':
    main()
