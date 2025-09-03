#!/usr/bin/env python3
# 파일명: autonomous_controller.py
# 설명: 자율주행 로봇 메인 컨트롤러 클래스
# 작성일: 2024
"""
라즈베리파이 기반 자율주행 로봇 메인 컨트롤러
- 라인 추적 및 장애물 회피 통합 제어
- 센서 데이터 융합 및 의사결정
- 상태 관리 및 안전 기능
"""

import time
import threading
import signal
import sys
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass

# 모듈 임포트
from ..sensors.line_sensor import LineSensor, LinePosition
from ..sensors.ultrasonic_sensor import UltrasonicSensor, ObstacleLevel
from ..actuators.motor_controller import MotorController
from ..actuators.led_controller import LEDController, RobotState


class AutonomousMode(Enum):
    """자율주행 모드 열거형"""
    STOP = "stop"                      # 정지 모드
    LINE_FOLLOWING = "line_following"  # 라인 추적 모드
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"  # 장애물 회피 모드
    EMERGENCY = "emergency"            # 비상 모드


@dataclass
class RobotCommand:
    """로봇 제어 명령 데이터 클래스"""
    action: str                        # 동작 명령
    speed: int                         # 속도 (0-100)
    priority: str                      # 우선순위 (low, normal, high, emergency)
    source: str                        # 명령 소스 (line_sensor, ultrasonic, manual)
    confidence: float                  # 신뢰도 (0.0-1.0)
    timestamp: float                   # 타임스탬프


