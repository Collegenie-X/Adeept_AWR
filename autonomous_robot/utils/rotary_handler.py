#!/usr/bin/env python3
# 파일명: rotary_handler.py
# 설명: 로타리 구간 전용 라인 추적 핸들러
# 작성일: 2024
"""
로타리(원형 교차로) 구간에서의 라인 추적 개선 모듈
- 빈도 기반 방향 결정 시스템
- 히스토리 기반 노이즈 필터링
- 로타리 진입/탈출 감지
- 적응형 속도 제어
"""

import time
from typing import List, Dict, Optional, Tuple
from enum import Enum
from collections import deque, Counter
from dataclasses import dataclass

from ..sensors.line_sensor import LinePosition


class RotaryState(Enum):
    """로타리 상태 열거형"""
    NORMAL = "normal"              # 일반 직선 구간
    ENTERING_ROTARY = "entering"   # 로타리 진입 중
    IN_ROTARY = "in_rotary"        # 로타리 내부
    EXITING_ROTARY = "exiting"     # 로타리 탈출 중


@dataclass
class RotaryDecision:
    """로타리 구간 주행 결정 데이터"""
    action: str                    # 주행 동작
    speed: int                     # 속도
    confidence: float              # 신뢰도
    rotary_state: RotaryState      # 로타리 상태
    frequency_score: Dict[str, int]  # 방향별 빈도 점수
    reasoning: str                 # 결정 근거


