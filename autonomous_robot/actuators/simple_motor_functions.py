#!/usr/bin/env python3
# 파일명: simple_motor_functions.py  
# 설명: 4개 기어모터를 제어하는 간단한 함수들 (고등학생 수준)
# 작성일: 2024

import time
from typing import Optional

# =============================================================================
# 전역 변수들 (모터 설정)
# =============================================================================

# 모터 핀 번호들 (L298N 드라이버 기준)
LEFT_MOTOR_ENABLE_PIN = 11      # 왼쪽 모터 속도 조절 핀 (PWM)
LEFT_MOTOR_DIRECTION_PIN_1 = 13    # 왼쪽 모터 방향 핀 1
LEFT_MOTOR_DIRECTION_PIN_2 = 12    # 왼쪽 모터 방향 핀 2

RIGHT_MOTOR_ENABLE_PIN = 7       # 오른쪽 모터 속도 조절 핀 (PWM)
RIGHT_MOTOR_DIRECTION_PIN_1 = 8     # 오른쪽 모터 방향 핀 1
RIGHT_MOTOR_DIRECTION_PIN_2 = 10    # 오른쪽 모터 방향 핀 2

# PWM 객체들 (속도 조절용)
left_motor_pwm_controller = None
right_motor_pwm_controller = None

# 모터 초기화 상태
are_motors_initialized = False


# =============================================================================
# 기본 GPIO 설정 함수들
# =============================================================================

def setup_all_motor_pins_and_pwm_controllers() -> bool:
    """
    모든 모터 핀들을 출력으로 설정하고 PWM 컨트롤러를 만드는 함수
    로봇을 시작할 때 한 번만 실행하면 됩니다.
    """
    global left_motor_pwm_controller, right_motor_pwm_controller, are_motors_initialized
    
    try:
        import RPi.GPIO as GPIO
        
        # GPIO 모드 설정 (물리 핀 번호 사용)
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        
        # 모든 모터 핀을 출력으로 설정
        motor_pins = [
            LEFT_MOTOR_ENABLE_PIN, LEFT_MOTOR_DIRECTION_PIN_1, LEFT_MOTOR_DIRECTION_PIN_2,
            RIGHT_MOTOR_ENABLE_PIN, RIGHT_MOTOR_DIRECTION_PIN_1, RIGHT_MOTOR_DIRECTION_PIN_2
        ]
        
        for pin in motor_pins:
            GPIO.setup(pin, GPIO.OUT)
        
        # 모든 모터 일단 정지 상태로 설정
        stop_all_motors_immediately()
        
        # PWM 컨트롤러 생성 (1000Hz 주파수)
        left_motor_pwm_controller = GPIO.PWM(LEFT_MOTOR_ENABLE_PIN, 1000)
        right_motor_pwm_controller = GPIO.PWM(RIGHT_MOTOR_ENABLE_PIN, 1000)
        
        are_motors_initialized = True
        print("✅ 모터 초기화 성공!")
        return True
        
    except Exception as error:
        print(f"❌ 모터 초기화 실패: {error}")
        return False


def check_if_motors_are_ready() -> bool:
    """
    모터들이 사용할 준비가 되었는지 확인하는 함수
    """
    if not are_motors_initialized:
        print("⚠️ 모터가 아직 초기화되지 않았습니다. setup_all_motor_pins_and_pwm_controllers() 함수를 먼저 실행하세요.")
        return False
    return True


# =============================================================================
# 개별 모터 제어 함수들
# =============================================================================

def control_left_motor_with_direction_and_speed(should_move: bool, forward_direction: bool, speed_percentage: int) -> None:
    """
    왼쪽 모터를 상세하게 제어하는 함수
    
    매개변수:
    - should_move: True면 움직임, False면 정지
    - forward_direction: True면 앞으로, False면 뒤로
    - speed_percentage: 속도 (0~100%)
    """
    if not check_if_motors_are_ready():
        return
    
    import RPi.GPIO as GPIO
    
    # 모터 정지
    if not should_move:
        GPIO.output(LEFT_MOTOR_DIRECTION_PIN_1, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_DIRECTION_PIN_2, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_ENABLE_PIN, GPIO.LOW)
        return
    
    # 속도 범위 확인 (0~100 사이로 제한)
    speed_percentage = max(0, min(100, speed_percentage))
    
    # 방향 설정
    if forward_direction:
        # 앞으로 (시계 반대 방향)
        GPIO.output(LEFT_MOTOR_DIRECTION_PIN_1, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_DIRECTION_PIN_2, GPIO.HIGH)
        left_motor_pwm_controller.start(0)
        left_motor_pwm_controller.ChangeDutyCycle(speed_percentage)
    else:
        # 뒤로 (시계 방향)
        GPIO.output(LEFT_MOTOR_DIRECTION_PIN_1, GPIO.HIGH)
        GPIO.output(LEFT_MOTOR_DIRECTION_PIN_2, GPIO.LOW)
        left_motor_pwm_controller.start(100)
        left_motor_pwm_controller.ChangeDutyCycle(speed_percentage)


