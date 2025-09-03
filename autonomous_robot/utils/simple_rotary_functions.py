#!/usr/bin/env python3
# 파일명: simple_rotary_functions.py
# 설명: 원형 로터리 구간을 위한 간단한 함수들 (고등학생 수준)
# 작성일: 2024

import time
from typing import Tuple, Dict, List

# =============================================================================
# 전역 변수들 (로터리 상태 저장용)
# =============================================================================

# 센서 읽기 기록 저장 (최근 20개까지)
recent_sensor_readings = []

# 방향별 카운트 저장
left_count_in_window = 0
right_count_in_window = 0
center_count_in_window = 0

# 로터리 상태 추적
is_currently_in_rotary = False
rotary_start_time = 0.0
consecutive_same_direction_count = 0
last_detected_direction = ""

# 설정값들
SENSOR_MEMORY_SIZE = 20  # 기억할 센서 읽기 개수
ROTARY_DETECTION_THRESHOLD = 4  # 로터리 감지를 위한 최소 좌우 변화 횟수
DIRECTION_DECISION_THRESHOLD = 12  # 방향 결정을 위한 최소 센서 개수


# =============================================================================
# 기본 센서 처리 함수들
# =============================================================================

def read_three_line_sensors_and_convert_to_position(left_pin: int, center_pin: int, right_pin: int) -> str:
    """
    3개 라인센서를 읽어서 로봇이 어디에 있는지 알아내는 함수
    
    센서값 조합에 따른 위치:
    - 가운데 센서만 감지: "center" (정상 주행)
    - 왼쪽 센서만 감지: "left" (오른쪽으로 돌아야 함)
    - 오른쪽 센서만 감지: "right" (왼쪽으로 돌아야 함)
    - 아무것도 감지 안됨: "lost" (라인을 놓침)
    - 여러개 동시 감지: "multiple" (교차로나 넓은 라인)
    """
    try:
        import RPi.GPIO as GPIO
        
        left_sensor_value = GPIO.input(left_pin)
        center_sensor_value = GPIO.input(center_pin)
        right_sensor_value = GPIO.input(right_pin)
        
        # 감지된 센서 개수 세기
        detected_sensor_count = left_sensor_value + center_sensor_value + right_sensor_value
        
        if detected_sensor_count == 0:
            return "lost"
        elif detected_sensor_count > 1:
            return "multiple"
        elif center_sensor_value == 1:
            return "center"
        elif left_sensor_value == 1:
            return "left"
        elif right_sensor_value == 1:
            return "right"
        else:
            return "lost"
            
    except Exception:
        # GPIO가 없는 환경에서는 테스트 값 반환
        return "center"


def add_new_sensor_reading_to_memory(current_position: str) -> None:
    """
    새로운 센서 읽기 결과를 기억 저장소에 추가하는 함수
    오래된 기록은 자동으로 삭제됨 (최근 20개만 보관)
    """
    global recent_sensor_readings
    
    # 현재 시간과 함께 위치 정보 저장
    current_time = time.time()
    new_reading = {
        'position': current_position,
        'time': current_time
    }
    
    # 새 읽기 결과 추가
    recent_sensor_readings.append(new_reading)
    
    # 오래된 기록 제거 (최신 20개만 유지)
    if len(recent_sensor_readings) > SENSOR_MEMORY_SIZE:
        recent_sensor_readings.pop(0)  # 가장 오래된 것 제거


def count_each_direction_in_recent_readings() -> Tuple[int, int, int]:
    """
    최근 센서 읽기들에서 각 방향이 몇 번 나왔는지 세는 함수
    
    반환값: (왼쪽_개수, 가운데_개수, 오른쪽_개수)
    """
    global recent_sensor_readings
    
    left_count = 0
    center_count = 0
    right_count = 0
    
    for reading in recent_sensor_readings:
        position = reading['position']
        if position == "left":
            left_count += 1
        elif position == "center":
            center_count += 1
        elif position == "right":
            right_count += 1
        # "lost"나 "multiple"은 세지 않음
    
    return left_count, center_count, right_count


# =============================================================================
# 로터리 감지 함수들  
# =============================================================================

def check_if_robot_is_entering_rotary_by_analyzing_sensor_pattern() -> bool:
    """
    로봇이 원형 로터리에 진입하고 있는지 센서 패턴을 분석해서 판단하는 함수
    
    로터리 진입의 특징:
    1. 왼쪽과 오른쪽 센서가 번갈아가며 감지됨
    2. 직선에서와 달리 센서 변화가 자주 일어남
    3. 최근 읽기에서 좌우 센서가 모두 여러 번 나타남
    """
    global recent_sensor_readings
    
    # 최소한의 데이터가 필요
    if len(recent_sensor_readings) < 8:
        return False
    
    # 최근 8개 읽기에서 좌우 변화 패턴 분석
    recent_positions = [reading['position'] for reading in recent_sensor_readings[-8:]]
    
    left_appearances = recent_positions.count("left")
    right_appearances = recent_positions.count("right")
    
    # 좌우가 모두 여러 번 나타나고, 너무 한쪽으로 치우치지 않으면 로터리 진입으로 판단
    has_enough_left_right_changes = (left_appearances >= 2 and right_appearances >= 2)
    is_not_too_biased = abs(left_appearances - right_appearances) <= 3
    
    return has_enough_left_right_changes and is_not_too_biased


