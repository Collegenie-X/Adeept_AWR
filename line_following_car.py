#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
라인 센서 기반 자율 주행차
Line Sensor Based Autonomous Car

기능:
- 3개 라인 센서로 라인 추적
- 전역 상수로 속도 조절
- 실시간 센서 상태 출력
- 간단한 PID 제어
"""

import time
import threading
import sys

# ==================== 전역 상수 (속도 조절) ====================
# 직진 속도 설정
FORWARD_SPEED = 50  # 직진 기본 속도 (0-100)

# 좌회전 속도 설정 (좌측으로 치우쳤을 때 우회전 필요)
LEFT_TURN_RIGHT_MOTOR = 60  # 우측 모터 속도 (직진)
LEFT_TURN_LEFT_MOTOR = 20  # 좌측 모터 속도 (감속 또는 후진)

# 우회전 속도 설정 (우측으로 치우쳤을 때 좌회전 필요)
RIGHT_TURN_LEFT_MOTOR = 60  # 좌측 모터 속도 (직진)
RIGHT_TURN_RIGHT_MOTOR = 20  # 우측 모터 속도 (감속 또는 후진)

# 라인 탐색 속도 (라인을 잃었을 때)
SEARCH_SPEED = 30  # 탐색 회전 속도

# 제어 주기
CONTROL_FREQUENCY = 20  # Hz (20Hz = 50ms)
# ================================================================

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


class LineFollowingCar:
    """라인 추적 자율 주행차"""

    def __init__(self):
        print("라인 추적 자율 주행차 초기화 중...")

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
        self.last_valid_position = 0  # 마지막으로 감지된 라인 위치
        self.line_lost_count = 0  # 라인 분실 카운터

        # 제어 스레드
        self.control_thread = None

        self.print_config()

    def print_config(self):
        """현재 설정 출력"""
        print("\n" + "=" * 50)
        print("🚗 라인 추적 자율 주행차 설정")
        print("=" * 50)
        print(f"직진 속도: {FORWARD_SPEED}%")
        print(
            f"좌회전 시 - 우측모터: {LEFT_TURN_RIGHT_MOTOR}%, 좌측모터: {LEFT_TURN_LEFT_MOTOR}%"
        )
        print(
            f"우회전 시 - 좌측모터: {RIGHT_TURN_LEFT_MOTOR}%, 우측모터: {RIGHT_TURN_RIGHT_MOTOR}%"
        )
        print(f"라인 탐색 속도: {SEARCH_SPEED}%")
        print(f"제어 주기: {CONTROL_FREQUENCY}Hz")
        print("=" * 50)

    def start(self):
        """자율 주행 시작"""
        if self.running:
            print("⚠️ 이미 실행 중입니다!")
            return

        print("\n🚀 라인 추적 자율 주행 시작!")
        self.running = True

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

                # 제어 주기 대기
                time.sleep(1.0 / CONTROL_FREQUENCY)

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

        # 센서 상태 출력
        print(
            f"센서: [{sensors['left']}{sensors['middle']}{sensors['right']}] "
            f"위치: {position} - {description}"
        )

        if position is None:
            # 라인 없음 - 탐색 모드
            self.handle_line_lost()
        else:
            # 라인 감지됨 - 추적 모드
            self.line_lost_count = 0
            self.last_valid_position = position
            self.follow_line(position, description)

    def follow_line(self, position, description):
        """라인 추적 제어"""
        if not self.motor_controller:
            print(f"시뮬레이션: {description}")
            return

        if position == 0:
            # 중앙 - 직진
            self.motor_controller.set_motor_speed("A", FORWARD_SPEED)  # 우측
            self.motor_controller.set_motor_speed("B", FORWARD_SPEED)  # 좌측
            print(f"→ 직진 (속도: {FORWARD_SPEED}%)")

        elif position < 0:
            # 좌측으로 치우침 - 우회전 필요
            self.motor_controller.set_motor_speed("A", LEFT_TURN_RIGHT_MOTOR)  # 우측
            self.motor_controller.set_motor_speed("B", LEFT_TURN_LEFT_MOTOR)  # 좌측
            print(
                f"→ 우회전 (우측:{LEFT_TURN_RIGHT_MOTOR}%, 좌측:{LEFT_TURN_LEFT_MOTOR}%)"
            )

        else:  # position > 0
            # 우측으로 치우침 - 좌회전 필요
            self.motor_controller.set_motor_speed("A", RIGHT_TURN_RIGHT_MOTOR)  # 우측
            self.motor_controller.set_motor_speed("B", RIGHT_TURN_LEFT_MOTOR)  # 좌측
            print(
                f"→ 좌회전 (우측:{RIGHT_TURN_RIGHT_MOTOR}%, 좌측:{RIGHT_TURN_LEFT_MOTOR}%)"
            )

    def handle_line_lost(self):
        """라인 분실 처리"""
        self.line_lost_count += 1

        if self.line_lost_count > 5:  # 0.25초 동안 라인 분실
            # 마지막 위치 기반으로 탐색
            if self.last_valid_position <= 0:
                # 좌측에서 잃었으면 좌회전으로 탐색
                if self.motor_controller:
                    self.motor_controller.set_motor_speed("A", SEARCH_SPEED)  # 우측
                    self.motor_controller.set_motor_speed(
                        "B", -SEARCH_SPEED
                    )  # 좌측 후진
                print(f"🔍 좌측 탐색 중... (속도: ±{SEARCH_SPEED}%)")
            else:
                # 우측에서 잃었으면 우회전으로 탐색
                if self.motor_controller:
                    self.motor_controller.set_motor_speed(
                        "A", -SEARCH_SPEED
                    )  # 우측 후진
                    self.motor_controller.set_motor_speed("B", SEARCH_SPEED)  # 좌측
                print(f"🔍 우측 탐색 중... (속도: ±{SEARCH_SPEED}%)")
        else:
            # 잠시 정지
            if self.motor_controller:
                self.motor_controller.motor_stop()
            print("⏸️ 라인 탐색 중...")

    def simulate_driving(self):
        """시뮬레이션 모드 주행"""
        import random

        # 랜덤하게 라인 상태 시뮬레이션
        scenarios = [
            (0, "중앙"),
            (-0.5, "좌측 약간"),
            (0.5, "우측 약간"),
            (-1, "좌측 많이"),
            (1, "우측 많이"),
            (None, "라인 없음"),
        ]

        position, desc = random.choice(scenarios)
        print(f"시뮬레이션: {desc} (위치: {position})")

        if position is None:
            print("→ 탐색 모드")
        elif position == 0:
            print(f"→ 직진 (속도: {FORWARD_SPEED}%)")
        elif position < 0:
            print(
                f"→ 우회전 (우측:{LEFT_TURN_RIGHT_MOTOR}%, 좌측:{LEFT_TURN_LEFT_MOTOR}%)"
            )
        else:
            print(
                f"→ 좌회전 (우측:{RIGHT_TURN_RIGHT_MOTOR}%, 좌측:{RIGHT_TURN_LEFT_MOTOR}%)"
            )

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
    print("\n💡 속도 조절:")
    print("  파일 상단의 전역 상수를 수정하세요:")
    print("  - FORWARD_SPEED: 직진 속도")
    print("  - LEFT_TURN_*: 좌회전(우측으로 치우쳤을때) 속도")
    print("  - RIGHT_TURN_*: 우회전(좌측으로 치우쳤을때) 속도")
    print("  - SEARCH_SPEED: 라인 탐색 속도")


def interactive_mode():
    """대화형 제어 모드"""
    car = LineFollowingCar()

    print("\n🎮 대화형 제어 모드")
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
                car.print_config()
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


def auto_mode():
    """자동 실행 모드 (5초 후 자동 시작)"""
    print("\n🤖 자동 실행 모드")
    print("5초 후 자동으로 라인 추적을 시작합니다...")
    print("Ctrl+C로 언제든지 중단할 수 있습니다.")

    car = LineFollowingCar()

    try:
        # 5초 카운트다운
        for i in range(5, 0, -1):
            print(f"시작까지 {i}초...")
            time.sleep(1)

        car.start()

        # 무한 대기 (Ctrl+C까지)
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n⌨️ Ctrl+C 감지됨")
    finally:
        car.cleanup()


def main():
    """메인 함수"""
    print("🚗 라인 센서 기반 자율 주행차")
    print("=" * 40)

    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        # 자동 모드
        auto_mode()
    else:
        # 대화형 모드
        interactive_mode()

    print("\n👋 프로그램 종료")


if __name__ == "__main__":
    main()
