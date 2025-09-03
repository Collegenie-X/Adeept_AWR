#!/usr/bin/env python3
# 파일명: obstacle_avoidance_strategies.py
# 설명: 초음파 센서를 이용한 장애물 회피 전략 함수들 (고등학생 수준)
# 작성일: 2024

import time
from typing import Dict, List, Optional, Tuple
from enum import Enum

# =============================================================================
# 장애물 회피 상태 및 전략 정의
# =============================================================================

class AvoidanceStrategy(Enum):
    """장애물 회피 전략 종류"""
    SIMPLE_RIGHT_TURN = "simple_right_turn"        # 간단 우회전
    SMART_SIDE_SELECTION = "smart_side_selection"  # 좌우 선택형
    WALL_FOLLOWING = "wall_following"              # 벽 따라가기
    REVERSE_AND_RETRY = "reverse_and_retry"        # 후진 후 재시도
    EMERGENCY_STOP = "emergency_stop"              # 비상 정지

class AvoidancePhase(Enum):
    """회피 단계"""
    DETECTING = "detecting"          # 장애물 감지 중
    PLANNING = "planning"            # 회피 경로 계획 중
    AVOIDING = "avoiding"            # 회피 동작 실행 중
    RETURNING = "returning"          # 원래 경로로 복귀 중
    COMPLETED = "completed"          # 회피 완료

# =============================================================================
# 전역 변수 (회피 상태 추적)
# =============================================================================

# 현재 회피 상태
current_avoidance_strategy = AvoidanceStrategy.SIMPLE_RIGHT_TURN
current_avoidance_phase = AvoidancePhase.DETECTING
avoidance_start_time = 0.0
avoidance_step_count = 0

# 장애물 감지 기록
obstacle_detection_history = []
OBSTACLE_HISTORY_SIZE = 10

# 회피 동작 기록
avoidance_action_sequence = []
MAX_AVOIDANCE_STEPS = 20

# 회피 성공/실패 통계
successful_avoidances = 0
failed_avoidances = 0

# =============================================================================
# 장애물 감지 및 분석 함수들
# =============================================================================

def add_obstacle_detection_to_history(distance_cm: Optional[float], danger_level: str) -> None:
    """
    장애물 감지 결과를 기록에 추가하는 함수
    """
    global obstacle_detection_history
    
    detection_record = {
        'distance': distance_cm,
        'danger_level': danger_level,
        'timestamp': time.time()
    }
    
    obstacle_detection_history.append(detection_record)
    
    # 기록 크기 제한
    if len(obstacle_detection_history) > OBSTACLE_HISTORY_SIZE:
        obstacle_detection_history.pop(0)

def analyze_obstacle_persistence_and_direction() -> Dict[str, any]:
    """
    장애물이 지속적으로 감지되는지, 어느 방향에 있는지 분석하는 함수
    """
    if len(obstacle_detection_history) < 3:
        return {
            'is_persistent': False,
            'danger_trend': 'unknown',
            'recommended_strategy': AvoidanceStrategy.SIMPLE_RIGHT_TURN
        }
    
    # 최근 5개 기록 분석
    recent_records = obstacle_detection_history[-5:]
    
    # 지속성 분석 (위험한 상황이 계속 나타나는가?)
    dangerous_count = 0
    for record in recent_records:
        if record['danger_level'] in ['very_dangerous', 'dangerous']:
            dangerous_count += 1
    
    is_persistent = dangerous_count >= 3
    
    # 위험도 변화 추세 분석
    if len(recent_records) >= 2:
        latest_danger = recent_records[-1]['danger_level']
        previous_danger = recent_records[-2]['danger_level']
        
        danger_levels = ['safe', 'caution', 'dangerous', 'very_dangerous']
        
        try:
            latest_index = danger_levels.index(latest_danger)
            previous_index = danger_levels.index(previous_danger)
            
            if latest_index > previous_index:
                danger_trend = 'getting_worse'
            elif latest_index < previous_index:
                danger_trend = 'getting_better'
            else:
                danger_trend = 'stable'
        except ValueError:
            danger_trend = 'unknown'
    else:
        danger_trend = 'unknown'
    
    # 추천 전략 결정
    if is_persistent and danger_trend == 'getting_worse':
        recommended_strategy = AvoidanceStrategy.REVERSE_AND_RETRY
    elif is_persistent:
        recommended_strategy = AvoidanceStrategy.SMART_SIDE_SELECTION
    else:
        recommended_strategy = AvoidanceStrategy.SIMPLE_RIGHT_TURN
    
    return {
        'is_persistent': is_persistent,
        'danger_trend': danger_trend,
        'dangerous_detection_count': dangerous_count,
        'recommended_strategy': recommended_strategy
    }