def control_right_motor_with_direction_and_speed(should_move: bool, forward_direction: bool, speed_percentage: int) -> None:
    """
    오른쪽 모터를 상세하게 제어하는 함수
    
    매개변수:
    - should_move: True면 움직임, False면 정지
    - forward_direction: True면 앞으로, False면 뒤로  
    - speed_percentage: 속도 (0~100%)
    """
    if not check_if_motors_are_ready():
        return
    
    import RPi.GPIO as GPIO
    
    # 모터 정지
    if not should_move:
        GPIO.output(RIGHT_MOTOR_DIRECTION_PIN_1, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_DIRECTION_PIN_2, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_ENABLE_PIN, GPIO.LOW)
        return
    
    # 속도 범위 확인 (0~100 사이로 제한)
    speed_percentage = max(0, min(100, speed_percentage))
    
    # 방향 설정
    if forward_direction:
        # 앞으로 (시계 방향)
        GPIO.output(RIGHT_MOTOR_DIRECTION_PIN_1, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_DIRECTION_PIN_2, GPIO.LOW)
        right_motor_pwm_controller.start(100)
        right_motor_pwm_controller.ChangeDutyCycle(speed_percentage)
    else:
        # 뒤로 (시계 반대 방향)
        GPIO.output(RIGHT_MOTOR_DIRECTION_PIN_1, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_DIRECTION_PIN_2, GPIO.HIGH)
        right_motor_pwm_controller.start(0)
        right_motor_pwm_controller.ChangeDutyCycle(speed_percentage)


# =============================================================================
# 고수준 이동 명령 함수들 (실제로 많이 사용할 함수들)
# =============================================================================

def move_robot_straight_forward_at_speed(speed_percentage: int = 80) -> None:
    """
    로봇을 지정된 속도로 직진시키는 함수
    양쪽 모터를 같은 속도로 앞으로 돌립니다.
    """
    control_left_motor_with_direction_and_speed(True, True, speed_percentage)
    control_right_motor_with_direction_and_speed(True, True, speed_percentage)


def move_robot_straight_backward_at_speed(speed_percentage: int = 80) -> None:
    """
    로봇을 지정된 속도로 후진시키는 함수
    양쪽 모터를 같은 속도로 뒤로 돌립니다.
    """
    control_left_motor_with_direction_and_speed(True, False, speed_percentage)
    control_right_motor_with_direction_and_speed(True, False, speed_percentage)


def turn_robot_left_by_slowing_left_motor(speed_percentage: int = 80, turn_sharpness: float = 0.6) -> None:
    """
    로봇을 왼쪽으로 돌리는 함수 (왼쪽 모터를 느리게 해서)
    
    매개변수:
    - speed_percentage: 기본 속도
    - turn_sharpness: 회전 강도 (0.0~1.0, 낮을수록 급회전)
    """
    left_motor_speed = int(speed_percentage * turn_sharpness)  # 왼쪽 모터는 느리게
    right_motor_speed = speed_percentage                        # 오른쪽 모터는 그대로
    
    control_left_motor_with_direction_and_speed(True, True, left_motor_speed)
    control_right_motor_with_direction_and_speed(True, True, right_motor_speed)


def turn_robot_right_by_slowing_right_motor(speed_percentage: int = 80, turn_sharpness: float = 0.6) -> None:
    """
    로봇을 오른쪽으로 돌리는 함수 (오른쪽 모터를 느리게 해서)
    
    매개변수:
    - speed_percentage: 기본 속도
    - turn_sharpness: 회전 강도 (0.0~1.0, 낮을수록 급회전)
    """
    left_motor_speed = speed_percentage                         # 왼쪽 모터는 그대로
    right_motor_speed = int(speed_percentage * turn_sharpness)  # 오른쪽 모터는 느리게
    
    control_left_motor_with_direction_and_speed(True, True, left_motor_speed)
    control_right_motor_with_direction_and_speed(True, True, right_motor_speed)


def spin_robot_left_in_place_at_speed(speed_percentage: int = 80) -> None:
    """
    로봇을 제자리에서 왼쪽으로 회전시키는 함수
    왼쪽 모터는 뒤로, 오른쪽 모터는 앞으로 돌립니다.
    """
    control_left_motor_with_direction_and_speed(True, False, speed_percentage)  # 왼쪽 후진
    control_right_motor_with_direction_and_speed(True, True, speed_percentage)   # 오른쪽 전진


