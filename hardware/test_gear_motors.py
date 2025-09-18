#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
기어 모터 수동 제어 모듈 (개선버전)
- L298N 모터 드라이버를 통한 DC 모터 제어
- WASD 키보드 입력을 통한 실시간 수동 제어
- 간결한 함수형 접근법으로 재작성
- 핀 매핑 문제 해결
"""

import RPi.GPIO as GPIO
import time
import sys
import select
import tty
import termios

# BCM 모드 GPIO 핀 정의 (pinout.md 기준)
ENA, ENB = 26, 17  # PWM 활성화 핀
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

    # PWM 객체 생성 (더 낮은 주파수 사용 - 모터 드라이버 호환성)
    pwmA = GPIO.PWM(ENA, 1000)  # 100Hz로 변경
    pwmB = GPIO.PWM(ENB, 1000)  # 100Hz로 변경

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


def get_key():
    """
    개선된 키 입력 받기 (차단 방식)
    터미널에서 키 입력을 확실하게 감지
    """
    if sys.stdin.isatty():
        # 터미널 설정 저장
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            # raw 모드로 변경 (즉시 입력 감지)
            tty.setraw(sys.stdin.fileno())
            
            # 키 입력 대기 (차단 방식)
            key = sys.stdin.read(1)
            
            # 특수 키 처리 (ESC 시퀀스)
            if ord(key) == 27:  # ESC
                return "esc"
            elif ord(key) == 32:  # Space
                return " "
            elif ord(key) == 127:  # Backspace/Delete
                return "del"
            else:
                return key
                
        except KeyboardInterrupt:
            return "q"  # Ctrl+C를 q로 처리
        finally:
            # 터미널 설정 복원
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    return None


def manual_control_mode():
    """
    단순 모터 제어 모드
    숫자 키로 직접 속도 설정 (1~9), 방향키로 제어
    """
    print("=" * 50)
    print("단순 모터 제어 모드")
    print("=" * 50)
    print("속도 설정:")
    print("  1~9: 직접 속도 설정 (10%~90%)")
    print("방향 제어:")
    print("  W: 전진")
    print("  S: 후진") 
    print("  A: 좌회전")
    print("  D: 우회전")
    print("  Space: 정지")
    print("  Q: 종료")
    print("=" * 50)

    # 기본 속도 설정
    base_speed = 30
    current_right_speed = 0
    current_left_speed = 0

    print(f"현재 속도: {base_speed}% | 키를 눌러주세요...")
    
    try:
        while True:
            key = get_key()

            if key:
                key = key.lower()

                # 숫자 키로 속도 직접 설정
                if key in "123456789":
                    base_speed = int(key) * 10
                    print(f"🎯 속도 설정: {base_speed}%")

                # 방향 제어
                elif key == "w":  # 전진
                    current_right_speed = base_speed
                    current_left_speed = base_speed
                    print(f"⬆️  전진 {base_speed}%")
                    drive(current_right_speed, current_left_speed)

                elif key == "s":  # 후진
                    current_right_speed = -base_speed
                    current_left_speed = -base_speed
                    print(f"⬇️  후진 {base_speed}%")
                    drive(current_right_speed, current_left_speed)

                elif key == "a":  # 좌회전
                    current_right_speed = base_speed
                    current_left_speed = 0
                    print(f"⬅️  좌회전 {base_speed}%")
                    drive(current_right_speed, current_left_speed)

                elif key == "d":  # 우회전
                    current_right_speed = 0
                    current_left_speed = base_speed
                    print(f"➡️  우회전 {base_speed}%")
                    drive(current_right_speed, current_left_speed)

                elif key == " ":  # 정지
                    current_right_speed = 0
                    current_left_speed = 0
                    print("⏹️  정지")
                    drive(current_right_speed, current_left_speed)

                elif key == "q":  # 종료
                    print("👋 종료")
                    break

                else:
                    print(f"알 수 없는 키: {key}")

            else:
                # 키 입력이 없으면 잠시 대기
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n키보드 인터럽트로 종료")
    finally:
        motor_stop()
        print("모터 정지 완료")


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

        # PWM 객체 생성 및 시작 (낮은 주파수)
        self.pwmA = GPIO.PWM(ENA, 100)  # 100Hz로 변경
        self.pwmB = GPIO.PWM(ENB, 100)  # 100Hz로 변경
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


def test_individual_motors():
    """개별 모터 테스트 - 좌우 모터를 따로 테스트"""
    print("=" * 50)
    print("개별 모터 PWM 테스트")
    print("=" * 50)
    
    try:
        setup()
        
        # 오른쪽 모터 (모터A) 단독 테스트
        print("\n🔧 오른쪽 모터(A) 테스트:")
        test_levels = [20, 40, 60, 80]
        
        for level in test_levels:
            print(f"  오른쪽 모터 {level}% 테스트 (2초)")
            motor_a_control(+1, level)  # 오른쪽 모터만
            motor_b_control(0, 0)       # 왼쪽 모터 정지
            time.sleep(2.0)
            motor_stop()
            time.sleep(1.0)
            
        # 왼쪽 모터 (모터B) 단독 테스트  
        print("\n🔧 왼쪽 모터(B) 테스트:")
        
        for level in test_levels:
            print(f"  왼쪽 모터 {level}% 테스트 (2초)")
            motor_a_control(0, 0)       # 오른쪽 모터 정지
            motor_b_control(+1, level)  # 왼쪽 모터만
            time.sleep(2.0)
            motor_stop()
            time.sleep(1.0)
            
        print("\n✅ 개별 모터 테스트 완료")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류: {e}")
    finally:
        motor_stop()
        cleanup()


def test_hardware_diagnosis():
    """하드웨어 진단 테스트"""
    print("=" * 50)
    print("🔍 하드웨어 진단 테스트")
    print("=" * 50)
    
    try:
        setup()
        
        print("1️⃣ ENA 핀(모터A PWM) 테스트:")
        print("   - ENA 핀에 점퍼 캡이 있다면 제거하세요")
        print("   - PWM 신호 확인")
        
        # ENA PWM 직접 테스트
        for duty in [30, 50, 70]:
            print(f"   🔧 ENA PWM {duty}% 설정")
            GPIO.output(A1, GPIO.HIGH)  # 방향 설정
            GPIO.output(A2, GPIO.LOW)
            pwmA.ChangeDutyCycle(duty)  # PWM 직접 제어
            time.sleep(2)
            
        pwmA.ChangeDutyCycle(0)
        
        print("\n2️⃣ ENB 핀(모터B PWM) 테스트:")
        print("   - ENB 핀에 점퍼 캡이 있다면 제거하세요")
        
        # ENB PWM 직접 테스트
        for duty in [30, 50, 70]:
            print(f"   🔧 ENB PWM {duty}% 설정")
            GPIO.output(B1, GPIO.HIGH)  # 방향 설정
            GPIO.output(B2, GPIO.LOW)
            pwmB.ChangeDutyCycle(duty)  # PWM 직접 제어
            time.sleep(2)
            
        pwmB.ChangeDutyCycle(0)
        
        print("\n3️⃣ 핀 연결 확인:")
        print(f"   - ENA(PWM): GPIO {ENA}")
        print(f"   - A1(방향): GPIO {A1}")
        print(f"   - A2(방향): GPIO {A2}")
        print(f"   - ENB(PWM): GPIO {ENB}")
        print(f"   - B1(방향): GPIO {B1}")  
        print(f"   - B2(방향): GPIO {B2}")
        
        print("\n✅ 하드웨어 진단 완료")
        
    except Exception as e:
        print(f"❌ 진단 중 오류: {e}")
    finally:
        motor_stop()
        cleanup()


if __name__ == "__main__":
    import sys
    
    try:
        print("🚗 모터 테스트 프로그램")
        print("=" * 40)
        print("사용법:")
        print("  python3 test_gear_motors.py        - 수동 제어")
        print("  python3 test_gear_motors.py motor  - 개별 모터 테스트")
        print("  python3 test_gear_motors.py check  - 하드웨어 진단")
        print("=" * 40)
        
        if len(sys.argv) > 1:
            if sys.argv[1] == "motor":
                test_individual_motors()
            elif sys.argv[1] == "check":
                test_hardware_diagnosis()
            else:
                print("알 수 없는 옵션입니다.")
        else:
            setup()
            manual_control_mode()

    except KeyboardInterrupt:
        print("\n👋 프로그램 종료")
    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        cleanup()