def update_rotary_status_based_on_current_situation(current_position: str) -> str:
    """
    현재 상황을 보고 로터리 상태를 업데이트하는 함수
    
    반환값: "normal", "entering", "inside", "exiting" 중 하나
    """
    global is_currently_in_rotary, rotary_start_time, consecutive_same_direction_count, last_detected_direction
    
    current_time = time.time()
    
    # 로터리 진입 감지
    if not is_currently_in_rotary and check_if_robot_is_entering_rotary_by_analyzing_sensor_pattern():
        is_currently_in_rotary = True
        rotary_start_time = current_time
        consecutive_same_direction_count = 0
        print("🔄 로터리 진입 감지!")
        return "entering"
    
    # 이미 로터리 안에 있는 경우
    if is_currently_in_rotary:
        time_in_rotary = current_time - rotary_start_time
        
        # 같은 방향이 연속으로 나오는지 체크 (로터리 탈출 신호)
        if current_position == last_detected_direction:
            consecutive_same_direction_count += 1
        else:
            consecutive_same_direction_count = 1
            last_detected_direction = current_position
        
        # 로터리 탈출 조건: 가운데 센서가 연속 5번 이상 감지
        if current_position == "center" and consecutive_same_direction_count >= 5:
            is_currently_in_rotary = False
            print(f"✅ 로터리 탈출! (소요시간: {time_in_rotary:.1f}초)")
            return "exiting"
        
        # 로터리 안에서 너무 오래 있으면 강제로 나가기 모드
        if time_in_rotary > 10.0:  # 10초 넘으면
            is_currently_in_rotary = False
            print("⏰ 로터리에서 너무 오래 있어서 강제 탈출")
            return "exiting"
        
        # 로터리 진입 후 1초 지나면 내부 상태로 전환
        if time_in_rotary > 1.0:
            return "inside"
        else:
            return "entering"
    
    # 평상시 직선 주행
    return "normal"


# =============================================================================
# 로터리 전용 주행 결정 함수들
# =============================================================================

def decide_driving_action_for_normal_line_following(current_position: str) -> Dict[str, any]:
    """
    일반 직선 구간에서의 주행 방향을 결정하는 함수 (기본적인 라인 추적)
    """
    if current_position == "center":
        return {
            'action': 'move_straight_forward',
            'speed': 100,
            'reason': '가운데 라인 감지 - 직진'
        }
    elif current_position == "left":
        return {
            'action': 'turn_right_to_follow_line',
            'speed': 80,
            'reason': '왼쪽 라인 감지 - 오른쪽으로 수정'
        }
    elif current_position == "right":
        return {
            'action': 'turn_left_to_follow_line',
            'speed': 80,
            'reason': '오른쪽 라인 감지 - 왼쪽으로 수정'
        }
    else:  # lost
        return {
            'action': 'move_backward_to_find_line',
            'speed': 50,
            'reason': '라인 놓침 - 후진해서 찾기'
        }


def decide_driving_action_for_rotary_entry(current_position: str) -> Dict[str, any]:
    """
    로터리 진입 시 주행 방향을 결정하는 함수 (조심스럽게)
    """
    left_count, center_count, right_count = count_each_direction_in_recent_readings()
    total_count = left_count + center_count + right_count
    
    if total_count < 5:  # 데이터 부족
        return {
            'action': 'move_straight_forward_slowly',
            'speed': 40,
            'reason': '로터리 진입 - 데이터 부족하여 천천히 직진'
        }
    
    # 가운데가 많이 감지되면 그대로 직진
    if center_count >= total_count * 0.5:
        return {
            'action': 'move_straight_forward_slowly',
            'speed': 60,
            'reason': f'로터리 진입 - 가운데 많음 ({center_count}/{total_count})'
        }
    
    # 왼쪽이 훨씬 많으면 오른쪽으로
    if left_count > right_count * 2:
        return {
            'action': 'turn_right_slowly',
            'speed': 50,
            'reason': f'로터리 진입 - 왼쪽 많음 ({left_count}/{total_count})'
        }
    
    # 오른쪽이 훨씬 많으면 왼쪽으로
    if right_count > left_count * 2:
        return {
            'action': 'turn_left_slowly',
            'speed': 50,
            'reason': f'로터리 진입 - 오른쪽 많음 ({right_count}/{total_count})'
        }
    
    # 애매하면 천천히 직진
    return {
        'action': 'move_straight_forward_slowly',
        'speed': 45,
        'reason': '로터리 진입 - 방향 애매해서 천천히 직진'
    }