# =============================================================================
# 회피 전략별 구현 함수들
# =============================================================================

def execute_simple_right_turn_avoidance(distance_cm: float) -> Dict[str, any]:
    """
    전략 1: 간단한 우회전 회피
    
    가장 기본적인 회피 방법:
    1. 장애물 감지하면 우회전
    2. 일정 시간 직진
    3. 좌회전해서 원래 방향으로 복귀
    """
    global avoidance_step_count, avoidance_start_time, current_avoidance_phase
    
    if current_avoidance_phase == AvoidancePhase.DETECTING:
        # 회피 시작
        current_avoidance_phase = AvoidancePhase.PLANNING
        avoidance_start_time = time.time()
        avoidance_step_count = 0
        
        return {
            'action': 'stop_all_motors',
            'speed': 0,
            'duration': 0.5,
            'next_phase': 'avoiding',
            'reason': '장애물 감지 - 회피 계획 수립'
        }
    
    elif current_avoidance_phase == AvoidancePhase.PLANNING:
        # 우회전 시작
        current_avoidance_phase = AvoidancePhase.AVOIDING
        avoidance_step_count = 1
        
        return {
            'action': 'spin_right_in_place',
            'speed': 60,
            'duration': 1.0,
            'next_phase': 'avoiding',
            'reason': '1단계: 우회전으로 장애물 회피'
        }
    
    elif current_avoidance_phase == AvoidancePhase.AVOIDING:
        if avoidance_step_count == 1:
            # 직진으로 장애물 옆으로 이동
            avoidance_step_count = 2
            return {
                'action': 'move_straight_forward',
                'speed': 50,
                'duration': 1.5,
                'next_phase': 'avoiding',
                'reason': '2단계: 직진으로 장애물 옆 통과'
            }
        
        elif avoidance_step_count == 2:
            # 좌회전으로 원래 방향 복귀
            avoidance_step_count = 3
            current_avoidance_phase = AvoidancePhase.RETURNING
            return {
                'action': 'spin_left_in_place',
                'speed': 60,
                'duration': 1.0,
                'next_phase': 'returning',
                'reason': '3단계: 좌회전으로 원래 방향 복귀'
            }
    
    elif current_avoidance_phase == AvoidancePhase.RETURNING:
        # 회피 완료
        current_avoidance_phase = AvoidancePhase.COMPLETED
        
        return {
            'action': 'move_straight_forward',
            'speed': 70,
            'duration': 0.5,
            'next_phase': 'completed',
            'reason': '4단계: 직진으로 정상 주행 복귀'
        }
    
    else:  # COMPLETED
        # 회피 완료 - 정상 주행으로 복귀
        reset_avoidance_state()
        return {
            'action': 'continue_normal_driving',
            'speed': 80,
            'duration': 0,
            'next_phase': 'detecting',
            'reason': '회피 완료 - 정상 주행 복귀'
        }