class RotaryFrequencyAnalyzer:
    """로타리 구간 빈도 분석기"""
    
    def __init__(self, window_size: int = 10, threshold_ratio: float = 0.6):
        """
        빈도 분석기 초기화
        
        Args:
            window_size: 분석할 히스토리 윈도우 크기
            threshold_ratio: 방향 결정을 위한 임계 비율
        """
        self.window_size = window_size
        self.threshold_ratio = threshold_ratio
        
        # 방향별 히스토리 저장
        self.direction_history: deque = deque(maxlen=window_size)
        self.position_history: deque = deque(maxlen=window_size)
        
        # 빈도 계산용
        self.direction_counter = Counter()
        self.position_counter = Counter()
        
        # 연속 감지 카운터
        self.consecutive_left = 0
        self.consecutive_right = 0
        self.consecutive_center = 0
        self.consecutive_lost = 0
        
        # 로타리 상태 관리
        self.current_rotary_state = RotaryState.NORMAL
        self.rotary_entry_time = 0.0
        self.in_rotary_duration = 0.0
    
    def add_observation(self, line_position: LinePosition, sensor_values: Tuple[int, int, int]) -> None:
        """새로운 관찰값 추가"""
        current_time = time.time()
        
        # 히스토리에 추가
        self.direction_history.append((line_position, current_time))
        self.position_history.append(sensor_values)
        
        # 연속 감지 카운터 업데이트
        self._update_consecutive_counters(line_position)
        
        # 로타리 상태 업데이트
        self._update_rotary_state(line_position, current_time)
        
        # 빈도 카운터 업데이트
        self._update_frequency_counters()
    
    def _update_consecutive_counters(self, position: LinePosition) -> None:
        """연속 감지 카운터 업데이트"""
        # 모든 카운터 리셋
        if position != LinePosition.LEFT:
            self.consecutive_left = 0
        else:
            self.consecutive_left += 1
            
        if position != LinePosition.RIGHT:
            self.consecutive_right = 0
        else:
            self.consecutive_right += 1
            
        if position != LinePosition.CENTER:
            self.consecutive_center = 0
        else:
            self.consecutive_center += 1
            
        if position != LinePosition.LOST:
            self.consecutive_lost = 0
        else:
            self.consecutive_lost += 1
    
    def _update_rotary_state(self, position: LinePosition, current_time: float) -> None:
        """로타리 상태 업데이트"""
        # 로타리 진입 감지: 좌우 센서가 자주 번갈아 감지됨
        if self._detect_rotary_entry():
            if self.current_rotary_state == RotaryState.NORMAL:
                self.current_rotary_state = RotaryState.ENTERING_ROTARY
                self.rotary_entry_time = current_time
                print("🔄 로타리 진입 감지")
        
        # 로타리 내부 상태로 전환
        elif (self.current_rotary_state == RotaryState.ENTERING_ROTARY and 
              current_time - self.rotary_entry_time > 1.0):
            self.current_rotary_state = RotaryState.IN_ROTARY
            print("🌀 로타리 내부 진입")
        
        # 로타리 탈출 감지: 중앙 센서가 안정적으로 감지됨
        elif (self.current_rotary_state == RotaryState.IN_ROTARY and 
              self.consecutive_center >= 5):
            self.current_rotary_state = RotaryState.EXITING_ROTARY
            print("🚪 로타리 탈출 시작")
        
        # 일반 상태로 복귀
        elif (self.current_rotary_state == RotaryState.EXITING_ROTARY and 
              self.consecutive_center >= 10):
            self.current_rotary_state = RotaryState.NORMAL
            self.in_rotary_duration = current_time - self.rotary_entry_time
            print(f"✅ 로타리 탈출 완료 (소요시간: {self.in_rotary_duration:.1f}초)")
    
    def _detect_rotary_entry(self) -> bool:
        """로타리 진입 감지"""
        if len(self.direction_history) < 6:
            return False
        
        # 최근 6개 관찰에서 좌우 번갈아 나타나는 패턴 감지
        recent_positions = [pos for pos, _ in list(self.direction_history)[-6:]]
        
        left_count = recent_positions.count(LinePosition.LEFT)
        right_count = recent_positions.count(LinePosition.RIGHT)
        
        # 좌우가 모두 나타나고, 둘 중 하나가 과도하게 많지 않을 때
        return (left_count >= 2 and right_count >= 2 and 
                abs(left_count - right_count) <= 2)
    
    def _update_frequency_counters(self) -> None:
        """빈도 카운터 업데이트"""
        # 방향별 빈도 계산
        self.direction_counter.clear()
        for position, _ in self.direction_history:
            self.direction_counter[position.value] += 1
        
        # 센서값별 빈도 계산  
        self.position_counter.clear()
        for left, center, right in self.position_history:
            if left == 1:
                self.position_counter['left'] += 1
            if center == 1:
                self.position_counter['center'] += 1
            if right == 1:
                self.position_counter['right'] += 1
    
    def get_frequency_decision(self) -> RotaryDecision:
        """빈도 기반 주행 결정"""
        if len(self.direction_history) < 3:
            return RotaryDecision(
                action='forward',
                speed=60,
                confidence=0.3,
                rotary_state=self.current_rotary_state,
                frequency_score={},
                reasoning="데이터 부족"
            )
        
        # 로타리 상태별 처리
        if self.current_rotary_state == RotaryState.NORMAL:
            return self._normal_decision()
        elif self.current_rotary_state == RotaryState.ENTERING_ROTARY:
            return self._entering_rotary_decision()
        elif self.current_rotary_state == RotaryState.IN_ROTARY:
            return self._in_rotary_decision()
        else:  # EXITING_ROTARY
            return self._exiting_rotary_decision()
    
    def _normal_decision(self) -> RotaryDecision:
        """일반 구간 결정"""
        # 최근 관찰값 기반 결정
        recent_position = self.direction_history[-1][0]
        
        if recent_position == LinePosition.CENTER:
            return RotaryDecision(
                action='forward',
                speed=100,
                confidence=0.9,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning="중앙선 감지 - 직진"
            )
        elif recent_position == LinePosition.LEFT:
            return RotaryDecision(
                action='pivot_right',
                speed=80,
                confidence=0.8,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning="좌측선 감지 - 우회전"
            )
        elif recent_position == LinePosition.RIGHT:
            return RotaryDecision(
                action='pivot_left',
                speed=80,
                confidence=0.8,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning="우측선 감지 - 좌회전"
            )
        else:
            return RotaryDecision(
                action='backward',
                speed=50,
                confidence=0.5,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning="라인 분실 - 후진"
            )
    
    def _entering_rotary_decision(self) -> RotaryDecision:
        """로타리 진입 시 결정"""
        # 진입 시에는 속도를 줄이고 안정적인 방향으로
        left_freq = self.direction_counter.get('left', 0)
        right_freq = self.direction_counter.get('right', 0)
        center_freq = self.direction_counter.get('center', 0)
        
        total_freq = left_freq + right_freq + center_freq
        
        if total_freq == 0:
            return RotaryDecision(
                action='forward',
                speed=40,
                confidence=0.3,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning="로타리 진입 - 저속 직진"
            )
        
        # 빈도가 높은 방향 선택 (단, 더 보수적으로)
        if center_freq >= total_freq * 0.4:
            return RotaryDecision(
                action='forward',
                speed=60,
                confidence=0.7,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning=f"로타리 진입 - 중앙선 빈도 높음 ({center_freq}/{total_freq})"
            )
        elif left_freq > right_freq * 1.5:
            return RotaryDecision(
                action='turn_right',
                speed=50,
                confidence=0.6,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning=f"로타리 진입 - 좌측선 빈도 높음 ({left_freq}/{total_freq})"
            )
        elif right_freq > left_freq * 1.5:
            return RotaryDecision(
                action='turn_left',
                speed=50,
                confidence=0.6,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning=f"로타리 진입 - 우측선 빈도 높음 ({right_freq}/{total_freq})"
            )
        else:
            # 빈도가 비슷하면 직진
            return RotaryDecision(
                action='forward',
                speed=45,
                confidence=0.5,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning="로타리 진입 - 방향 빈도 비슷, 직진"
            )
    
    def _in_rotary_decision(self) -> RotaryDecision:
        """로타리 내부에서의 결정 (핵심 로직)"""
        left_freq = self.direction_counter.get('left', 0)
        right_freq = self.direction_counter.get('right', 0)
        center_freq = self.direction_counter.get('center', 0)
        
        total_freq = left_freq + right_freq + center_freq
        
        if total_freq == 0:
            return RotaryDecision(
                action='forward',
                speed=30,
                confidence=0.2,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning="로타리 내부 - 센서 데이터 없음"
            )
        
        # 빈도 비율 계산
        left_ratio = left_freq / total_freq
        right_ratio = right_freq / total_freq
        center_ratio = center_freq / total_freq
        
        # 연속 감지 가중치 적용
        stability_bonus = 0.1
        if self.consecutive_left >= 3:
            left_ratio += stability_bonus
        if self.consecutive_right >= 3:
            right_ratio += stability_bonus
        if self.consecutive_center >= 3:
            center_ratio += stability_bonus
        
        # 결정 로직 (임계값 기반)
        if center_ratio >= self.threshold_ratio:
            return RotaryDecision(
                action='forward',
                speed=70,
                confidence=0.8,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning=f"로타리 내부 - 중앙선 강세 ({center_ratio:.2f})"
            )
        elif left_ratio >= self.threshold_ratio and left_ratio > right_ratio * 2:
            return RotaryDecision(
                action='turn_right',
                speed=55,
                confidence=0.7,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning=f"로타리 내부 - 좌측선 강세 ({left_ratio:.2f})"
            )
        elif right_ratio >= self.threshold_ratio and right_ratio > left_ratio * 2:
            return RotaryDecision(
                action='turn_left',
                speed=55,
                confidence=0.7,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning=f"로타리 내부 - 우측선 강세 ({right_ratio:.2f})"
            )
        else:
            # 빈도가 비슷할 때는 최근 트렌드 고려
            recent_trend = self._analyze_recent_trend()
            return RotaryDecision(
                action=recent_trend['action'],
                speed=45,
                confidence=0.5,
                rotary_state=self.current_rotary_state,
                frequency_score=dict(self.direction_counter),
                reasoning=f"로타리 내부 - 최근 트렌드 기반: {recent_trend['reasoning']}"
            )
    
    def _exiting_rotary_decision(self) -> RotaryDecision:
        """로타리 탈출 시 결정"""
        # 탈출 시에는 중앙선을 따라 직진
        return RotaryDecision(
            action='forward',
            speed=80,
            confidence=0.9,
            rotary_state=self.current_rotary_state,
            frequency_score=dict(self.direction_counter),
            reasoning="로타리 탈출 - 중앙선 추적"
        )
    
    def _analyze_recent_trend(self) -> Dict[str, str]:
        """최근 트렌드 분석"""
        if len(self.direction_history) < 5:
            return {'action': 'forward', 'reasoning': '데이터 부족'}
        
        # 최근 5개 관찰의 트렌드 분석
        recent_positions = [pos for pos, _ in list(self.direction_history)[-5:]]
        
        # 마지막 유효한 방향 찾기
        for pos in reversed(recent_positions):
            if pos == LinePosition.LEFT:
                return {'action': 'turn_right', 'reasoning': '최근 좌측선 감지'}
            elif pos == LinePosition.RIGHT:
                return {'action': 'turn_left', 'reasoning': '최근 우측선 감지'}
            elif pos == LinePosition.CENTER:
                return {'action': 'forward', 'reasoning': '최근 중앙선 감지'}
        
        return {'action': 'forward', 'reasoning': '트렌드 불명확'}
    
    def get_debug_info(self) -> Dict[str, any]:
        """디버깅 정보 반환"""
        return {
            'rotary_state': self.current_rotary_state.value,
            'direction_frequencies': dict(self.direction_counter),
            'consecutive_counts': {
                'left': self.consecutive_left,
                'right': self.consecutive_right,
                'center': self.consecutive_center,
                'lost': self.consecutive_lost
            },
            'history_length': len(self.direction_history),
            'window_size': self.window_size,
            'threshold_ratio': self.threshold_ratio,
            'in_rotary_duration': self.in_rotary_duration
        }