def spin_robot_right_in_place_at_speed(speed_percentage: int = 80) -> None:
    """
    로봇을 제자리에서 오른쪽으로 회전시키는 함수
    왼쪽 모터는 앞으로, 오른쪽 모터는 뒤로 돌립니다.
    """
    control_left_motor_with_direction_and_speed(True, True, speed_percentage)   # 왼쪽 전진
    control_right_motor_with_direction_and_speed(True, False, speed_percentage) # 오른쪽 후진


def stop_all_motors_immediately() -> None:
    """
    모든 모터를 즉시 정지시키는 함수
    비상 시에 사용합니다.
    """
    if not check_if_motors_are_ready():
        return
    
    import RPi.GPIO as GPIO
    
    # 모든 방향 핀을 LOW로 설정
    GPIO.output(LEFT_MOTOR_DIRECTION_PIN_1, GPIO.LOW)
    GPIO.output(LEFT_MOTOR_DIRECTION_PIN_2, GPIO.LOW)
    GPIO.output(RIGHT_MOTOR_DIRECTION_PIN_1, GPIO.LOW)
    GPIO.output(RIGHT_MOTOR_DIRECTION_PIN_2, GPIO.LOW)
    
    # 모든 Enable 핀을 LOW로 설정 (전원 차단)
    GPIO.output(LEFT_MOTOR_ENABLE_PIN, GPIO.LOW)
    GPIO.output(RIGHT_MOTOR_ENABLE_PIN, GPIO.LOW)


# =============================================================================
# 명령어 기반 모터 제어 함수
# =============================================================================

def execute_driving_action_with_speed(action_name: str, speed_percentage: int = 80) -> None:
    """
    문자열 명령을 받아서 해당하는 모터 동작을 실행하는 함수
    로터리 함수에서 나온 action을 바로 실행할 때 사용합니다.
    
    지원하는 명령어들:
    - "move_straight_forward", "move_straight_forward_slowly"
    - "move_backward_to_find_line" 
    - "turn_left_to_follow_line", "turn_left_slowly"
    - "turn_right_to_follow_line", "turn_right_slowly"
    - "spin_left_in_place", "spin_right_in_place"
    - "stop_all_motors"
    """
    
    if action_name in ["move_straight_forward", "move_straight_forward_slowly"]:
        move_robot_straight_forward_at_speed(speed_percentage)
        
    elif action_name == "move_backward_to_find_line":
        move_robot_straight_backward_at_speed(speed_percentage)
        
    elif action_name in ["turn_left_to_follow_line", "turn_left_slowly"]:
        turn_robot_left_by_slowing_left_motor(speed_percentage)
        
    elif action_name in ["turn_right_to_follow_line", "turn_right_slowly"]:
        turn_robot_right_by_slowing_right_motor(speed_percentage)
        
    elif action_name == "spin_left_in_place":
        spin_robot_left_in_place_at_speed(speed_percentage)
        
    elif action_name == "spin_right_in_place":
        spin_robot_right_in_place_at_speed(speed_percentage)
        
    elif action_name == "stop_all_motors":
        stop_all_motors_immediately()
        
    else:
        print(f"⚠️ 알 수 없는 명령: {action_name}")
        stop_all_motors_immediately()  # 안전을 위해 정지


# =============================================================================
# 안전 및 정리 함수들
# =============================================================================

def cleanup_all_motor_resources_safely() -> None:
    """
    모든 모터 관련 자원을 안전하게 정리하는 함수
    프로그램 종료 시에 반드시 호출해야 합니다.
    """
    global are_motors_initialized
    
    if are_motors_initialized:
        # 모든 모터 정지
        stop_all_motors_immediately()
        
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()  # GPIO 자원 해제
            print("✅ 모터 자원 정리 완료")
        except:
            print("⚠️ GPIO 정리 중 오류 발생")
        
        are_motors_initialized = False


def test_all_motor_movements_step_by_step():
    """
    모든 모터 동작을 단계별로 테스트하는 함수
    """
    print("🧪 모터 테스트 시작...")
    
    if not setup_all_motor_pins_and_pwm_controllers():
        print("❌ 모터 초기화 실패로 테스트 중단")
        return
    
    test_movements = [
        ("직진", "move_straight_forward", 50),
        ("후진", "move_backward_to_find_line", 50),
        ("좌회전", "turn_left_to_follow_line", 50),
        ("우회전", "turn_right_to_follow_line", 50),
        ("제자리 좌회전", "spin_left_in_place", 50),
        ("제자리 우회전", "spin_right_in_place", 50)
    ]
    
    for description, action, speed in test_movements:
        print(f"테스트: {description} ({action})")
        execute_driving_action_with_speed(action, speed)
        time.sleep(1)  # 1초 동안 실행
        stop_all_motors_immediately()
        time.sleep(0.5)  # 0.5초 대기
    
    print("✅ 모터 테스트 완료!")
    cleanup_all_motor_resources_safely()


if __name__ == "__main__":
    # 이 파일을 직접 실행할 때만 테스트 실행
    test_all_motor_movements_step_by_step()