def execute_smart_side_selection_avoidance(distance_cm: float) -> Dict[str, any]:
    """
    전략 2: 좌우 스캔해서 더 안전한 쪽으로 회피
    
    더 똑똑한 회피 방법:
    1. 제자리에서 좌우로 고개를 돌려 스캔
    2. 더 안전한 쪽을 선택
    3. 선택한 방향으로 회피
    """
    global avoidance_step_count, current_avoidance_phase
    
    if current_avoidance_phase == AvoidancePhase.DETECTING:
        current_avoidance_phase = AvoidancePhase.PLANNING
        avoidance_step_count = 0
        
        return {
            'action': 'stop_all_motors',
            'speed': 0,
            'duration': 0.3,
            'next_phase': 'planning',
            'reason': '장애물 감지 - 좌우 스캔 준비'
        }
    
    elif current_avoidance_phase == AvoidancePhase.PLANNING:
        if avoidance_step_count == 0:
            # 우측 스캔
            avoidance_step_count = 1
            return {
                'action': 'spin_right_in_place',
                'speed': 30,
                'duration': 0.5,
                'next_phase': 'planning',
                'reason': '우측 방향 안전도 확인 중',
                'scan_direction': 'right'
            }
        
        elif avoidance_step_count == 1:
            # 중앙으로 복귀
            avoidance_step_count = 2
            return {
                'action': 'spin_left_in_place',
                'speed': 30,
                'duration': 0.5,
                'next_phase': 'planning',
                'reason': '중앙 위치로 복귀 중'
            }
        
        elif avoidance_step_count == 2:
            # 좌측 스캔
            avoidance_step_count = 3
            return {
                'action': 'spin_left_in_place',
                'speed': 30,
                'duration': 0.5,
                'next_phase': 'planning',
                'reason': '좌측 방향 안전도 확인 중',
                'scan_direction': 'left'
            }
        
        elif avoidance_step_count == 3:
            # 중앙으로 복귀 후 더 안전한 방향 선택
            avoidance_step_count = 4
            current_avoidance_phase = AvoidancePhase.AVOIDING
            
            # 여기서는 우측을 기본값으로 선택 (실제로는 스캔 결과 활용)
            return {
                'action': 'spin_right_in_place',
                'speed': 30,
                'duration': 0.25,
                'next_phase': 'avoiding',
                'reason': '중앙 복귀 후 안전한 방향 선택'
            }
    
    elif current_avoidance_phase == AvoidancePhase.AVOIDING:
        if avoidance_step_count == 4:
            # 선택한 방향으로 회피 이동
            avoidance_step_count = 5
            return {
                'action': 'move_straight_forward',
                'speed': 60,
                'duration': 2.0,
                'next_phase': 'returning',
                'reason': '안전한 방향으로 회피 이동'
            }
    
    # 복귀 과정은 simple_right_turn과 동일
    return execute_simple_right_turn_avoidance(distance_cm)

def execute_wall_following_avoidance(distance_cm: float) -> Dict[str, any]:
    """
    전략 3: 벽을 따라가며 회피
    
    벽이나 큰 장애물을 따라 이동하는 방법:
    1. 장애물과 일정 거리 유지
    2. 장애물을 오른쪽에 두고 따라가기
    3. 장애물이 끝나면 원래 경로로 복귀
    """
    global avoidance_step_count, current_avoidance_phase
    
    TARGET_WALL_DISTANCE = 25.0  # 벽과 유지할 거리 (cm)
    
    if current_avoidance_phase == AvoidancePhase.DETECTING:
        current_avoidance_phase = AvoidancePhase.AVOIDING
        avoidance_step_count = 0
        
        return {
            'action': 'spin_right_in_place',
            'speed': 50,
            'duration': 0.7,
            'next_phase': 'avoiding',
            'reason': '벽 따라가기 시작 - 우회전'
        }
    
    elif current_avoidance_phase == AvoidancePhase.AVOIDING:
        # 벽과의 거리에 따라 조정
        if distance_cm is None:
            # 거리 측정 실패 시 안전하게 직진
            return {
                'action': 'move_straight_forward',
                'speed': 40,
                'duration': 0.5,
                'next_phase': 'avoiding',
                'reason': '거리 측정 실패 - 안전 속도로 직진'
            }
        
        elif distance_cm < TARGET_WALL_DISTANCE - 5:
            # 벽에 너무 가까움 - 왼쪽으로 조금 이동
            return {
                'action': 'turn_left_to_follow_line',
                'speed': 45,
                'duration': 0.3,
                'next_phase': 'avoiding',
                'reason': f'벽에 너무 가까움 ({distance_cm:.1f}cm) - 좌측으로 조정'
            }
        
        elif distance_cm > TARGET_WALL_DISTANCE + 10:
            # 벽에서 너무 멀어짐 - 오른쪽으로 조금 이동
            return {
                'action': 'turn_right_to_follow_line',
                'speed': 45,
                'duration': 0.3,
                'next_phase': 'avoiding',
                'reason': f'벽에서 너무 멀음 ({distance_cm:.1f}cm) - 우측으로 조정'
            }
        
        else:
            # 적절한 거리 - 직진
            avoidance_step_count += 1
            
            # 일정 시간 후 복귀 시도
            if avoidance_step_count > 15:  # 약 3초 후
                current_avoidance_phase = AvoidancePhase.RETURNING
            
            return {
                'action': 'move_straight_forward',
                'speed': 60,
                'duration': 0.2,
                'next_phase': 'avoiding' if avoidance_step_count <= 15 else 'returning',
                'reason': f'벽 따라가기 중 ({distance_cm:.1f}cm 거리 유지)'
            }
    
    elif current_avoidance_phase == AvoidancePhase.RETURNING:
        # 원래 방향으로 복귀
        current_avoidance_phase = AvoidancePhase.COMPLETED
        return {
            'action': 'spin_left_in_place',
            'speed': 50,
            'duration': 0.7,
            'next_phase': 'completed',
            'reason': '벽 따라가기 완료 - 원래 방향으로 복귀'
        }
    
    else:  # COMPLETED
        reset_avoidance_state()
        return {
            'action': 'continue_normal_driving',
            'speed': 80,
            'duration': 0,
            'next_phase': 'detecting',
            'reason': '벽 따라가기 회피 완료'
        }

