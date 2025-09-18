import time
import sys
import select
import tty
import termios
import RPi.GPIO as GPIO

# GPIO 설정
Motor_A_EN = 26
Motor_A_Pin1 = 26
Motor_A_Pin2 = 21

# Motor_A_EN = 17
# Motor_A_Pin1 = 27
# Motor_A_Pin2 = 18
speed = 20

def setup():
    """모터 초기화"""
    global pwm_A
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(Motor_A_EN, GPIO.OUT)
    GPIO.setup(Motor_A_Pin1, GPIO.OUT)
    GPIO.setup(Motor_A_Pin2, GPIO.OUT)
    
    # PWM 설정 (1000Hz)
    pwm_A = GPIO.PWM(Motor_A_EN, 1000)
    pwm_A.start(0)

def move(speed, direction):
    """모터 이동 제어"""
    # PWM 활성화 핀 확인
    GPIO.output(Motor_A_EN, GPIO.HIGH)
    
    if direction == 'forward':
        GPIO.output(Motor_A_Pin1, GPIO.HIGH)
        GPIO.output(Motor_A_Pin2, GPIO.LOW)
    elif direction == 'backward':
        GPIO.output(Motor_A_Pin1, GPIO.LOW)
        GPIO.output(Motor_A_Pin2, GPIO.HIGH)
    
    pwm_A.ChangeDutyCycle(speed)

def motorBrake():
    """모터 브레이크 (즉시 정지)"""
    try:
        # 브레이크: 두 방향 핀을 모두 HIGH로 설정
        GPIO.output(Motor_A_Pin1, GPIO.HIGH)
        GPIO.output(Motor_A_Pin2, GPIO.HIGH)
        pwm_A.ChangeDutyCycle(100)  # 최대 브레이크력
        time.sleep(0.1)  # 짧은 브레이크
        
        # 완전 정지
        GPIO.output(Motor_A_Pin1, GPIO.LOW)
        GPIO.output(Motor_A_Pin2, GPIO.LOW)
        pwm_A.ChangeDutyCycle(0)
        
    except Exception as e:
        print(f"브레이크 오류: {e}")

def motorStop():
    """모터 강제 완전 정지"""
    global pwm_A
    try:
        # 1단계: PWM 완전 정지
        pwm_A.ChangeDutyCycle(0)
        
        # 2단계: 방향 핀 모두 LOW (브레이크 효과)
        GPIO.output(Motor_A_Pin1, GPIO.LOW)
        GPIO.output(Motor_A_Pin2, GPIO.LOW)
        
        # 3단계: PWM 활성화 핀도 LOW로 설정 (완전 차단)
        GPIO.output(Motor_A_EN, GPIO.LOW)
        time.sleep(0.2)  # 완전 정지 대기
        
        # 4단계: PWM 재활성화 (다음 동작을 위해)
        GPIO.output(Motor_A_EN, GPIO.HIGH)
        
    except Exception as e:
        print(f"모터 정지 오류: {e}")
        # 강제 핀 정지
        try:
            GPIO.output(Motor_A_Pin1, GPIO.LOW)
            GPIO.output(Motor_A_Pin2, GPIO.LOW)
            GPIO.output(Motor_A_EN, GPIO.LOW)
        except:
            pass

def destroy():
    """완전 리소스 해제 및 초기화"""
    global pwm_A
    try:
        print("\n🔄 시스템 종료 중...")
        
        # 모터 완전 정지
        motorStop()
        
        # PWM 객체 정리
        if 'pwm_A' in globals():
            pwm_A.stop()
            
        # GPIO 완전 정리
        GPIO.cleanup()
        
        print("✅ 시스템 정리 완료")
        
    except Exception as e:
        print(f"정리 중 오류: {e}")
        # 강제 GPIO 정리
        try:
            GPIO.cleanup()
        except:
            pass

def get_key():
    """개선된 키보드 입력 받기"""
    if sys.stdin.isatty():
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            
            # 키 입력 대기 (차단 방식)
            key = sys.stdin.read(1)
            
            # 특수 키 처리
            if ord(key) == 27:  # ESC
                return "q"
            elif ord(key) == 13:  # Enter
                return "enter"
            elif ord(key) == 32:  # Space
                return " "
            elif ord(key) == 127:  # Backspace/Delete
                return "del"
            else:
                return key
                
        except KeyboardInterrupt:
            return "q"
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    return None

def keyboard_control():
    """키보드 제어 모드"""
    global speed
    
    print("=" * 50)
    print("🚗 오른쪽 모터(A) 속도 테스트")
    print("=" * 50)
    print("속도 설정:")
    print("  0: 0% (정지)")
    print("  1~9: 10%~90% 속도")
    print("제어:")
    print("  W: 직진 테스트")
    print("  Enter: 직진 테스트 (W와 같음)")
    print("  Space: 정지")
    print("  B: 브레이크 (즉시 정지)")
    print("  Q: 종료")
    print("=" * 50)
    
    print(f"현재 속도: {speed}% | 키를 입력하세요...")
    
    try:
        while True:
            key = get_key()
            
            if key:
                key = key.lower()
                
                # 숫자 키로 속도 설정
                if key in "0123456789":
                    speed = int(key) * 10
                    motorStop()  # 속도 변경시 일단 정지
                    print(f"🎯 속도 설정: {speed}%")
                
                # W키 또는 Enter키로 직진 테스트
                elif key == "w" or key == "enter":
                    if speed > 0:
                        print(f"⬆️  직진 테스트 {speed}% (2초간)")
                        try:
                            move(speed, 'forward')
                            time.sleep(1.0)
                        except Exception as e:
                            print(f"모터 제어 오류: {e}")
                        finally:
                            motorBrake()  # 브레이크 사용
                            print("⏹️  테스트 완료")
                    else:
                        print("⚠️  속도를 먼저 설정하세요 (1~9)")
                
                # Space키로 정지
                elif key == " ":
                    motorStop()
                    print("⏹️  모터 정지")
                
                # B키로 브레이크
                elif key == "b":
                    motorBrake()
                    print("🛑 모터 브레이크!")
                
                # Q키 또는 ESC키로 종료
                elif key == "q" or key == "\x1b":
                    print("👋 프로그램 종료")
                    break
                
                else:
                    print(f"❓ 알 수 없는 키: {key} (코드: {ord(key)})")
    
    except KeyboardInterrupt:
        print("\n🛑 키보드 인터럽트로 종료")
    except Exception as e:
        print(f"❌ 오류: {e}")
    finally:
        # 모터 강제 정지
        try:
            motorStop()
        except:
            pass

# 실행 메인
if __name__ == '__main__':
    try:
        print("🔧 모터 초기화 중...")
        setup()
        print("✅ 초기화 완료")
        keyboard_control()
    except KeyboardInterrupt:
        print("\n🛑 키보드 인터럽트로 프로그램 종료")
    except Exception as e:
        print(f"❌ 실행 중 오류: {e}")
    finally:
        destroy()