class EnhancedRotaryLineSensor:
    """로타리 구간 개선된 라인 센서"""
    
    def __init__(self, base_line_sensor, analyzer_window_size: int = 15):
        """
        개선된 라인 센서 초기화
        
        Args:
            base_line_sensor: 기본 라인 센서 객체
            analyzer_window_size: 빈도 분석 윈도우 크기
        """
        self.base_sensor = base_line_sensor
        self.frequency_analyzer = RotaryFrequencyAnalyzer(window_size=analyzer_window_size)
        
        # 성능 모니터링
        self.total_decisions = 0
        self.rotary_decisions = 0
        self.start_time = time.time()
    
    def get_enhanced_driving_direction(self) -> Dict[str, any]:
        """개선된 주행 방향 결정"""
        # 기본 센서 데이터 수집
        basic_command = self.base_sensor.get_driving_direction()
        line_position = LinePosition(basic_command['line_position'])
        sensor_values = basic_command['sensor_values']
        
        # 빈도 분석기에 관찰값 추가
        self.frequency_analyzer.add_observation(line_position, sensor_values)
        
        # 빈도 기반 결정 수행
        rotary_decision = self.frequency_analyzer.get_frequency_decision()
        
        # 통계 업데이트
        self.total_decisions += 1
        if rotary_decision.rotary_state != RotaryState.NORMAL:
            self.rotary_decisions += 1
        
        # 최종 명령 구성
        enhanced_command = {
            'action': rotary_decision.action,
            'speed': rotary_decision.speed,
            'line_position': rotary_decision.rotary_state.value,
            'sensor_values': sensor_values,
            'confidence': rotary_decision.confidence,
            'rotary_info': {
                'state': rotary_decision.rotary_state.value,
                'frequency_score': rotary_decision.frequency_score,
                'reasoning': rotary_decision.reasoning,
                'basic_action': basic_command['action']  # 기본 센서 결과 비교용
            },
            'enhanced': True  # 개선된 센서임을 표시
        }
        
        return enhanced_command
    
    def print_status(self) -> None:
        """현재 상태 출력"""
        debug_info = self.frequency_analyzer.get_debug_info()
        runtime = time.time() - self.start_time
        
        print(f"\n=== 로타리 라인 센서 상태 ===")
        print(f"로타리 상태: {debug_info['rotary_state']}")
        print(f"방향 빈도: {debug_info['direction_frequencies']}")
        print(f"연속 감지: {debug_info['consecutive_counts']}")
        print(f"총 결정: {self.total_decisions} (로타리: {self.rotary_decisions})")
        print(f"실행 시간: {runtime:.1f}초")
        print("=" * 30)


def main():
    """테스트 함수"""
    print("로타리 핸들러 테스트 시작...")
    
    # 기본 라인 센서 임포트 (테스트용)
    try:
        from ..sensors.line_sensor import LineSensor
        
        line_sensor = LineSensor()
        if not line_sensor.initialize_gpio():
            print("라인 센서 초기화 실패")
            return
        
        # 개선된 센서 생성
        enhanced_sensor = EnhancedRotaryLineSensor(line_sensor)
        
        print("로타리 라인 센서 테스트 시작 (Ctrl+C로 종료)")
        
        while True:
            command = enhanced_sensor.get_enhanced_driving_direction()
            
            print(f"동작: {command['action']} | 속도: {command['speed']} | "
                  f"상태: {command['rotary_info']['state']} | "
                  f"신뢰도: {command['confidence']:.2f}")
            print(f"근거: {command['rotary_info']['reasoning']}")
            
            time.sleep(0.2)
            
    except ImportError:
        print("라인 센서 모듈을 찾을 수 없습니다.")
    except KeyboardInterrupt:
        print("\n테스트 종료")


if __name__ == '__main__':
    main()