def execute_reverse_and_retry_avoidance(distance_cm: float) -> Dict[str, any]:
    """
    전략 4: 후진 후 다른 경로 시도
    
    앞이 막혔을 때 사용하는 방법:
    1. 후진해서 거리 확보
    2. 다른 방향으로 시도
    3. 여러 방향 시도해도 안 되면 정지
    """
    global avoidance_step_count, current_avoidance_phase
    
    if current_avoidance_phase == AvoidancePhase.DETECTING:
        current_avoidance_phase = AvoidancePhase.PLANNING
        avoidance_step_count = 0
        
        return {
            'action': 'move_straight_backward',
            'speed': 50,
            'duration': 1.5,
            'next_phase': 'planning',
            'reason': '막다른 길 감지 - 후진으로 거리 확보'
        }
    
    elif current_avoidance_phase == AvoidancePhase.PLANNING:
        if avoidance_step_count == 0:
            # 첫 번째 시도: 우회전
            avoidance_step_count = 1
            current_avoidance_phase = AvoidancePhase.AVOIDING
            return {
                'action': 'spin_right_in_place',
                'speed': 60,
                'duration': 1.5,
                'next_phase': 'avoiding',
                'reason': '1차 시도: 우회전으로 다른 경로 탐색'
            }
    
    elif current_avoidance_phase == AvoidancePhase.AVOIDING:
        if avoidance_step_count == 1:
            # 우회전 후 직진 시도
            avoidance_step_count = 2
            return {
                'action': 'move_straight_forward',
                'speed': 40,
                'duration': 1.0,
                'next_phase': 'avoiding',
                'reason': '우회전 후 전진 시도'
            }
        
        elif avoidance_step_count == 2:
            # 여전히 막혀있다면 다시 후진
            avoidance_step_count = 3
            return {
                'action': 'move_straight_backward',
                'speed': 50,
                'duration': 1.0,
                'next_phase': 'avoiding',
                'reason': '경로 막힘 - 다시 후진'
            }
        
        elif avoidance_step_count == 3:
            # 좌회전 시도
            avoidance_step_count = 4
            return {
                'action': 'spin_left_in_place',
                'speed': 60,
                'duration': 3.0,
                'next_phase': 'avoiding',
                'reason': '2차 시도: 좌회전으로 다른 경로 탐색'
            }
        
        elif avoidance_step_count == 4:
            # 좌회전 후 직진 시도
            avoidance_step_count = 5
            current_avoidance_phase = AvoidancePhase.RETURNING
            return {
                'action': 'move_straight_forward',
                'speed': 40,
                'duration': 1.0,
                'next_phase': 'returning',
                'reason': '좌회전 후 전진 시도'
            }
    
    elif current_avoidance_phase == AvoidancePhase.RETURNING:
        # 시도 완료
        current_avoidance_phase = AvoidancePhase.COMPLETED
        return {
            'action': 'move_straight_forward',
            'speed': 60,
            'duration': 0.5,
            'next_phase': 'completed',
            'reason': '새로운 경로 찾기 완료'
        }
    
    else:  # COMPLETED
        reset_avoidance_state()
        return {
            'action': 'continue_normal_driving',
            'speed': 80,
            'duration': 0,
            'next_phase': 'detecting',
            'reason': '후진-재시도 회피 완료'
        }

def execute_emergency_stop_avoidance(distance_cm: float) -> Dict[str, any]:
    """
    전략 5: 비상 정지
    
    매우 위험한 상황에서 사용:
    1. 즉시 모든 모터 정지
    2. 사용자 개입 대기
    """
    global current_avoidance_phase
    
    current_avoidance_phase = AvoidancePhase.COMPLETED
    
    return {
        'action': 'stop_all_motors',
        'speed': 0,
        'duration': 0,
        'next_phase': 'emergency',
        'reason': f'비상 상황! 거리 {distance_cm:.1f}cm - 즉시 정지'
    }

