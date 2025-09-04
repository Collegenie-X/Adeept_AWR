#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Adeept AWR 자율주행 로봇 메인 제어 프로그램
- 라즈베리파이 기반 4륜 자율주행 로봇
- 라인 추적, 장애물 회피, LED 상태 표시 통합 제어
- 모듈형 설계로 각 구성요소 독립 제어 가능

하드웨어 구성:
- 기어 모터 4개 (L298N 드라이버)
- 라인 센서 3개 (적외선)
- 초음파 센서 1개 (HC-SR04)
- LED 스트립 16개 (WS2812)
- 부저 1개

작성일: 2024
"""

import time
import signal
import sys
import threading
from typing import Optional, Dict, Any
from enum import Enum

# 하드웨어 제어 모듈 임포트
try:
    from hardware.test_gear_motors import GearMotorController
    from hardware.test_line_sensors import LineSensorController
    from hardware.test_ultrasonic_sensor import UltrasonicSensor
    from hardware.test_led_strip import LEDStripController, RobotState
    from hardware.test_servo_motors import ServoMotorController

    HARDWARE_AVAILABLE = True
except ImportError as e:
    print(f"하드웨어 모듈 임포트 오류: {e}")
    print("시뮬레이션 모드로 실행됩니다.")
    HARDWARE_AVAILABLE = False


class RobotMode(Enum):
    """로봇 동작 모드"""

    IDLE = "idle"  # 대기 상태
    MANUAL = "manual"  # 수동 제어
    LINE_FOLLOWING = "line_following"  # 라인 추적
    OBSTACLE_AVOIDANCE = "obstacle_avoidance"  # 장애물 회피
    AUTO_NAVIGATION = "auto_navigation"  # 자율 주행
    EMERGENCY_STOP = "emergency_stop"  # 비상 정지


class AutonomousRobot:
    """자율주행 로봇 메인 제어 클래스"""

    def __init__(self):
        # 핀아웃 설정 (pinout.md 기준)
        self.pinout_config = {
            # 모터 제어 (L298N)
            "motor_a_enable": 4,  # 우측 모터 PWM
            "motor_a_pin1": 14,  # 우측 모터 방향 1
            "motor_a_pin2": 15,  # 우측 모터 방향 2
            "motor_b_enable": 17,  # 좌측 모터 PWM
            "motor_b_pin1": 27,  # 좌측 모터 방향 1
            "motor_b_pin2": 18,  # 좌측 모터 방향 2
            # 센서
            "ultrasonic_trig": 11,  # 초음파 트리거
            "ultrasonic_echo": 8,  # 초음파 에코
            "line_left": 20,  # 라인센서 좌측
            "line_middle": 16,  # 라인센서 중앙
            "line_right": 19,  # 라인센서 우측
            # 출력 장치
            "led_strip": 12,  # WS2812 LED 스트립
            "buzzer": 20,  # 부저 (라인센서 좌측과 공유)
        }

        # 제어 상태
        self.current_mode = RobotMode.IDLE
        self.is_running = False
        self.emergency_stop = False

        # 하드웨어 컨트롤러 초기화
        self.initialize_hardware()

        # 제어 스레드
        self.control_thread: Optional[threading.Thread] = None

        # 신호 처리기 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def initialize_hardware(self):
        """하드웨어 컨트롤러 초기화"""
        print("하드웨어 초기화 중...")

        if HARDWARE_AVAILABLE:
            try:
                # 모터 컨트롤러
                self.motor_controller = GearMotorController()
                print("✓ 기어 모터 컨트롤러 초기화 완료")

                # 센서 컨트롤러
                self.line_sensor = LineSensorController()
                self.ultrasonic_sensor = UltrasonicSensor()
                print("✓ 센서 컨트롤러 초기화 완료")

                # LED 컨트롤러
                self.led_controller = LEDStripController()
                print("✓ LED 컨트롤러 초기화 완료")

                # 서보모터 컨트롤러 (선택적)
                try:
                    self.servo_controller = ServoMotorController()
                    print("✓ 서보모터 컨트롤러 초기화 완료")
                except Exception as servo_error:
                    print(f"서보모터 초기화 실패: {servo_error}")
                    self.servo_controller = None

                # 초기 상태 설정
                self.led_controller.set_state_color(RobotState.IDLE)

            except Exception as e:
                print(f"하드웨어 초기화 오류: {e}")
                print("시뮬레이션 모드로 전환합니다.")
                self._initialize_simulation()
        else:
            self._initialize_simulation()

    def _initialize_simulation(self):
        """시뮬레이션 모드 초기화"""
        self.motor_controller = None
        self.line_sensor = None
        self.ultrasonic_sensor = None
        self.led_controller = None
        self.servo_controller = None
        print("시뮬레이션 모드로 실행 중...")

    def signal_handler(self, signum, frame):
        """시그널 처리기 (Ctrl+C 등)"""
        print("\n\n프로그램 종료 신호를 받았습니다.")
        self.emergency_stop = True
        self.stop_robot()
        sys.exit(0)

    def start_robot(self):
        """로봇 시작"""
        if self.is_running:
            print("로봇이 이미 실행 중입니다.")
            return

        self.is_running = True
        self.emergency_stop = False

        if self.led_controller:
            self.led_controller.set_state_color(RobotState.MOVING)

        # 제어 스레드 시작
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()

        print("로봇이 시작되었습니다.")

    def stop_robot(self):
        """로봇 정지"""
        print("로봇을 정지합니다...")
        self.is_running = False

        # 모터 정지
        if self.motor_controller:
            self.motor_controller.motor_stop()

        # LED 상태 변경
        if self.led_controller:
            if self.emergency_stop:
                self.led_controller.set_state_color(RobotState.ERROR)
            else:
                self.led_controller.set_state_color(RobotState.SHUTDOWN)

        # 제어 스레드 대기
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=2.0)

        print("로봇이 정지되었습니다.")

    def set_mode(self, mode: RobotMode):
        """로봇 동작 모드 변경"""
        if mode == self.current_mode:
            return

        print(f"모드 변경: {self.current_mode.value} → {mode.value}")
        self.current_mode = mode

        # LED 상태 변경
        if self.led_controller:
            if mode == RobotMode.IDLE:
                self.led_controller.set_state_color(RobotState.IDLE)
            elif mode == RobotMode.LINE_FOLLOWING:
                self.led_controller.set_state_color(RobotState.LINE_FOLLOWING)
            elif mode == RobotMode.OBSTACLE_AVOIDANCE:
                self.led_controller.set_state_color(RobotState.OBSTACLE)
            elif mode == RobotMode.EMERGENCY_STOP:
                self.led_controller.set_state_color(RobotState.ERROR)
            else:
                self.led_controller.set_state_color(RobotState.MOVING)

    def _control_loop(self):
        """메인 제어 루프"""
        while self.is_running and not self.emergency_stop:
            try:
                if self.current_mode == RobotMode.IDLE:
                    self._idle_mode()
                elif self.current_mode == RobotMode.LINE_FOLLOWING:
                    self._line_following_mode()
                elif self.current_mode == RobotMode.OBSTACLE_AVOIDANCE:
                    self._obstacle_avoidance_mode()
                elif self.current_mode == RobotMode.AUTO_NAVIGATION:
                    self._auto_navigation_mode()
                elif self.current_mode == RobotMode.EMERGENCY_STOP:
                    self._emergency_stop_mode()
                    break

                time.sleep(0.05)  # 20Hz 제어 주기

            except Exception as e:
                print(f"제어 루프 오류: {e}")
                self.emergency_stop = True
                break

        # 안전 정지
        if self.motor_controller:
            self.motor_controller.motor_stop()

    def _idle_mode(self):
        """대기 모드"""
        if self.motor_controller:
            self.motor_controller.motor_stop()

    def _line_following_mode(self):
        """라인 추적 모드"""
        if not self.line_sensor or not self.motor_controller:
            print("라인 추적에 필요한 하드웨어가 없습니다.")
            return

        # 라인 센서 읽기
        line_info = self.line_sensor.get_line_position()
        position = line_info["position"]

        # 기본 속도 설정
        base_speed = 40

        if position is None:
            # 라인 없음 - 탐색 모드
            if self.led_controller:
                self.led_controller.set_state_color(RobotState.LOST)
            self._search_line()
        else:
            # 라인 추적 제어
            if self.led_controller:
                self.led_controller.set_state_color(RobotState.LINE_FOLLOWING)

            if position == 0:  # 중앙
                # 직진
                self.motor_controller.set_motor_speed("A", base_speed)
                self.motor_controller.set_motor_speed("B", base_speed)
            elif position < 0:  # 좌측으로 치우침 - 우회전 필요
                turn_speed = int(abs(position) * 30)
                self.motor_controller.set_motor_speed("A", base_speed + turn_speed)
                self.motor_controller.set_motor_speed("B", base_speed - turn_speed)
            else:  # 우측으로 치우침 - 좌회전 필요
                turn_speed = int(position * 30)
                self.motor_controller.set_motor_speed("A", base_speed - turn_speed)
                self.motor_controller.set_motor_speed("B", base_speed + turn_speed)

    def _search_line(self):
        """라인 탐색 (라인을 잃었을 때)"""
        # 제자리에서 좌회전하며 라인 탐색
        if self.motor_controller:
            self.motor_controller.set_motor_speed("A", -30)
            self.motor_controller.set_motor_speed("B", 30)

    def _obstacle_avoidance_mode(self):
        """장애물 회피 모드"""
        if not self.ultrasonic_sensor or not self.motor_controller:
            print("장애물 회피에 필요한 하드웨어가 없습니다.")
            return

        # 거리 측정
        distance = self.ultrasonic_sensor.measure_distance()

        if distance is None:
            distance = 999  # 측정 실패 시 안전한 거리로 간주

        if distance < 10:  # 10cm 이내 - 비상 정지
            if self.led_controller:
                self.led_controller.set_state_color(RobotState.ERROR)
            self.motor_controller.motor_stop()
        elif distance < 20:  # 20cm 이내 - 후진 및 회전
            if self.led_controller:
                self.led_controller.set_state_color(RobotState.OBSTACLE)
            self.motor_controller.set_motor_speed("A", -40)
            self.motor_controller.set_motor_speed("B", 40)  # 우회전하며 후진
        elif distance < 40:  # 40cm 이내 - 감속
            if self.led_controller:
                self.led_controller.set_state_color(RobotState.OBSTACLE)
            self.motor_controller.set_motor_speed("A", 20)
            self.motor_controller.set_motor_speed("B", 20)
        else:  # 안전 거리 - 정상 주행
            if self.led_controller:
                self.led_controller.set_state_color(RobotState.MOVING)
            self.motor_controller.set_motor_speed("A", 50)
            self.motor_controller.set_motor_speed("B", 50)

    def _auto_navigation_mode(self):
        """자율 주행 모드 (라인 추적 + 장애물 회피)"""
        if not all([self.line_sensor, self.ultrasonic_sensor, self.motor_controller]):
            print("자율 주행에 필요한 하드웨어가 없습니다.")
            return

        # 장애물 우선 확인
        distance = self.ultrasonic_sensor.measure_distance()
        if distance and distance < 30:
            # 장애물이 가까우면 회피 모드로 전환
            self._obstacle_avoidance_mode()
        else:
            # 라인 추적 실행
            self._line_following_mode()

    def _emergency_stop_mode(self):
        """비상 정지 모드"""
        if self.motor_controller:
            self.motor_controller.motor_stop()
        if self.led_controller:
            self.led_controller.set_state_color(RobotState.ERROR)
        self.is_running = False

    def move_forward(self, speed: int = 50):
        """전진"""
        if self.motor_controller:
            self.motor_controller.set_motor_speed("A", speed)
            self.motor_controller.set_motor_speed("B", speed)
        else:
            print(f"시뮬레이션: 전진 (속도: {speed})")

    def move_backward(self, speed: int = 50):
        """후진"""
        if self.motor_controller:
            self.motor_controller.set_motor_speed("A", -speed)
            self.motor_controller.set_motor_speed("B", -speed)
        else:
            print(f"시뮬레이션: 후진 (속도: {speed})")

    def turn_left(self, speed: int = 50):
        """좌회전"""
        if self.motor_controller:
            self.motor_controller.set_motor_speed("A", speed)
            self.motor_controller.set_motor_speed("B", -speed)
        else:
            print(f"시뮬레이션: 좌회전 (속도: {speed})")

    def turn_right(self, speed: int = 50):
        """우회전"""
        if self.motor_controller:
            self.motor_controller.set_motor_speed("A", -speed)
            self.motor_controller.set_motor_speed("B", speed)
        else:
            print(f"시뮬레이션: 우회전 (속도: {speed})")

    def set_servo_angle(self, channel: int, angle: float):
        """서보모터 각도 제어"""
        if self.servo_controller:
            self.servo_controller.set_servo_angle(channel, angle)
        else:
            print(f"시뮬레이션: 서보 {channel} → {angle}도")

    def center_servo(self, channel: int):
        """서보모터 중앙 위치로 이동"""
        if self.servo_controller:
            self.servo_controller.center_servo(channel)
        else:
            print(f"시뮬레이션: 서보 {channel} → 90도 (중앙)")

    def sweep_servo(self, channel: int, cycles: int = 1):
        """서보모터 스윕 동작"""
        if self.servo_controller:
            self.servo_controller.sweep_servo(channel, 0, 180, 1.0, cycles)
        else:
            print(f"시뮬레이션: 서보 {channel} 스윕 동작 ({cycles}회)")

    def get_sensor_data(self) -> Dict[str, Any]:
        """모든 센서 데이터 수집"""
        data = {}

        # 라인 센서
        if self.line_sensor:
            data["line"] = self.line_sensor.get_line_position()
        else:
            data["line"] = {"position": None, "description": "센서 없음"}

        # 초음파 센서
        if self.ultrasonic_sensor:
            data["distance"] = self.ultrasonic_sensor.measure_distance()
        else:
            data["distance"] = None

        return data

    def cleanup(self):
        """정리 및 종료"""
        print("로봇 시스템을 정리합니다...")

        self.stop_robot()

        # 각 컨트롤러 정리
        if hasattr(self, "motor_controller") and self.motor_controller:
            self.motor_controller.cleanup()

        if hasattr(self, "line_sensor") and self.line_sensor:
            self.line_sensor.cleanup()

        if hasattr(self, "ultrasonic_sensor") and self.ultrasonic_sensor:
            self.ultrasonic_sensor.cleanup()

        if hasattr(self, "led_controller") and self.led_controller:
            self.led_controller.cleanup()

        if hasattr(self, "servo_controller") and self.servo_controller:
            self.servo_controller.cleanup()

        print("시스템 정리 완료")


def interactive_mode(robot: AutonomousRobot):
    """대화형 제어 모드"""
    print("\n=== Adeept AWR 자율주행 로봇 제어 ===")
    print("명령어:")
    print("  1 - 라인 추적 모드")
    print("  2 - 장애물 회피 모드")
    print("  3 - 자율 주행 모드")
    print("  4 - 수동 제어 모드")
    print("  s - 센서 데이터 확인")
    print("  q - 종료")
    print("  w/a/s/d - 전진/좌회전/후진/우회전 (수동 모드)")
    print("  space - 정지")
    print("  servo <채널> <각도> - 서보모터 제어 (예: servo 0 90)")
    print("  center <채널> - 서보모터 중앙 위치 (예: center 0)")
    print("  sweep <채널> - 서보모터 스윕 동작 (예: sweep 0)")
    print("=====================================\n")

    while True:
        try:
            command = input("명령 입력: ").strip()
            cmd_parts = command.lower().split()

            if not cmd_parts:
                continue

            cmd = cmd_parts[0]

            if cmd == "q":
                break
            elif cmd == "1":
                robot.set_mode(RobotMode.LINE_FOLLOWING)
                robot.start_robot()
            elif cmd == "2":
                robot.set_mode(RobotMode.OBSTACLE_AVOIDANCE)
                robot.start_robot()
            elif cmd == "3":
                robot.set_mode(RobotMode.AUTO_NAVIGATION)
                robot.start_robot()
            elif cmd == "4":
                robot.set_mode(RobotMode.MANUAL)
                robot.stop_robot()
                print("수동 제어 모드 (w/a/s/d로 조작)")
            elif cmd == "s":
                data = robot.get_sensor_data()
                print(f"센서 데이터: {data}")
            elif cmd == "w":
                robot.move_forward()
            elif cmd == "a":
                robot.turn_left()
            elif cmd == "s" and robot.current_mode == RobotMode.MANUAL:
                robot.move_backward()
            elif cmd == "d":
                robot.turn_right()
            elif cmd == " " or cmd == "space":
                robot.stop_robot()
                robot.set_mode(RobotMode.IDLE)
            elif cmd == "servo" and len(cmd_parts) == 3:
                try:
                    channel = int(cmd_parts[1])
                    angle = float(cmd_parts[2])
                    robot.set_servo_angle(channel, angle)
                except ValueError:
                    print("사용법: servo <채널> <각도> (예: servo 0 90)")
            elif cmd == "center" and len(cmd_parts) == 2:
                try:
                    channel = int(cmd_parts[1])
                    robot.center_servo(channel)
                except ValueError:
                    print("사용법: center <채널> (예: center 0)")
            elif cmd == "sweep" and len(cmd_parts) == 2:
                try:
                    channel = int(cmd_parts[1])
                    robot.sweep_servo(channel, 1)
                except ValueError:
                    print("사용법: sweep <채널> (예: sweep 0)")
            else:
                print("알 수 없는 명령어입니다.")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"명령 처리 오류: {e}")


def main():
    """메인 함수"""
    print("Adeept AWR 자율주행 로봇을 시작합니다...")

    # 로봇 인스턴스 생성
    robot = AutonomousRobot()

    try:
        # 대화형 모드 실행
        interactive_mode(robot)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    except Exception as e:
        print(f"예상치 못한 오류: {e}")
    finally:
        # 정리
        robot.cleanup()
        print("프로그램이 종료되었습니다.")


if __name__ == "__main__":
    main()
