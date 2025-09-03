#!/usr/bin/env python3
# 파일명: line_sensor.py
# 설명: 라인 트래킹 센서 제어 모듈
# 작성일: 2024
"""
라인 트래킹을 위한 3개 적외선 센서 모듈
- 좌측, 중앙, 우측 센서 상태 읽기
- 라인 감지 상태 분석
- 주행 방향 결정 로직
"""

import RPi.GPIO as GPIO
import time
from enum import Enum
from typing import Tuple, Dict


class LinePosition(Enum):
    """라인 위치 상태 열거형"""
    CENTER = "center"          # 중앙 라인 감지
    LEFT = "left"              # 좌측 라인 감지
    RIGHT = "right"            # 우측 라인 감지
    LOST = "lost"              # 라인 감지 안됨
    MULTIPLE = "multiple"      # 여러 센서 동시 감지


class LineSensor:
    """라인 트래킹 센서 컨트롤러 클래스"""
    
    def __init__(self):
        """라인 센서 초기화"""
        # 센서 핀 설정 (기존 코드 기준)
        self.left_sensor_pin = 38      # 좌측 센서 핀
        self.center_sensor_pin = 36    # 중앙 센서 핀
        self.right_sensor_pin = 35     # 우측 센서 핀
        
        # 초기화 상태 플래그
        self.is_initialized = False
        
        # 센서 상태 히스토리 (노이즈 필터링용)
        self.sensor_history = []
        self.history_size = 3
    
    def initialize_gpio(self) -> bool:
        """GPIO 핀 초기화"""
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BOARD)
            
            # 센서 핀을 입력으로 설정
            GPIO.setup(self.left_sensor_pin, GPIO.IN)
            GPIO.setup(self.center_sensor_pin, GPIO.IN)
            GPIO.setup(self.right_sensor_pin, GPIO.IN)
            
            self.is_initialized = True
            print("라인 센서 초기화 완료")
            return True
            
        except Exception as e:
            print(f"라인 센서 초기화 오류: {e}")
            return False
    
    def _check_initialization(self) -> bool:
        """초기화 상태 확인"""
        if not self.is_initialized:
            print("경고: 라인 센서가 초기화되지 않았습니다.")
            return False
        return True
    
    def read_sensor_raw(self) -> Tuple[int, int, int]:
        """센서 원시 데이터 읽기"""
        if not self._check_initialization():
            return (0, 0, 0)
        
        try:
            left_value = GPIO.input(self.left_sensor_pin)
            center_value = GPIO.input(self.center_sensor_pin)
            right_value = GPIO.input(self.right_sensor_pin)
            
            return (left_value, center_value, right_value)
            
        except Exception as e:
            print(f"센서 읽기 오류: {e}")
            return (0, 0, 0)
    
    def read_sensor_filtered(self) -> Tuple[int, int, int]:
        """노이즈 필터링된 센서 데이터 읽기"""
        # 현재 센서 값 읽기
        current_reading = self.read_sensor_raw()
        
        # 히스토리에 추가
        self.sensor_history.append(current_reading)
        
        # 히스토리 크기 제한
        if len(self.sensor_history) > self.history_size:
            self.sensor_history.pop(0)
        
        # 다수결 방식으로 필터링 (간단한 노이즈 제거)
        if len(self.sensor_history) >= 2:
            # 최근 2개 값의 평균 사용
            recent_values = self.sensor_history[-2:]
            left_avg = sum(reading[0] for reading in recent_values) / len(recent_values)
            center_avg = sum(reading[1] for reading in recent_values) / len(recent_values)
            right_avg = sum(reading[2] for reading in recent_values) / len(recent_values)
            
            # 0.5 기준으로 디지털화
            return (
                1 if left_avg >= 0.5 else 0,
                1 if center_avg >= 0.5 else 0,
                1 if right_avg >= 0.5 else 0
            )
        
        return current_reading
    
    def analyze_line_position(self) -> LinePosition:
        """라인 위치 분석"""
        left, center, right = self.read_sensor_filtered()
        
        # 센서 상태 분석
        sensor_count = left + center + right
        
        if sensor_count == 0:
            return LinePosition.LOST
        elif sensor_count > 1:
            return LinePosition.MULTIPLE
        elif center == 1:
            return LinePosition.CENTER
        elif left == 1:
            return LinePosition.LEFT
        elif right == 1:
            return LinePosition.RIGHT
        else:
            return LinePosition.LOST
    
    def get_driving_direction(self) -> Dict[str, any]:
        """주행 방향 결정"""
        line_position = self.analyze_line_position()
        left, center, right = self.read_sensor_filtered()
        
        # 기본 주행 명령 구조
        command = {
            'action': 'stop',        # forward, backward, turn_left, turn_right, pivot_left, pivot_right, stop
            'speed': 80,             # 속도 (0-100)
            'line_position': line_position.value,
            'sensor_values': (left, center, right),
            'confidence': 1.0,       # 명령 신뢰도 (0.0-1.0)
            'timestamp': time.time(), # 타임스탬프 추가
            'enhanced': False        # 기본 센서임을 표시
        }
        
        # 라인 위치에 따른 주행 명령 결정
        if line_position == LinePosition.CENTER:
            # 중앙 라인 감지 - 직진
            command.update({
                'action': 'forward',
                'speed': 100,
                'confidence': 1.0
            })
            
        elif line_position == LinePosition.LEFT:
            # 좌측 라인 감지 - 우회전으로 보정
            command.update({
                'action': 'pivot_right',
                'speed': 100,
                'confidence': 0.9
            })
            
        elif line_position == LinePosition.RIGHT:
            # 우측 라인 감지 - 좌회전으로 보정
            command.update({
                'action': 'pivot_left',
                'speed': 100,
                'confidence': 0.9
            })
            
        elif line_position == LinePosition.LOST:
            # 라인 감지 안됨 - 후진하여 라인 재탐색
            command.update({
                'action': 'backward',
                'speed': 60,
                'confidence': 0.5
            })
            
        elif line_position == LinePosition.MULTIPLE:
            # 여러 센서 동시 감지 - 교차점이나 넓은 라인
            # 중앙 센서 우선으로 직진
            if center == 1:
                command.update({
                    'action': 'forward',
                    'speed': 80,
                    'confidence': 0.7
                })
            else:
                command.update({
                    'action': 'forward',
                    'speed': 60,
                    'confidence': 0.6
                })
        
        return command
    
    def print_sensor_status(self) -> None:
        """센서 상태 출력 (디버깅용)"""
        left, center, right = self.read_sensor_raw()
        line_position = self.analyze_line_position()
        
        print(f"센서 상태 - 좌:{left} 중:{center} 우:{right} | 라인위치: {line_position.value}")
    
    def calibrate_sensors(self, duration: int = 5) -> Dict[str, any]:
        """센서 캘리브레이션 (선택적 기능)"""
        print(f"센서 캘리브레이션 시작 ({duration}초)")
        
        readings = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            readings.append(self.read_sensor_raw())
            time.sleep(0.1)
        
        # 통계 계산
        if readings:
            avg_left = sum(r[0] for r in readings) / len(readings)
            avg_center = sum(r[1] for r in readings) / len(readings)
            avg_right = sum(r[2] for r in readings) / len(readings)
            
            calibration_data = {
                'sample_count': len(readings),
                'averages': (avg_left, avg_center, avg_right),
                'raw_readings': readings[-10:]  # 마지막 10개 읽기값
            }
            
            print(f"캘리브레이션 완료 - 평균값: 좌:{avg_left:.2f} 중:{avg_center:.2f} 우:{avg_right:.2f}")
            return calibration_data
        
        return {}
    
    def cleanup(self) -> None:
        """리소스 정리"""
        if self.is_initialized:
            self.is_initialized = False
            print("라인 센서 정리 완료")


def main():
    """라인 센서 테스트 함수"""
    sensor = LineSensor()
    
    if not sensor.initialize_gpio():
        print("센서 초기화 실패")
        return
    
    try:
        print("라인 센서 테스트 시작... (Ctrl+C로 종료)")
        print("센서를 라인 위에 위치시키고 테스트하세요.\n")
        
        while True:
            # 센서 상태 출력
            sensor.print_sensor_status()
            
            # 주행 방향 분석
            direction_cmd = sensor.get_driving_direction()
            print(f"주행 명령: {direction_cmd['action']} (속도: {direction_cmd['speed']}, 신뢰도: {direction_cmd['confidence']:.1f})")
            print("-" * 50)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n사용자에 의해 테스트 중단")
    finally:
        sensor.cleanup()


if __name__ == '__main__':
    main()
