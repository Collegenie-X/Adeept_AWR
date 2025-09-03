#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
라인 센서 노이즈 필터링 시스템

이 모듈은 3개의 라인 센서(왼쪽, 가운데, 오른쪽)에서 발생하는 노이즈를 
제거하고 안정적인 라인 추적을 위한 필터링 기능을 제공합니다.

주요 기능:
- 다중 샘플링을 통한 노이즈 제거
- 통계적 이상값 감지 및 제거  
- 일관성 검사를 통한 센서 신뢰도 평가
- 센서별 히스토리 관리 및 트렌드 분석
- 센서 고장 감지 및 백업 로직

작성자: 자율주행 로봇 팀
"""

import time
import statistics
from collections import deque
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


# =============================================================================
# 라인 센서 필터링 설정값들
# =============================================================================

# 센서 샘플링 설정
MULTIPLE_SAMPLE_COUNT = 5  # 한 번에 측정할 횟수
SAMPLE_INTERVAL_MS = 5  # 샘플 간격 (밀리초)

# 히스토리 저장 설정
SENSOR_HISTORY_SIZE = 20  # 각 센서별 최근 측정값 저장 개수
RELIABLE_HISTORY_SIZE = 10  # 신뢰할 수 있는 값들 저장 개수
CONSISTENCY_WINDOW_SIZE = 5  # 일관성 검사 윈도우 크기

# 노이즈 감지 임계값들
OUTLIER_DETECTION_THRESHOLD = 2.0  # 이상값 감지 임계치 (표준편차 배수)
CONSISTENCY_THRESHOLD = 0.3  # 일관성 임계치 (30% 이내 변동)
SENSOR_FLIP_RATE_THRESHOLD = 0.5  # 센서 변화율 임계치 (50% 이상 변화시 노이즈)

# 센서 상태 평가
MIN_CONFIDENCE_SCORE = 70.0  # 최소 신뢰도 점수
MAX_CONSECUTIVE_ERRORS = 5  # 최대 연속 오류 허용 횟수


# =============================================================================
# 라인 센서 데이터 클래스
# =============================================================================

@dataclass
class LineSensorReading:
    """라인 센서 한 번의 측정 결과"""
    left: bool
    center: bool
    right: bool
    timestamp: float
    confidence: float = 1.0  # 신뢰도 (0.0 ~ 1.0)
    
    def to_tuple(self) -> Tuple[bool, bool, bool]:
        """튜플 형태로 변환"""
        return (self.left, self.center, self.right)
    
    def to_string(self) -> str:
        """문자열 형태로 변환 (디버깅용)"""
        l = "L" if self.left else "_"
        c = "C" if self.center else "_"
        r = "R" if self.right else "_"
        return f"{l}{c}{r}"
    
    def count_active_sensors(self) -> int:
        """활성화된 센서 개수 반환"""
        return sum([self.left, self.center, self.right])


@dataclass
class LineSensorFilterStatus:
    """라인 센서 필터링 시스템 상태"""
    total_measurements: int = 0
    filtered_measurements: int = 0
    noise_detected_count: int = 0
    sensor_reliability_scores: Dict[str, float] = None
    consecutive_error_counts: Dict[str, int] = None
    is_system_healthy: bool = True
    
    def __post_init__(self):
        if self.sensor_reliability_scores is None:
            self.sensor_reliability_scores = {"left": 100.0, "center": 100.0, "right": 100.0}
        if self.consecutive_error_counts is None:
            self.consecutive_error_counts = {"left": 0, "center": 0, "right": 0}


# =============================================================================
# 전역 변수들 (필터링 시스템 상태)
# =============================================================================

# 센서별 측정 히스토리
left_sensor_history = deque(maxlen=SENSOR_HISTORY_SIZE)
center_sensor_history = deque(maxlen=SENSOR_HISTORY_SIZE)  
right_sensor_history = deque(maxlen=SENSOR_HISTORY_SIZE)

# 신뢰할 수 있는 측정값들
reliable_readings_history = deque(maxlen=RELIABLE_HISTORY_SIZE)

# 필터링 시스템 상태
filter_status = LineSensorFilterStatus()

# 마지막 측정 시간
last_measurement_time = 0.0


# =============================================================================
# 기본 센서 읽기 함수들 (GPIO 인터페이스)
# =============================================================================

def read_single_line_sensor_gpio(pin_number: int) -> bool:
    """
    GPIO를 통해 단일 라인 센서 값을 읽는 함수
    
    매개변수:
    - pin_number: GPIO 핀 번호
    
    반환값: True(라인 감지) 또는 False(라인 없음)
    """
    try:
        import RPi.GPIO as GPIO
        
        # GPIO 설정 (이미 설정되어 있다면 무시)
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(pin_number, GPIO.IN)
        
        # 센서 값 읽기 (LOW = 라인 감지, HIGH = 라인 없음)
        sensor_value = GPIO.input(pin_number)
        line_detected = (sensor_value == GPIO.LOW)
        
        return line_detected
        
    except ImportError:
        # 라즈베리파이가 아닌 환경에서는 시뮬레이션 값 반환
        import random
        return random.choice([True, False])
        
    except Exception as error:
        print(f"⚠️ 라인 센서 {pin_number} 읽기 오류: {error}")
        return False


def read_all_three_line_sensors_once(left_pin: int, center_pin: int, right_pin: int) -> LineSensorReading:
    """
    3개 라인 센서를 한 번에 읽는 함수
    
    매개변수:
    - left_pin: 왼쪽 센서 핀 번호
    - center_pin: 가운데 센서 핀 번호  
    - right_pin: 오른쪽 센서 핀 번호
    
    반환값: LineSensorReading 객체
    """
    current_time = time.time()
    
    # 3개 센서를 동시에 읽기 (시간 차이 최소화)
    left_value = read_single_line_sensor_gpio(left_pin)
    center_value = read_single_line_sensor_gpio(center_pin)
    right_value = read_single_line_sensor_gpio(right_pin)
    
    reading = LineSensorReading(
        left=left_value,
        center=center_value,
        right=right_value,
        timestamp=current_time
    )
    
    return reading


# =============================================================================
# 노이즈 필터링 핵심 함수들
# =============================================================================

def take_multiple_sensor_samples_and_filter(left_pin: int, center_pin: int, right_pin: int) -> Optional[LineSensorReading]:
    """
    여러 번 샘플링해서 노이즈를 제거하는 메인 필터링 함수
    
    과정:
    1. MULTIPLE_SAMPLE_COUNT 횟수만큼 연속 측정
    2. 각 센서별로 다수결 방식으로 최종값 결정
    3. 일관성 검사 수행
    4. 신뢰도 점수 계산
    """
    global filter_status, last_measurement_time
    
    # 샘플링 시작
    samples = []
    sample_start_time = time.time()
    
    for i in range(MULTIPLE_SAMPLE_COUNT):
        reading = read_all_three_line_sensors_once(left_pin, center_pin, right_pin)
        samples.append(reading)
        
        # 샘플 간격 유지
        if i < MULTIPLE_SAMPLE_COUNT - 1:
            time.sleep(SAMPLE_INTERVAL_MS / 1000.0)
    
    filter_status.total_measurements += len(samples)
    
    # 각 센서별로 다수결 방식으로 최종값 결정
    left_votes = sum(1 for s in samples if s.left)
    center_votes = sum(1 for s in samples if s.center)
    right_votes = sum(1 for s in samples if s.right)
    
    # 다수결 결과 (과반수 이상이면 True)
    majority_threshold = MULTIPLE_SAMPLE_COUNT / 2
    final_left = left_votes > majority_threshold
    final_center = center_votes > majority_threshold
    final_right = right_votes > majority_threshold
    
    # 신뢰도 계산 (다수결의 확실성)
    left_confidence = abs(left_votes - majority_threshold) / majority_threshold
    center_confidence = abs(center_votes - majority_threshold) / majority_threshold
    right_confidence = abs(right_votes - majority_threshold) / majority_threshold
    overall_confidence = (left_confidence + center_confidence + right_confidence) / 3.0
    
    # 최종 측정값 생성
    filtered_reading = LineSensorReading(
        left=final_left,
        center=final_center,
        right=final_right,
        timestamp=time.time(),
        confidence=min(1.0, overall_confidence)
    )
    
    # 히스토리에 추가
    left_sensor_history.append(final_left)
    center_sensor_history.append(final_center)
    right_sensor_history.append(final_right)
    
    # 일관성 검사
    is_consistent = check_sensor_reading_consistency(filtered_reading)
    
    if is_consistent:
        reliable_readings_history.append(filtered_reading)
        update_sensor_reliability_scores(True)
        filter_status.filtered_measurements += 1
    else:
        update_sensor_reliability_scores(False)
        filter_status.noise_detected_count += 1
        print(f"⚠️ 라인 센서 일관성 검사 실패: {filtered_reading.to_string()}")
    
    last_measurement_time = time.time()
    
    return filtered_reading if is_consistent else None


def check_sensor_reading_consistency(new_reading: LineSensorReading) -> bool:
    """
    새로운 센서 읽기 값이 이전 값들과 일관성이 있는지 확인
    
    일관성 검사 항목:
    1. 급격한 변화 감지 (모든 센서가 동시에 반전되는 경우)
    2. 비현실적인 패턴 감지 (물리적으로 불가능한 변화)
    3. 히스토리와의 유사성 검사
    """
    if len(reliable_readings_history) < 2:
        return True  # 히스토리가 부족하면 일관성 있다고 가정
    
    # 최근 측정값들과 비교
    recent_readings = list(reliable_readings_history)[-CONSISTENCY_WINDOW_SIZE:]
    
    # 1. 급격한 전체 센서 변화 감지
    if len(recent_readings) >= 1:
        last_reading = recent_readings[-1]
        changes = 0
        if new_reading.left != last_reading.left:
            changes += 1
        if new_reading.center != last_reading.center:
            changes += 1
        if new_reading.right != last_reading.right:
            changes += 1
        
        # 3개 센서가 모두 동시에 변화하는 것은 비현실적
        if changes == 3:
            return False
    
    # 2. 센서별 변화율 계산
    for sensor_name, current_value in [("left", new_reading.left), 
                                      ("center", new_reading.center), 
                                      ("right", new_reading.right)]:
        sensor_history = get_sensor_specific_history(sensor_name)
        if len(sensor_history) >= CONSISTENCY_WINDOW_SIZE:
            recent_values = sensor_history[-CONSISTENCY_WINDOW_SIZE:]
            change_rate = calculate_sensor_change_rate(recent_values)
            
            if change_rate > SENSOR_FLIP_RATE_THRESHOLD:
                return False
    
    # 3. 전체적인 패턴 일관성 (활성 센서 개수 급변 체크)
    if len(recent_readings) >= 3:
        recent_active_counts = [r.count_active_sensors() for r in recent_readings[-3:]]
        new_active_count = new_reading.count_active_sensors()
        
        avg_recent_count = statistics.mean(recent_active_counts)
        if abs(new_active_count - avg_recent_count) > 2:  # 2개 이상 차이나면 이상
            return False
    
    return True


def get_sensor_specific_history(sensor_name: str) -> deque:
    """특정 센서의 히스토리를 반환"""
    if sensor_name == "left":
        return left_sensor_history
    elif sensor_name == "center":
        return center_sensor_history
    elif sensor_name == "right":
        return right_sensor_history
    else:
        return deque()


def calculate_sensor_change_rate(sensor_values: List[bool]) -> float:
    """센서 값들의 변화율을 계산 (0.0 ~ 1.0)"""
    if len(sensor_values) < 2:
        return 0.0
    
    changes = 0
    for i in range(1, len(sensor_values)):
        if sensor_values[i] != sensor_values[i-1]:
            changes += 1
    
    change_rate = changes / (len(sensor_values) - 1)
    return change_rate


def update_sensor_reliability_scores(measurement_was_good: bool) -> None:
    """센서 신뢰도 점수를 업데이트"""
    global filter_status
    
    # 모든 센서에 대해 동일하게 적용 (개별 센서 신뢰도는 추후 확장 가능)
    for sensor_name in ["left", "center", "right"]:
        if measurement_was_good:
            # 좋은 측정 - 신뢰도 상승
            filter_status.sensor_reliability_scores[sensor_name] = min(100.0, 
                filter_status.sensor_reliability_scores[sensor_name] + 2.0)
            filter_status.consecutive_error_counts[sensor_name] = 0
        else:
            # 나쁜 측정 - 신뢰도 하락  
            filter_status.sensor_reliability_scores[sensor_name] = max(0.0,
                filter_status.sensor_reliability_scores[sensor_name] - 5.0)
            filter_status.consecutive_error_counts[sensor_name] += 1
    
    # 전체 시스템 건강성 평가
    avg_reliability = statistics.mean(filter_status.sensor_reliability_scores.values())
    max_consecutive_errors = max(filter_status.consecutive_error_counts.values())
    
    filter_status.is_system_healthy = (avg_reliability >= MIN_CONFIDENCE_SCORE and 
                                      max_consecutive_errors < MAX_CONSECUTIVE_ERRORS)


# =============================================================================
# 고급 필터링 함수들
# =============================================================================

def get_most_reliable_recent_reading() -> Optional[LineSensorReading]:
    """가장 신뢰할 수 있는 최근 측정값을 반환"""
    if not reliable_readings_history:
        return None
    
    # 가장 최근의 신뢰할 수 있는 측정값 반환
    return reliable_readings_history[-1]


def predict_next_sensor_reading_based_on_trend() -> Optional[LineSensorReading]:
    """트렌드를 기반으로 다음 센서 읽기 값을 예측"""
    if len(reliable_readings_history) < 3:
        return None
    
    recent_readings = list(reliable_readings_history)[-3:]
    
    # 각 센서별로 트렌드 분석
    predicted_left = predict_single_sensor_trend([r.left for r in recent_readings])
    predicted_center = predict_single_sensor_trend([r.center for r in recent_readings])
    predicted_right = predict_single_sensor_trend([r.right for r in recent_readings])
    
    predicted_reading = LineSensorReading(
        left=predicted_left,
        center=predicted_center,
        right=predicted_right,
        timestamp=time.time(),
        confidence=0.7  # 예측값이므로 신뢰도 낮음
    )
    
    return predicted_reading


def predict_single_sensor_trend(sensor_values: List[bool]) -> bool:
    """단일 센서의 트렌드를 예측"""
    if len(sensor_values) < 2:
        return False
    
    # 최근 값들 중 다수결로 결정
    true_count = sum(sensor_values)
    return true_count > len(sensor_values) / 2


# =============================================================================
# 메인 인터페이스 함수들
# =============================================================================

def get_filtered_line_sensor_reading(left_pin: int, center_pin: int, right_pin: int) -> Dict[str, Any]:
    """
    노이즈 필터링된 라인 센서 읽기 결과를 반환하는 메인 함수
    
    이 함수를 다른 모듈에서 호출하여 안정적인 라인 센서 값을 얻습니다.
    """
    # 필터링된 측정 시도
    filtered_reading = take_multiple_sensor_samples_and_filter(left_pin, center_pin, right_pin)
    
    if filtered_reading is not None:
        # 성공적인 측정
        result = {
            "sensors": {
                "left": filtered_reading.left,
                "center": filtered_reading.center,
                "right": filtered_reading.right
            },
            "confidence": filtered_reading.confidence,
            "timestamp": filtered_reading.timestamp,
            "sensor_pattern": filtered_reading.to_string(),
            "active_sensor_count": filtered_reading.count_active_sensors(),
            "measurement_quality": "good",
            "noise_filtered": True,
            "system_health": filter_status.is_system_healthy
        }
    else:
        # 측정 실패 - 백업 방법 사용
        backup_reading = get_most_reliable_recent_reading()
        
        if backup_reading is not None:
            result = {
                "sensors": {
                    "left": backup_reading.left,
                    "center": backup_reading.center,
                    "right": backup_reading.right
                },
                "confidence": backup_reading.confidence * 0.5,  # 백업이므로 신뢰도 감소
                "timestamp": backup_reading.timestamp,
                "sensor_pattern": backup_reading.to_string(),
                "active_sensor_count": backup_reading.count_active_sensors(),
                "measurement_quality": "backup_used",
                "noise_filtered": True,
                "system_health": filter_status.is_system_healthy
            }
        else:
            # 완전 실패 - 안전한 기본값 반환
            result = {
                "sensors": {
                    "left": False,
                    "center": True,  # 중앙 센서만 활성화 (직진)
                    "right": False
                },
                "confidence": 0.1,
                "timestamp": time.time(),
                "sensor_pattern": "_C_",
                "active_sensor_count": 1,
                "measurement_quality": "failed_using_safe_default",
                "noise_filtered": False,
                "system_health": False
            }
    
    return result


# =============================================================================
# 시스템 모니터링 및 디버깅 함수들  
# =============================================================================

def get_line_sensor_filter_status() -> Dict[str, Any]:
    """라인 센서 필터링 시스템의 상태 정보를 반환"""
    return {
        "total_measurements": filter_status.total_measurements,
        "successful_measurements": filter_status.filtered_measurements,
        "noise_detected": filter_status.noise_detected_count,
        "success_rate": (filter_status.filtered_measurements / max(filter_status.total_measurements, 1)) * 100,
        "noise_rate": (filter_status.noise_detected_count / max(filter_status.total_measurements, 1)) * 100,
        "sensor_reliability": filter_status.sensor_reliability_scores.copy(),
        "consecutive_errors": filter_status.consecutive_error_counts.copy(),
        "system_healthy": filter_status.is_system_healthy,
        "history_sizes": {
            "left": len(left_sensor_history),
            "center": len(center_sensor_history),
            "right": len(right_sensor_history),
            "reliable": len(reliable_readings_history)
        }
    }


def print_line_sensor_filter_status() -> None:
    """라인 센서 필터링 상태를 화면에 출력"""
    status = get_line_sensor_filter_status()
    
    print(f"\n=== 라인 센서 필터링 시스템 상태 ===")
    print(f"총 측정: {status['total_measurements']}회")
    print(f"성공 측정: {status['successful_measurements']}회 ({status['success_rate']:.1f}%)")
    print(f"노이즈 감지: {status['noise_detected']}회 ({status['noise_rate']:.1f}%)")
    print(f"시스템 상태: {'정상' if status['system_healthy'] else '불량'}")
    
    print(f"\n센서별 신뢰도:")
    for sensor, score in status["sensor_reliability"].items():
        errors = status["consecutive_errors"][sensor]
        print(f"  {sensor}: {score:.1f}% (연속오류: {errors}회)")
    
    print(f"\n히스토리 크기:")
    for name, size in status["history_sizes"].items():
        print(f"  {name}: {size}개")
    
    print("=" * 40)


def reset_line_sensor_filter_system() -> None:
    """라인 센서 필터링 시스템을 초기화"""
    global filter_status, last_measurement_time
    
    # 히스토리 초기화
    left_sensor_history.clear()
    center_sensor_history.clear()
    right_sensor_history.clear()
    reliable_readings_history.clear()
    
    # 상태 초기화
    filter_status = LineSensorFilterStatus()
    last_measurement_time = 0.0
    
    print("🔄 라인 센서 필터링 시스템 초기화 완료")


def test_line_sensor_filtering_system(left_pin: int, center_pin: int, right_pin: int, duration: int = 30) -> None:
    """라인 센서 필터링 시스템 테스트"""
    print(f"🧪 라인 센서 필터링 시스템 테스트 시작 ({duration}초)")
    
    reset_line_sensor_filter_system()
    start_time = time.time()
    test_count = 0
    
    while time.time() - start_time < duration:
        test_count += 1
        
        # 필터링된 센서 읽기
        result = get_filtered_line_sensor_reading(left_pin, center_pin, right_pin)
        
        print(f"테스트 {test_count:2d}: 패턴={result['sensor_pattern']} | "
              f"신뢰도={result['confidence']:.2f} | 품질={result['measurement_quality']}")
        
        if test_count % 10 == 0:
            print_line_sensor_filter_status()
        
        time.sleep(0.5)
    
    print(f"\n✅ 라인 센서 필터링 테스트 완료 (총 {test_count}회 측정)")
    print_line_sensor_filter_status()


if __name__ == "__main__":
    # 테스트용 실행
    print("🤖 라인 센서 노이즈 필터링 시스템 테스트")
    test_line_sensor_filtering_system(35, 36, 37, 10)