# =============================================================================
# 회피 전략 선택 및 관리 함수들
# =============================================================================

def select_best_avoidance_strategy_based_on_situation(
    distance_cm: Optional[float], 
    danger_level: str, 
    line_position: str
) -> AvoidanceStrategy:
    """
    현재 상황을 분석해서 가장 적합한 회피 전략을 선택하는 함수
    """
    # 장애물 지속성 분석
    obstacle_analysis = analyze_obstacle_persistence_and_direction()
    
    # 매우 위험한 상황 - 비상 정지
    if danger_level == 'very_dangerous' or (distance_cm and distance_cm < 8):
        return AvoidanceStrategy.EMERGENCY_STOP
    
    # 지속적이고 악화되는 상황 - 후진 후 재시도
    elif obstacle_analysis['is_persistent'] and obstacle_analysis['danger_trend'] == 'getting_worse':
        return AvoidanceStrategy.REVERSE_AND_RETRY
    
    # 로터리나 복잡한 구간 - 벽 따라가기
    elif line_position in ['multiple', 'lost'] and obstacle_analysis['is_persistent']:
        return AvoidanceStrategy.WALL_FOLLOWING
    
    # 장애물이 지속적 - 스마트 선택
    elif obstacle_analysis['is_persistent']:
        return AvoidanceStrategy.SMART_SIDE_SELECTION
    
    # 일반적인 상황 - 간단한 우회전
    else:
        return AvoidanceStrategy.SIMPLE_RIGHT_TURN

def execute_selected_avoidance_strategy(
    strategy: AvoidanceStrategy, 
    distance_cm: Optional[float]
) -> Dict[str, any]:
    """
    선택된 회피 전략을 실행하는 함수
    """
    global current_avoidance_strategy
    current_avoidance_strategy = strategy
    
    if strategy == AvoidanceStrategy.SIMPLE_RIGHT_TURN:
        return execute_simple_right_turn_avoidance(distance_cm)
    
    elif strategy == AvoidanceStrategy.SMART_SIDE_SELECTION:
        return execute_smart_side_selection_avoidance(distance_cm)
    
    elif strategy == AvoidanceStrategy.WALL_FOLLOWING:
        return execute_wall_following_avoidance(distance_cm)
    
    elif strategy == AvoidanceStrategy.REVERSE_AND_RETRY:
        return execute_reverse_and_retry_avoidance(distance_cm)
    
    elif strategy == AvoidanceStrategy.EMERGENCY_STOP:
        return execute_emergency_stop_avoidance(distance_cm)
    
    else:
        # 기본값: 간단한 우회전
        return execute_simple_right_turn_avoidance(distance_cm)

def get_complete_obstacle_avoidance_command(
    distance_cm: Optional[float], 
    danger_level: str, 
    line_position: str = "center"
) -> Dict[str, any]:
    """
    전체 장애물 회피 시스템의 메인 함수
    
    이 함수를 호출하면:
    1. 현재 상황을 분석하고
    2. 최적의 회피 전략을 선택하고
    3. 해당 전략을 실행합니다
    """
    # 장애물 감지 기록에 추가
    add_obstacle_detection_to_history(distance_cm, danger_level)
    
    # 회피가 진행 중인지 확인
    if current_avoidance_phase != AvoidancePhase.DETECTING:
        # 이미 회피 중이면 현재 전략 계속 실행
        result = execute_selected_avoidance_strategy(current_avoidance_strategy, distance_cm)
    else:
        # 새로운 회피 시작
        if danger_level in ['dangerous', 'very_dangerous']:
            # 최적 전략 선택
            best_strategy = select_best_avoidance_strategy_based_on_situation(
                distance_cm, danger_level, line_position
            )
            
            # 선택된 전략 실행
            result = execute_selected_avoidance_strategy(best_strategy, distance_cm)
        else:
            # 위험하지 않으면 회피 불필요
            result = {
                'action': 'continue_normal_driving',
                'speed': 80,
                'duration': 0,
                'next_phase': 'detecting',
                'reason': '장애물 없음 - 정상 주행 계속'
            }
    
    # 추가 정보 포함
    result.update({
        'avoidance_strategy': current_avoidance_strategy.value,
        'avoidance_phase': current_avoidance_phase.value,
        'step_count': avoidance_step_count,
        'obstacle_distance': distance_cm,
        'danger_level': danger_level
    })
    
    return result