class AutonomousController:
    """자율주행 로봇 메인 컨트롤러 클래스"""
    
    def __init__(self):
        """자율주행 컨트롤러 초기화"""
        # 컴포넌트 초기화
        self.line_sensor = LineSensor()
        self.ultrasonic_sensor = UltrasonicSensor()
        self.motor_controller = MotorController()
        self.led_controller = LEDController()
        
        # 제어 파라미터
        self.default_speed = 80            # 기본 주행 속도
        self.obstacle_threshold = 20.0     # 장애물 회피 거리 (cm)
        self.emergency_threshold = 10.0    # 비상 정지 거리 (cm)
        
        # 상태 관리
        self.current_mode = AutonomousMode.STOP
        self.is_running = False
        self.is_emergency = False
        
        # 제어 루프 스레드
        self.control_thread: Optional[threading.Thread] = None
        self.control_loop_interval = 0.1   # 제어 루프 주기 (100ms)
        
        # 성능 모니터링
        self.loop_count = 0
        self.start_time = 0.0
        
        # 신호 핸들러 등록 (Ctrl+C 처리)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def initialize_all_components(self) -> bool:
        """모든 컴포넌트 초기화"""
        print("자율주행 로봇 초기화 시작...")
        
        # 각 컴포넌트 순차 초기화
        components_status = {
            "라인 센서": self.line_sensor.initialize_gpio(),
            "초음파 센서": self.ultrasonic_sensor.initialize_gpio(),
            "모터 컨트롤러": self.motor_controller.initialize_gpio(),
            "LED 컨트롤러": self.led_controller.initialize_led()
        }
        
        # 초기화 결과 출력
        for component, status in components_status.items():
            status_text = "성공" if status else "실패"
            print(f"  {component}: {status_text}")
        
        # 모든 컴포넌트가 성공적으로 초기화되었는지 확인
        all_success = all(components_status.values())
        
        if all_success:
            print("모든 컴포넌트 초기화 완료")
            # LED 시작 시퀀스 실행
            self.led_controller.show_startup_sequence()
            self.led_controller.set_robot_state(RobotState.IDLE)
        else:
            print("일부 컴포넌트 초기화 실패")
        
        return all_success
    
    def _signal_handler(self, signum, frame):
        """신호 핸들러 (Ctrl+C 처리)"""
        print("\n비상 정지 신호 수신")
        self.emergency_stop()
        sys.exit(0)
    
    def start_autonomous_driving(self, mode: AutonomousMode = AutonomousMode.LINE_FOLLOWING) -> bool:
        """자율주행 시작"""
        if self.is_running:
            print("이미 자율주행이 실행 중입니다.")
            return False
        
        self.current_mode = mode
        self.is_running = True
        self.is_emergency = False
        self.start_time = time.time()
        self.loop_count = 0
        
        # 제어 루프 스레드 시작
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        
        print(f"자율주행 시작 - 모드: {mode.value}")
        self.led_controller.set_robot_state(RobotState.MOVING)
        return True
    
    def stop_autonomous_driving(self) -> None:
        """자율주행 정지"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.current_mode = AutonomousMode.STOP
        
        # 스레드 종료 대기
        if self.control_thread:
            self.control_thread.join(timeout=2)
        
        # 모터 정지
        self.motor_controller.stop_all_motors()
        
        print("자율주행 정지")
        self.led_controller.set_robot_state(RobotState.IDLE)
    
    def emergency_stop(self) -> None:
        """비상 정지"""
        self.is_emergency = True
        self.is_running = False
        
        # 즉시 모터 정지
        self.motor_controller.stop_all_motors()
        
        print("비상 정지 실행!")
        self.led_controller.set_robot_state(RobotState.ERROR)
        self.led_controller.start_blink_animation(255, 0, 0, 0.2)
    
    def _control_loop(self) -> None:
        """메인 제어 루프"""
        while self.is_running and not self.is_emergency:
            try:
                # 제어 루프 시작 시간
                loop_start = time.time()
                
                # 센서 데이터 수집
                sensor_data = self._collect_sensor_data()
                
                # 명령 결정 (센서 융합)
                command = self._make_decision(sensor_data)
                
                # 명령 실행
                self._execute_command(command)
                
                # 상태 업데이트
                self._update_status(sensor_data, command)
                
                # 루프 카운터 증가
                self.loop_count += 1
                
                # 주기 조절
                loop_duration = time.time() - loop_start
                sleep_time = max(0, self.control_loop_interval - loop_duration)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"제어 루프 오류: {e}")
                self.emergency_stop()
                break
    
    def _collect_sensor_data(self) -> Dict[str, Any]:
        """센서 데이터 수집"""
        # 라인 센서 데이터
        line_command = self.line_sensor.get_driving_direction()
        
        # 초음파 센서 데이터
        distance = self.ultrasonic_sensor.get_distance_with_history()
        obstacle_level = self.ultrasonic_sensor.analyze_obstacle_level(distance)
        ultrasonic_command = self.ultrasonic_sensor.get_avoidance_command()
        
        return {
            'line_sensor': {
                'command': line_command,
                'position': line_command['line_position'],
                'sensor_values': line_command['sensor_values']
            },
            'ultrasonic_sensor': {
                'distance': distance,
                'obstacle_level': obstacle_level.value,
                'command': ultrasonic_command
            },
            'timestamp': time.time()
        }
    
    def _make_decision(self, sensor_data: Dict[str, Any]) -> RobotCommand:
        """센서 데이터를 기반으로 최종 명령 결정"""
        line_cmd = sensor_data['line_sensor']['command']
        ultrasonic_cmd = sensor_data['ultrasonic_sensor']['command']
        distance = sensor_data['ultrasonic_sensor']['distance']
        
        # 우선순위 규칙:
        # 1. 비상 정지 (거리 < 10cm)
        # 2. 장애물 회피 (거리 < 20cm)
        # 3. 라인 추적
        
        # 비상 정지 체크
        if distance is not None and distance < self.emergency_threshold:
            return RobotCommand(
                action='stop',
                speed=0,
                priority='emergency',
                source='ultrasonic',
                confidence=1.0,
                timestamp=time.time()
            )
        
        # 장애물 회피 우선
        if (distance is not None and 
            distance < self.obstacle_threshold and 
            ultrasonic_cmd['priority'] in ['high', 'emergency']):
            
            return RobotCommand(
                action=ultrasonic_cmd['action'],
                speed=ultrasonic_cmd['speed'],
                priority=ultrasonic_cmd['priority'],
                source='ultrasonic',
                confidence=0.9,
                timestamp=time.time()
            )
        
        # 라인 추적 (기본 모드)
        # 장애물이 안전한 거리에 있으면 라인 추적 우선
        speed_adjustment = 1.0
        
        # 거리에 따른 속도 조절
        if distance is not None:
            if distance < 40:
                speed_adjustment = 0.7  # 속도 30% 감소
            elif distance < 60:
                speed_adjustment = 0.85  # 속도 15% 감소
        
        adjusted_speed = int(line_cmd['speed'] * speed_adjustment)
        
        return RobotCommand(
            action=line_cmd['action'],
            speed=adjusted_speed,
            priority='normal',
            source='line_sensor',
            confidence=line_cmd['confidence'],
            timestamp=time.time()
        )
    
    def _execute_command(self, command: RobotCommand) -> None:
        """명령 실행"""
        if command.action == 'forward':
            self.motor_controller.move_forward(command.speed)
        elif command.action == 'backward':
            self.motor_controller.move_backward(command.speed)
        elif command.action == 'turn_left':
            self.motor_controller.turn_left(command.speed)
        elif command.action == 'turn_right':
            self.motor_controller.turn_right(command.speed)
        elif command.action == 'pivot_left':
            self.motor_controller.pivot_left(command.speed)
        elif command.action == 'pivot_right':
            self.motor_controller.pivot_right(command.speed)
        elif command.action == 'stop':
            self.motor_controller.stop_all_motors()
            if command.priority == 'emergency':
                self.emergency_stop()
    
    def _update_status(self, sensor_data: Dict[str, Any], command: RobotCommand) -> None:
        """상태 업데이트 및 LED 제어"""
        # 로봇 상태 결정
        if self.is_emergency:
            robot_state = RobotState.ERROR
        elif command.action == 'stop':
            robot_state = RobotState.IDLE
        elif command.source == 'ultrasonic' and command.priority in ['high', 'emergency']:
            robot_state = RobotState.OBSTACLE
        elif sensor_data['line_sensor']['position'] == 'lost':
            robot_state = RobotState.LOST
        elif sensor_data['line_sensor']['position'] in ['left', 'right', 'center']:
            robot_state = RobotState.LINE_FOLLOWING
        else:
            robot_state = RobotState.MOVING
        
        # LED 상태 업데이트
        if self.led_controller.current_state != robot_state:
            self.led_controller.set_robot_state(robot_state)
        
        # 장애물 거리에 따른 LED 경고
        distance = sensor_data['ultrasonic_sensor']['distance']
        if distance is not None and robot_state == RobotState.OBSTACLE:
            self.led_controller.show_obstacle_warning(distance)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """성능 통계 반환"""
        if self.start_time == 0:
            return {}
        
        runtime = time.time() - self.start_time
        avg_loop_rate = self.loop_count / runtime if runtime > 0 else 0
        
        return {
            'runtime_seconds': runtime,
            'total_loops': self.loop_count,
            'average_loop_rate_hz': avg_loop_rate,
            'current_mode': self.current_mode.value,
            'is_running': self.is_running,
            'is_emergency': self.is_emergency
        }
    
    def print_status(self) -> None:
        """현재 상태 출력"""
        stats = self.get_performance_stats()
        print(f"\n=== 로봇 상태 ===")
        print(f"모드: {self.current_mode.value}")
        print(f"실행 중: {self.is_running}")
        print(f"비상 상태: {self.is_emergency}")
        if stats:
            print(f"실행 시간: {stats['runtime_seconds']:.1f}초")
            print(f"루프 실행 횟수: {stats['total_loops']}")
            print(f"평균 루프 주파수: {stats['average_loop_rate_hz']:.1f}Hz")
    
    def cleanup(self) -> None:
        """모든 리소스 정리"""
        print("자율주행 컨트롤러 정리 시작...")
        
        # 자율주행 정지
        self.stop_autonomous_driving()
        
        # 각 컴포넌트 정리
        self.motor_controller.cleanup()
        self.line_sensor.cleanup()
        self.ultrasonic_sensor.cleanup()
        self.led_controller.cleanup()
        
        print("자율주행 컨트롤러 정리 완료")


def main():
    """자율주행 컨트롤러 테스트 및 실행"""
    robot = AutonomousController()
    
    try:
        # 초기화
        if not robot.initialize_all_components():
            print("컴포넌트 초기화 실패")
            return
        
        print("\n자율주행 로봇 준비 완료!")
        print("명령어:")
        print("  's' - 자율주행 시작")
        print("  'q' - 종료")
        print("  't' - 상태 출력")
        print("  'e' - 비상 정지")
        
        while True:
            command = input("\n명령 입력: ").strip().lower()
            
            if command == 's':
                robot.start_autonomous_driving()
            elif command == 'q':
                break
            elif command == 't':
                robot.print_status()
            elif command == 'e':
                robot.emergency_stop()
            else:
                print("알 수 없는 명령")
    
    except KeyboardInterrupt:
        print("\n사용자에 의해 중단")
    finally:
        robot.cleanup()


if __name__ == '__main__':
    main()
