#!/usr/bin/env python3
# 파일명: ultrasonic_sensor.py
# 설명: 초음파 센서를 이용한 거리 측정 및 장애물 감지 모듈
# 작성일: 2024
"""
HC-SR04 초음파 센서를 이용한 장애물 감지 모듈
- 거리 측정 기능
- 장애물 감지 및 회피 로직
- 노이즈 필터링 및 안정성 향상
"""

import RPi.GPIO as GPIO
import time
from typing import Optional, List, Dict
from enum import Enum


class ObstacleLevel(Enum):
    """장애물 위험도 레벨"""
    SAFE = "safe"              # 안전 (충분한 거리)
    CAUTION = "caution"        # 주의 (적당한 거리)
    WARNING = "warning"        # 경고 (가까운 거리)
    DANGER = "danger"          # 위험 (매우 가까운 거리)
    ERROR = "error"            # 측정 오류


class UltrasonicSensor:
    """초음파 센서 컨트롤러 클래스"""
    
    def __init__(self):
        """초음파 센서 초기화"""
        # 센서 핀 설정 (HC-SR04 기준)
        self.trigger_pin = 23      # 트리거 핀 (GPIO 23, 물리핀 16)
        self.echo_pin = 24         # 에코 핀 (GPIO 24, 물리핀 18)
        
        # 거리 임계값 설정 (cm)
        self.distance_thresholds = {
            'danger': 10.0,        # 10cm 이하 - 즉시 정지
            'warning': 20.0,       # 20cm 이하 - 회피 동작
            'caution': 40.0,       # 40cm 이하 - 속도 감소
            'safe': 100.0          # 100cm 이상 - 정상 주행
        }
        
        # 측정 설정
        self.max_distance = 300.0  # 최대 측정 거리 (cm)
        self.timeout = 0.03        # 타임아웃 (30ms)
        
        # 필터링을 위한 측정 히스토리
        self.distance_history: List[float] = []
        self.history_size = 5
        
        # 초기화 상태 플래그
        self.is_initialized = False
    
    def initialize_gpio(self) -> bool:
        """GPIO 핀 초기화"""
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BOARD)
            
            # 트리거 핀을 출력으로, 에코 핀을 입력으로 설정
            GPIO.setup(self.trigger_pin, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(self.echo_pin, GPIO.IN)
            
            self.is_initialized = True
            print("초음파 센서 초기화 완료")
            return True
            
        except Exception as e:
            print(f"초음파 센서 초기화 오류: {e}")
            return False
    
    def _check_initialization(self) -> bool:
        """초기화 상태 확인"""
        if not self.is_initialized:
            print("경고: 초음파 센서가 초기화되지 않았습니다.")
            return False
        return True
    
    def measure_distance_raw(self) -> Optional[float]:
        """단일 거리 측정 (원시 데이터)"""
        if not self._check_initialization():
            return None
        
        try:
            # 트리거 신호 생성 (10μs 펄스)
            GPIO.output(self.trigger_pin, GPIO.HIGH)
            time.sleep(0.00001)  # 10μs
            GPIO.output(self.trigger_pin, GPIO.LOW)
            
            # 에코 신호 시작 시점 측정
            pulse_start = time.time()
            timeout_start = pulse_start
            
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if pulse_start - timeout_start > self.timeout:
                    return None  # 타임아웃
            
            # 에코 신호 종료 시점 측정
            pulse_end = time.time()
            timeout_start = pulse_end
            
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if pulse_end - pulse_start > self.timeout:
                    return None  # 타임아웃
            
            # 거리 계산 (음속 340m/s, 왕복 거리를 반으로 나눔)
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34000) / 2  # cm 단위
            
            # 유효 범위 검증
            if 2.0 <= distance <= self.max_distance:
                return distance
            else:
                return None
                
        except Exception as e:
            print(f"거리 측정 오류: {e}")
            return None
    
    def measure_distance_filtered(self, samples: int = 3) -> Optional[float]:
        """필터링된 거리 측정 (여러 샘플의 평균)"""
        distances = []
        
        for _ in range(samples):
            distance = self.measure_distance_raw()
            if distance is not None:
                distances.append(distance)
            time.sleep(0.01)  # 샘플 간 간격
        
        if not distances:
            return None
        
        # 이상값 제거 (중간값 사용)
        distances.sort()
        if len(distances) >= 3:
            # 중간값 선택 (노이즈 제거)
            return distances[len(distances) // 2]
        else:
            # 평균값 사용
            return sum(distances) / len(distances)
    
    def get_distance_with_history(self) -> Optional[float]:
        """히스토리를 이용한 안정화된 거리 측정"""
        current_distance = self.measure_distance_filtered()
        
        if current_distance is not None:
            # 히스토리에 추가
            self.distance_history.append(current_distance)
            
            # 히스토리 크기 제한
            if len(self.distance_history) > self.history_size:
                self.distance_history.pop(0)
            
            # 이동 평균 계산
            if len(self.distance_history) >= 2:
                return sum(self.distance_history) / len(self.distance_history)
        
        return current_distance
    
    def analyze_obstacle_level(self, distance: Optional[float] = None) -> ObstacleLevel:
        """장애물 위험도 분석"""
        if distance is None:
            distance = self.get_distance_with_history()
        
        if distance is None:
            return ObstacleLevel.ERROR
        
        # 거리별 위험도 판정
        if distance <= self.distance_thresholds['danger']:
            return ObstacleLevel.DANGER
        elif distance <= self.distance_thresholds['warning']:
            return ObstacleLevel.WARNING
        elif distance <= self.distance_thresholds['caution']:
            return ObstacleLevel.CAUTION
        else:
            return ObstacleLevel.SAFE
    
    def get_avoidance_command(self) -> Dict[str, any]:
        """장애물 회피 명령 생성"""
        distance = self.get_distance_with_history()
        obstacle_level = self.analyze_obstacle_level(distance)
        
        # 기본 명령 구조
        command = {
            'action': 'forward',         # forward, backward, turn_left, turn_right, stop
            'speed': 80,                 # 속도 (0-100)
            'distance': distance,        # 측정된 거리
            'obstacle_level': obstacle_level.value,
            'priority': 'normal'         # low, normal, high, emergency
        }
        
        # 장애물 레벨에 따른 회피 명령 결정
        if obstacle_level == ObstacleLevel.DANGER:
            # 위험 - 즉시 정지 및 후진
            command.update({
                'action': 'stop',
                'speed': 0,
                'priority': 'emergency'
            })
            
        elif obstacle_level == ObstacleLevel.WARNING:
            # 경고 - 회피 동작 (우회전 선호)
            command.update({
                'action': 'turn_right',
                'speed': 60,
                'priority': 'high'
            })
            
        elif obstacle_level == ObstacleLevel.CAUTION:
            # 주의 - 속도 감소
            command.update({
                'action': 'forward',
                'speed': 50,
                'priority': 'normal'
            })
            
        elif obstacle_level == ObstacleLevel.SAFE:
            # 안전 - 정상 주행
            command.update({
                'action': 'forward',
                'speed': 80,
                'priority': 'low'
            })
            
        else:  # ERROR
            # 측정 오류 - 안전을 위해 정지
            command.update({
                'action': 'stop',
                'speed': 0,
                'priority': 'high'
            })
        
        return command
    
    def monitor_continuous(self, duration: int = 10) -> List[float]:
        """연속 모니터링 (테스트용)"""
        print(f"초음파 센서 연속 모니터링 시작 ({duration}초)")
        
        measurements = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            distance = self.get_distance_with_history()
            if distance is not None:
                measurements.append(distance)
                obstacle_level = self.analyze_obstacle_level(distance)
                print(f"거리: {distance:.1f}cm | 상태: {obstacle_level.value}")
            else:
                print("측정 실패")
            
            time.sleep(0.2)
        
        return measurements
    
    def cleanup(self) -> None:
        """리소스 정리"""
        if self.is_initialized:
            self.is_initialized = False
            print("초음파 센서 정리 완료")


def main():
    """초음파 센서 테스트 함수"""
    sensor = UltrasonicSensor()
    
    if not sensor.initialize_gpio():
        print("센서 초기화 실패")
        return
    
    try:
        print("초음파 센서 테스트 시작... (Ctrl+C로 종료)")
        print("센서 앞에 물체를 놓고 테스트하세요.\n")
        
        while True:
            # 거리 측정
            distance = sensor.get_distance_with_history()
            
            if distance is not None:
                # 장애물 레벨 분석
                obstacle_level = sensor.analyze_obstacle_level(distance)
                
                # 회피 명령 생성
                avoidance_cmd = sensor.get_avoidance_command()
                
                print(f"거리: {distance:.1f}cm | 상태: {obstacle_level.value}")
                print(f"회피 명령: {avoidance_cmd['action']} (속도: {avoidance_cmd['speed']}, 우선순위: {avoidance_cmd['priority']})")
                print("-" * 60)
            else:
                print("거리 측정 실패")
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n사용자에 의해 테스트 중단")
    finally:
        sensor.cleanup()


if __name__ == '__main__':
    main()