# =============================================================================
# 상태 관리 및 유틸리티 함수들
# =============================================================================

def reset_avoidance_state() -> None:
    """
    회피 상태를 초기화하는 함수 (회피 완료 후 호출)
    """
    global current_avoidance_phase, avoidance_step_count, avoidance_start_time
    global successful_avoidances
    
    current_avoidance_phase = AvoidancePhase.DETECTING
    avoidance_step_count = 0
    
    # 회피 완료 시간 계산
    if avoidance_start_time > 0:
        avoidance_duration = time.time() - avoidance_start_time
        successful_avoidances += 1
        print(f"✅ 회피 성공! (소요시간: {avoidance_duration:.1f}초)")
    
    avoidance_start_time = 0.0

def force_reset_avoidance_system() -> None:
    """
    회피 시스템을 강제로 초기화하는 함수 (문제 발생 시 사용)
    """
    global current_avoidance_strategy, current_avoidance_phase
    global avoidance_step_count, avoidance_start_time
    global obstacle_detection_history, avoidance_action_sequence
    
    current_avoidance_strategy = AvoidanceStrategy.SIMPLE_RIGHT_TURN
    current_avoidance_phase = AvoidancePhase.DETECTING
    avoidance_step_count = 0
    avoidance_start_time = 0.0
    
    obstacle_detection_history = []
    avoidance_action_sequence = []
    
    print("🔄 장애물 회피 시스템 강제 초기화 완료")

def get_avoidance_system_status() -> Dict[str, any]:
    """
    현재 회피 시스템 상태를 반환하는 함수 (디버깅용)
    """
    return {
        'current_strategy': current_avoidance_strategy.value,
        'current_phase': current_avoidance_phase.value,
        'step_count': avoidance_step_count,
        'successful_avoidances': successful_avoidances,
        'failed_avoidances': failed_avoidances,
        'detection_history_count': len(obstacle_detection_history),
        'is_avoiding': current_avoidance_phase != AvoidancePhase.DETECTING
    }

def print_avoidance_status_for_debugging() -> None:
    """
    회피 시스템 상태를 화면에 출력하는 함수
    """
    status = get_avoidance_system_status()
    
    print(f"\n=== 장애물 회피 시스템 상태 ===")
    print(f"현재 전략: {status['current_strategy']}")
    print(f"현재 단계: {status['current_phase']}")
    print(f"단계 번호: {status['step_count']}")
    print(f"회피 중: {'예' if status['is_avoiding'] else '아니오'}")
    print(f"성공한 회피: {status['successful_avoidances']}회")
    print(f"실패한 회피: {status['failed_avoidances']}회")
    print(f"감지 기록: {status['detection_history_count']}개")
    print("=" * 30)

# =============================================================================
# 테스트 함수
# =============================================================================

def test_all_avoidance_strategies():
    """
    모든 회피 전략을 순서대로 테스트하는 함수
    """
    print("🧪 장애물 회피 전략 테스트 시작")
    
    test_scenarios = [
        (15.0, 'dangerous', 'center', '일반적인 장애물'),
        (8.0, 'very_dangerous', 'center', '매우 위험한 장애물'),
        (18.0, 'dangerous', 'multiple', '복잡한 구간의 장애물'),
        (12.0, 'dangerous', 'lost', '라인 분실 + 장애물')
    ]
    
    for distance, danger, line_pos, description in test_scenarios:
        print(f"\n--- {description} 테스트 ---")
        print(f"거리: {distance}cm, 위험도: {danger}, 라인: {line_pos}")
        
        # 회피 시스템 초기화
        force_reset_avoidance_system()
        
        # 회피 명령 생성
        for step in range(5):  # 5단계까지 시뮬레이션
            command = get_complete_obstacle_avoidance_command(distance, danger, line_pos)
            
            print(f"  단계 {step+1}: {command['action']} (속도: {command['speed']}%)")
            print(f"    이유: {command['reason']}")
            
            if command['next_phase'] == 'completed':
                break
            
            time.sleep(0.1)  # 시뮬레이션 간격
    
    print("\n✅ 모든 회피 전략 테스트 완료!")

if __name__ == "__main__":
    # 이 파일을 직접 실행할 때만 테스트 실행
    test_all_avoidance_strategies()
