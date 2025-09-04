#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
고급 라인 센서 기반 자율 주행차
Advanced Line Sensor Based Autonomous Car

기능:
- 설정 파일을 통한 속도 조절
- 실시간 설정 변경
- 향상된 제어 알고리즘
- 상세한 디버그 정보
"""

import time
import threading
import sys
import importlib

# 설정 파일 임포트
try:
    import car_config as config

    print("✓ 설정 파일 로드 완료")
except ImportError:
    print("❌ car_config.py 파일을 찾을 수 없습니다.")
    sys.exit(1)

# 하드웨어 모듈 임포트
try:
    from hardware.test_line_sensors import LineSensorController
    from hardware.test_gear_motors import GearMotorController

    HARDWARE_AVAILABLE = True
    print("✓ 하드웨어 모듈 로드 완료")
except ImportError as e:
    print(f"하드웨어 모듈 없음: {e}")
    print("시뮬레이션 모드로 실행")
    HARDWARE_AVAILABLE = False


class AdvancedLineFollowingCar:
    """고급 라인 추적 자율 주행차"""

    def __init__(self):
        print("고급 라인 추적 자율 주행차 초기화 중...")

        # 설정 검증
        errors = config.validate_config()
        if errors:
            print("❌ 설정 오류 발견:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)

        # 하드웨어 초기화
        self.line_sensor = None
        self.motor_controller = None
        self.running = False

        if HARDWARE_AVAILABLE:
            try:
                self.line_sensor = LineSensorController()
                self.motor_controller = GearMotorController()
                print("✓ 하드웨어 초기화 완료")
            except Exception as e:
                print(f"하드웨어 초기화 실패: {e}")
                print("시뮬레이션 모드로 전환")

        # 제어 상태
        self.last_valid_position = 0
        self.line_lost_count = 0
        self.stable_count = 0
        self.last_update_time = time.time()

        # 통계
        self.stats = {
            "total_time": 0,
            "line_detected_time": 0,
            "left_turns": 0,
            "right_turns": 0,
            "line_lost_events": 0,
        }

        # 제어 스레드
        self.control_thread = None

        config.print_config()

    def start(self):
        """자율 주행 시작"""
        if self.running:
            print("⚠️ 이미 실행 중입니다!")
            return

        print("\n🚀 고급 라인 추적 자율 주행 시작!")
        self.running = True
        self.stats["start_time"] = time.time()

        # 제어 스레드 시작
        self.control_thread = threading.Thread(target=self.control_loop, daemon=True)
        self.control_thread.start()

    def stop(self):
        """자율 주행 정지"""
        print("\n🛑 라인 추적 정지 중...")
        self.running = False

        # 모터 정지
        if self.motor_controller:
            self.motor_controller.motor_stop()

        # 통계 출력
        self.print_statistics()
        print("✓ 정지 완료")

    def control_loop(self):
        """메인 제어 루프"""
        print("제어 루프 시작...")

        while self.running:
            try:
                # 라인 센서 읽기
                if self.line_sensor:
                    line_info = self.line_sensor.get_line_position()
                    self.process_line_sensor(line_info)
                else:
                    # 시뮬레이션 모드
                    self.simulate_driving()

                # 통계 업데이트
                self.update_statistics()

                # 제어 주기 대기
                time.sleep(1.0 / config.CONTROL_FREQUENCY)

            except Exception as e:
                print(f"❌ 제어 루프 오류: {e}")
                break

        # 안전 정지
        if self.motor_controller:
            self.motor_controller.motor_stop()
        print("제어 루프 종료")

    def process_line_sensor(self, line_info):
        """라인 센서 데이터 처리 및 모터 제어"""
        position = line_info["position"]
        description = line_info["description"]
        pattern = line_info["pattern"]
        sensors = line_info["sensors"]

        # 디버그 정보 출력
        if config.DEBUG_CONFIG["show_sensor_raw"]:
            print(
                f"센서: [{sensors['left']}{sensors['middle']}{sensors['right']}] ",
                end="",
            )

        if config.DEBUG_CONFIG["show_position"]:
            print(f"위치: {position} - {description}", end="")

        if position is None:
            # 라인 없음 - 탐색 모드
            self.handle_line_lost()
        else:
            # 라인 감지됨 - 추적 모드
            self.line_lost_count = 0
            self.last_valid_position = position
            self.stable_count += 1
            self.follow_line_advanced(position, description)

        print()  # 줄바꿈

    def follow_line_advanced(self, position, description):
        """고급 라인 추적 제어"""
        if not self.motor_controller:
            if config.DEBUG_CONFIG["show_motor_speed"]:
                print(f" | 시뮬레이션: {description}")
            return

        # 급회전 판단
        is_sharp_turn = abs(position) > config.SENSOR_CONFIG["position_threshold"]

        if position == 0:
            # 중앙 - 직진
            left_speed = right_speed = config.FORWARD_SPEED
            direction = "직진"

        elif position < 0:
            # 좌측으로 치우침 - 우회전 필요
            right_speed = config.LEFT_TURN_CONFIG["right_motor"]
            left_speed = config.LEFT_TURN_CONFIG["left_motor"]

            if is_sharp_turn and config.SHARP_TURN_CONFIG["opposite_direction"]:
                # 급회전: 반대방향 모터 사용
                right_speed += config.SHARP_TURN_CONFIG["speed_boost"]
                left_speed = -abs(left_speed)  # 후진
                direction = "급우회전"
            else:
                direction = "우회전"

            self.stats["right_turns"] += 1

        else:  # position > 0
            # 우측으로 치우침 - 좌회전 필요
            left_speed = config.RIGHT_TURN_CONFIG["left_motor"]
            right_speed = config.RIGHT_TURN_CONFIG["right_motor"]

            if is_sharp_turn and config.SHARP_TURN_CONFIG["opposite_direction"]:
                # 급회전: 반대방향 모터 사용
                left_speed += config.SHARP_TURN_CONFIG["speed_boost"]
                right_speed = -abs(right_speed)  # 후진
                direction = "급좌회전"
            else:
                direction = "좌회전"

            self.stats["left_turns"] += 1

        # 속도 제한 적용
        right_speed = max(
            config.SAFETY_CONFIG["min_speed"],
            min(config.SAFETY_CONFIG["max_speed"], right_speed),
        )
        left_speed = max(
            config.SAFETY_CONFIG["min_speed"],
            min(config.SAFETY_CONFIG["max_speed"], left_speed),
        )

        # 모터 제어
        self.motor_controller.set_motor_speed("A", right_speed)  # 우측
        self.motor_controller.set_motor_speed("B", left_speed)  # 좌측

        if config.DEBUG_CONFIG["show_motor_speed"]:
            print(f" | {direction} (우측:{right_speed}%, 좌측:{left_speed}%)", end="")

    def handle_line_lost(self):
        """라인 분실 처리"""
        self.line_lost_count += 1
        line_lost_time = self.line_lost_count / config.CONTROL_FREQUENCY

        if line_lost_time > config.LINE_LOST_TIMEOUT:
            # 탐색 모드 시작
            if (
                self.line_lost_count
                == int(config.LINE_LOST_TIMEOUT * config.CONTROL_FREQUENCY) + 1
            ):
                self.stats["line_lost_events"] += 1

            # 마지막 위치 기반으로 탐색
            if self.last_valid_position <= 0:
                # 좌측에서 잃었으면 좌회전으로 탐색
                if self.motor_controller:
                    self.motor_controller.set_motor_speed(
                        "A", config.SEARCH_SPEED
                    )  # 우측
                    self.motor_controller.set_motor_speed(
                        "B", -config.SEARCH_SPEED
                    )  # 좌측 후진
                direction = "좌측 탐색"
            else:
                # 우측에서 잃었으면 우회전으로 탐색
                if self.motor_controller:
                    self.motor_controller.set_motor_speed(
                        "A", -config.SEARCH_SPEED
                    )  # 우측 후진
                    self.motor_controller.set_motor_speed(
                        "B", config.SEARCH_SPEED
                    )  # 좌측
                direction = "우측 탐색"

            if config.DEBUG_CONFIG["show_motor_speed"]:
                print(f" | 🔍 {direction} (±{config.SEARCH_SPEED}%)", end="")
        else:
            # 잠시 정지
            if self.motor_controller:
                self.motor_controller.motor_stop()
            print(" | ⏸️ 라인 대기", end="")

    def update_statistics(self):
        """통계 업데이트"""
        current_time = time.time()
        if hasattr(self.stats, "start_time"):
            self.stats["total_time"] = current_time - self.stats["start_time"]

    def print_statistics(self):
        """통계 출력"""
        print("\n" + "=" * 50)
        print("📊 주행 통계")
        print("=" * 50)
        print(f"총 주행 시간: {self.stats['total_time']:.1f}초")
        print(f"좌회전 횟수: {self.stats['left_turns']}")
        print(f"우회전 횟수: {self.stats['right_turns']}")
        print(f"라인 분실 횟수: {self.stats['line_lost_events']}")

        if self.stats["total_time"] > 0:
            turn_rate = (
                self.stats["left_turns"] + self.stats["right_turns"]
            ) / self.stats["total_time"]
            print(f"회전 빈도: {turn_rate:.2f}회/초")
        print("=" * 50)

    def simulate_driving(self):
        """시뮬레이션 모드 주행"""
        import random

        if config.SIMULATION_CONFIG["random_scenarios"]:
            scenarios = [
                (0, "중앙"),
                (-0.3, "좌측 약간"),
                (0.3, "우측 약간"),
                (-0.8, "좌측 많이"),
                (0.8, "우측 많이"),
                (None, "라인 없음"),
            ]

            position, desc = random.choice(scenarios)
        else:
            # 고정 시나리오
            position, desc = (0, "중앙")

        if config.DEBUG_CONFIG["show_position"]:
            print(f"시뮬레이션: {desc} (위치: {position})", end="")

        # 가상 제어 로직 시뮬레이션
        if position is None:
            if config.DEBUG_CONFIG["show_motor_speed"]:
                print(" | 탐색 모드", end="")
        elif position == 0:
            if config.DEBUG_CONFIG["show_motor_speed"]:
                print(f" | 직진 ({config.FORWARD_SPEED}%)", end="")
        elif position < 0:
            if config.DEBUG_CONFIG["show_motor_speed"]:
                print(
                    f" | 우회전 ({config.LEFT_TURN_CONFIG['right_motor']}%/{config.LEFT_TURN_CONFIG['left_motor']}%)",
                    end="",
                )
        else:
            if config.DEBUG_CONFIG["show_motor_speed"]:
                print(
                    f" | 좌회전 ({config.RIGHT_TURN_CONFIG['left_motor']}%/{config.RIGHT_TURN_CONFIG['right_motor']}%)",
                    end="",
                )

        print()  # 줄바꿈

    def reload_config(self):
        """설정 파일 다시 로드"""
        try:
            importlib.reload(config)
            print("✓ 설정 파일이 다시 로드되었습니다.")
            config.print_config()
        except Exception as e:
            print(f"❌ 설정 파일 로드 실패: {e}")

    def cleanup(self):
        """정리 및 종료"""
        print("\n🧹 시스템 정리 중...")

        self.stop()

        # 하드웨어 정리
        try:
            if self.motor_controller:
                self.motor_controller.cleanup()
            if self.line_sensor:
                self.line_sensor.cleanup()
        except Exception as e:
            print(f"정리 중 오류: {e}")

        print("✓ 정리 완료")


def print_help():
    """사용법 출력"""
    print("\n📋 사용법:")
    print("  s - 자율 주행 시작")
    print("  q - 정지 및 종료")
    print("  h - 도움말")
    print("  c - 현재 설정 보기")
    print("  r - 설정 파일 다시 로드")
    print("  stat - 통계 보기")
    print("\n💡 설정 조절:")
    print("  car_config.py 파일을 수정한 후 'r' 명령으로 다시 로드하세요.")
    print("  설정 변경 후 즉시 적용됩니다.")


def interactive_mode():
    """대화형 제어 모드"""
    car = AdvancedLineFollowingCar()

    print("\n🎮 고급 대화형 제어 모드")
    print_help()

    try:
        while True:
            command = input("\n명령 입력 (h:도움말): ").strip().lower()

            if command == "s":
                car.start()
            elif command == "q":
                break
            elif command == "h":
                print_help()
            elif command == "c":
                config.print_config()
            elif command == "r":
                car.reload_config()
            elif command == "stat":
                car.print_statistics()
            elif command == "":
                continue
            else:
                print(
                    "❌ 알 수 없는 명령어입니다. 'h'를 입력하면 도움말을 볼 수 있습니다."
                )

    except KeyboardInterrupt:
        print("\n\n⌨️ Ctrl+C 감지됨")
    finally:
        car.cleanup()


def main():
    """메인 함수"""
    print("🚗 고급 라인 센서 기반 자율 주행차")
    print("=" * 50)

    interactive_mode()
    print("\n👋 프로그램 종료")


if __name__ == "__main__":
    main()
