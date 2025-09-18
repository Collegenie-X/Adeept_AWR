import time
import RPi.GPIO as GPIO

# GPIO 설정
Motor_A_EN = 26
Motor_A_Pin1 = 26
Motor_A_Pin2 = 21


# Motor_A_EN = 17
# Motor_A_Pin1 = 27
# Motor_A_Pin2 = 18

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
    if direction == 'forward':
        GPIO.output(Motor_A_Pin1, GPIO.HIGH)
        GPIO.output(Motor_A_Pin2, GPIO.LOW)
    elif direction == 'backward':
        GPIO.output(Motor_A_Pin1, GPIO.LOW)
        GPIO.output(Motor_A_Pin2, GPIO.HIGH)
    
    pwm_A.ChangeDutyCycle(speed)

def motorStop():
    """모터 정지"""
    pwm_A.ChangeDutyCycle(0)

def destroy():
    """리소스 해제"""
    motorStop()
    GPIO.cleanup()

# 실행 예제
if __name__ == '__main__':
    try:
        setup()
        move(50, 'forward')  # 60% 속도로 전진
        time.sleep(1)
        motorStop()
        destroy()
    except KeyboardInterrupt:
        destroy()