def decide_driving_action_for_rotary_inside_using_frequency_method(current_position: str) -> Dict[str, any]:
    """
    로터리 내부에서 주행 방향을 결정하는 함수 (빈도 분석 방법 사용)
    
    이것이 가장 중요한 함수입니다!
    로터리에서 센서가 자주 왼쪽/오른쪽을 오가는 문제를 해결하기 위해
    최근 여러 번의 센서 읽기를 종합해서 판단합니다.
    """
    left_count, center_count, right_count = count_each_direction_in_recent_readings()
    total_count = left_count + center_count + right_count
    
    # 충분한 데이터가 없으면 현재 센서 값 그대로 사용
    if total_count < DIRECTION_DECISION_THRESHOLD:
        return {
            'action': 'move_straight_forward_slowly',
            'speed': 35,
            'reason': f'로터리 내부 - 데이터 부족 ({total_count}개)'
        }
    
    # 각 방향의 비율 계산
    left_ratio = left_count / total_count
    center_ratio = center_count / total_count
    right_ratio = right_count / total_count
    
    # 연속으로 같은 방향이 나오면 보너스 점수 (안정성 확인)
    stability_bonus = 0.15
    global consecutive_same_direction_count, last_detected_direction
    
    if consecutive_same_direction_count >= 3:
        if last_detected_direction == "left":
            left_ratio += stability_bonus
        elif last_detected_direction == "center":
            center_ratio += stability_bonus
        elif last_detected_direction == "right":
            right_ratio += stability_bonus
    
    # 가장 강한 방향으로 결정 (60% 이상이어야 확실한 결정)
    confidence_threshold = 0.6
    
    if center_ratio >= confidence_threshold:
        return {
            'action': 'move_straight_forward',
            'speed': 70,
            'reason': f'로터리 내부 - 가운데 강세 ({center_ratio:.1%}, {consecutive_same_direction_count}연속)'
        }
    
    elif left_ratio >= confidence_threshold and left_ratio > right_ratio * 2:
        return {
            'action': 'turn_right_to_follow_line',
            'speed': 55,
            'reason': f'로터리 내부 - 왼쪽 강세 ({left_ratio:.1%})'
        }
    
    elif right_ratio >= confidence_threshold and right_ratio > left_ratio * 2:
        return {
            'action': 'turn_left_to_follow_line',
            'speed': 55,
            'reason': f'로터리 내부 - 오른쪽 강세 ({right_ratio:.1%})'
        }
    
    else:
        # 애매한 상황에서는 최근 경향 따르기
        recent_trend = analyze_most_recent_sensor_trend()
        return {
            'action': recent_trend['action'],
            'speed': 45,
            'reason': f'로터리 내부 - 최근 경향: {recent_trend["reason"]}'
        }


def analyze_most_recent_sensor_trend() -> Dict[str, str]:
    """
    최근 5번의 센서 읽기에서 가장 마지막에 확실하게 감지된 방향을 찾는 함수
    """
    global recent_sensor_readings
    
    if len(recent_sensor_readings) < 5:
        return {'action': 'move_straight_forward_slowly', 'reason': '데이터 부족'}
    
    # 최근 5개를 거꾸로 확인해서 가장 최근의 명확한 방향 찾기
    recent_5_positions = [reading['position'] for reading in recent_sensor_readings[-5:]]
    
    for position in reversed(recent_5_positions):
        if position == "left":
            return {'action': 'turn_right_to_follow_line', 'reason': '최근 왼쪽 감지'}
        elif position == "right":
            return {'action': 'turn_left_to_follow_line', 'reason': '최근 오른쪽 감지'}
        elif position == "center":
            return {'action': 'move_straight_forward', 'reason': '최근 가운데 감지'}
    
    return {'action': 'move_straight_forward_slowly', 'reason': '최근 경향 불명확'}


def decide_driving_action_for_rotary_exit() -> Dict[str, any]:
    """
    로터리 탈출 시 주행 방향을 결정하는 함수 (안전하게 직진)
    """
    return {
        'action': 'move_straight_forward',
        'speed': 80,
        'reason': '로터리 탈출 - 가운데 라인 따라 직진'
    }


# =============================================================================
# 메인 통합 함수
# =============================================================================

def get_smart_driving_command_for_rotary_and_normal_sections(left_pin: int, center_pin: int, right_pin: int) -> Dict[str, any]:
    """
    로터리와 일반 구간을 모두 처리하는 똑똑한 주행 명령 결정 함수
    
    이 함수가 전체 시스템의 핵심입니다!
    1. 센서를 읽고
    2. 기록에 저장하고  
    3. 로터리 상태를 판단하고
    4. 상황에 맞는 주행 명령을 내립니다
    """
    
    # 1단계: 현재 센서 위치 읽기
    current_position = read_three_line_sensors_and_convert_to_position(left_pin, center_pin, right_pin)
    
    # 2단계: 센서 읽기 기록에 저장
    add_new_sensor_reading_to_memory(current_position)
    
    # 3단계: 로터리 상태 업데이트
    rotary_status = update_rotary_status_based_on_current_situation(current_position)
    
    # 4단계: 상황별 주행 명령 결정
    if rotary_status == "normal":
        driving_decision = decide_driving_action_for_normal_line_following(current_position)
    elif rotary_status == "entering":
        driving_decision = decide_driving_action_for_rotary_entry(current_position)
    elif rotary_status == "inside":
        driving_decision = decide_driving_action_for_rotary_inside_using_frequency_method(current_position)
    else:  # exiting
        driving_decision = decide_driving_action_for_rotary_exit()
    
    # 5단계: 결과 정보 추가
    left_count, center_count, right_count = count_each_direction_in_recent_readings()
    
    final_result = {
        'action': driving_decision['action'],
        'speed': driving_decision['speed'],
        'current_sensor': current_position,
        'rotary_status': rotary_status,
        'reason': driving_decision['reason'],
        'frequency_counts': {
            'left': left_count,
            'center': center_count, 
            'right': right_count
        },
        'total_readings': len(recent_sensor_readings)
    }
    
    return final_result


# =============================================================================
# 디버깅 및 모니터링 함수들
# =============================================================================

def print_current_status_for_debugging():
    """
    현재 로터리 시스템 상태를 출력하는 디버깅 함수
    """
    global is_currently_in_rotary, rotary_start_time, consecutive_same_direction_count
    
    left_count, center_count, right_count = count_each_direction_in_recent_readings()
    
    print(f"\n=== 로터리 시스템 상태 ===")
    print(f"로터리 안에 있나요? {'예' if is_currently_in_rotary else '아니오'}")
    print(f"최근 방향 빈도: 왼쪽={left_count}, 가운데={center_count}, 오른쪽={right_count}")
    print(f"연속 같은 방향: {consecutive_same_direction_count}번")
    print(f"저장된 센서 읽기: {len(recent_sensor_readings)}개")
    
    if is_currently_in_rotary:
        time_in_rotary = time.time() - rotary_start_time
        print(f"로터리 진입 후 시간: {time_in_rotary:.1f}초")
    
    print("=" * 25)


def reset_all_rotary_memory():
    """
    로터리 관련 모든 기억을 초기화하는 함수 (새로 시작할 때 사용)
    """
    global recent_sensor_readings, left_count_in_window, right_count_in_window, center_count_in_window
    global is_currently_in_rotary, rotary_start_time, consecutive_same_direction_count, last_detected_direction
    
    recent_sensor_readings = []
    left_count_in_window = 0
    right_count_in_window = 0  
    center_count_in_window = 0
    is_currently_in_rotary = False
    rotary_start_time = 0.0
    consecutive_same_direction_count = 0
    last_detected_direction = ""
    
    print("🔄 로터리 시스템 메모리 초기화 완료")


# =============================================================================
# 테스트 함수
# =============================================================================

def test_rotary_functions_with_sample_data():
    """
    샘플 데이터로 로터리 함수들을 테스트하는 함수
    """
    print("🧪 로터리 함수 테스트 시작")
    
    # 메모리 초기화
    reset_all_rotary_memory()
    
    # 테스트 시나리오: 직선 → 로터리 진입 → 로터리 내부 → 탈출
    test_sequence = [
        "center", "center", "center", "left", "right", "left", "center", "right",  # 로터리 진입
        "left", "right", "left", "left", "right", "center", "right", "left",       # 로터리 내부
        "center", "center", "center", "center", "center", "center"                 # 로터리 탈출
    ]
    
    for i, position in enumerate(test_sequence):
        print(f"\n--- 단계 {i+1}: 센서 = {position} ---")
        
        # 가짜 핀 번호로 테스트 (실제 GPIO 없이)
        result = get_smart_driving_command_for_rotary_and_normal_sections(35, 36, 37)
        
        print(f"행동: {result['action']}")
        print(f"속도: {result['speed']}")
        print(f"상태: {result['rotary_status']}")
        print(f"이유: {result['reason']}")
        
        time.sleep(0.1)  # 0.1초 간격
    
    print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    # 이 파일을 직접 실행할 때만 테스트 실행
    test_rotary_functions_with_sample_data()
