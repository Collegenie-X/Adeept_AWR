#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
초간단 자율 주행차 - 모듈형 메인 컨트롤러
Ultra Simple Autonomous Car - Modular Main Controller

기능:
1. 라인 센서로 검은 선 따라가기
2. 초음파 센서로 장애물 피하기
3. 키보드로 실시간 속도 조절

모듈형 설계:
- 각 기능별 서비스 클래스로 분리
- 메인 컨트롤러는 조정 및 흐름 제어만 담당
"""

import time
import threading
import os
import sys
import termios

# 하드웨어/컴포넌트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 컴포넌트 서비스 임포트 (모듈형)
from simple_car.components import (
    MotorControlService,
    UltrasonicSensorService,
    LineSensorService,
    KeyboardInputService,
    ConfigurationService,
    MenuService,
    AutonomousDriver,
    ManualController,
    SensorMonitor,
)


class UltraSimpleCarController:
    """초간단 자율주행차 메인 컨트롤러"""

    def __init__(self):
        # 서비스 초기화
        self.config = ConfigurationService()
        self.keyboard = KeyboardInputService()

        # 하드웨어 서비스
        self.line_service = LineSensorService()
        self.motor_service = MotorControlService()
        self.ultrasonic_service = UltrasonicSensorService()

        # 기능별 컨트롤러
        self.menu = MenuService(self.config)
        self.manual_controller = ManualController(
            self.motor_service, self.line_service, self.config
        )
        self.auto_driver = AutonomousDriver(
            self.motor_service,
            self.line_service,
            self.ultrasonic_service,
            self.config,
            manual_controller=self.manual_controller,
        )
        self.sensor_monitor = SensorMonitor(
            self.line_service, self.ultrasonic_service, self.config
        )

        # 상태 변수
        self.autonomous_mode = False
        self.running = True
        self.manual_control_active = False

    def setup(self) -> bool:
        """서비스 준비 상태 확인"""
        try:
            # 하드웨어 연결 상태 확인
            hw_line = getattr(self.line_service, "controller", None) is not None
            hw_motor = getattr(self.motor_service, "controller", None) is not None
            hw_ultra = getattr(self.ultrasonic_service, "sensor", None) is not None

            print(
                f"Hardware(line={hw_line}, motor={hw_motor}, ultrasonic={hw_ultra}) ready"
            )
            return True
        except Exception as e:
            print(f"Hardware setup error: {e}")
            return False

    def handle_keyboard_input(self) -> None:
        """키보드 입력 처리 스레드"""
        print("\n🎮 키보드 제어 활성화 - 키를 누르면 바로 반응합니다")
        print("'s' 명령만 Enter 키 필요, 나머지는 키만 누르면 즉시 반응")
        print("Ctrl+C로 안전하게 종료 가능")

        while self.running:
            try:
                # 상태 표시
                self.menu.print_status_line(
                    self.autonomous_mode, self.manual_control_active
                )

                # 키 입력 받기
                key = self.keyboard.read_single_key()
                if key is None:
                    continue

                # Early return 패턴으로 키 처리
                if not self._handle_control_keys(key):
                    continue
                if not self._handle_speed_adjustment_keys(key):
                    continue
                if not self._handle_debug_keys(key):
                    continue
                if not self._handle_manual_movement_keys(key):
                    continue

                # 알 수 없는 키
                if key and key.isprintable():
                    print(f"\n❌ 알 수 없는 명령: '{key}'. 'h' 키로 도움말 확인")

            except KeyboardInterrupt:
                print("\nCtrl+C 감지 - 안전 종료 중...")
                self.running = False
                break
            except Exception as e:
                print(f"\n오류: {e}")
                time.sleep(0.1)

    def _handle_control_keys(self, key: str) -> bool:
        """제어 키 처리 (h, q, Enter, space/p)"""
        if key == "h":
            print("\n")
            self.menu.print_control_menu()
            return False
        elif key == "q":
            print("\n🚪 프로그램 종료 요청")
            self.menu.print_final_settings()
            self.running = False
            return False
        elif key == "\n":
            if not self.autonomous_mode:
                print("\n🚗 자동 주행 시작")
                self.autonomous_mode = True
                self.manual_control_active = False
            else:
                print("\n이미 자동 주행 중")
            return False
        elif key in ["p", "space"]:
            print("\n🛑 즉시 정지 - 모든 동작 중단")
            self.manual_controller.emergency_stop()
            if self.autonomous_mode:
                self.autonomous_mode = False
                self.manual_control_active = True
                print("자동 모드 → 수동 모드로 전환")
            else:
                self.manual_control_active = True
                print("수동 모드에서 모든 동작 정지")
            return False
        elif key == "\x03":  # Ctrl+C
            print("\nCtrl+C 감지 - 안전 종료 중...")
            self.running = False
            return False
        return True

    def _handle_speed_adjustment_keys(self, key: str) -> bool:
        """속도 조절 키 처리 (1-0)"""
        if key == "1":
            speed = self.config.adjust_forward_speed(-10)
            print(f"\n✓ 전진 속도: {speed}%")
        elif key == "2":
            speed = self.config.adjust_forward_speed(10)
            print(f"\n✓ 전진 속도: {speed}%")
        elif key == "3":
            turn_time = self.config.adjust_turn_hold_time(1)  # +0.05초
            print(f"\n✓ 회전 지연 시간: {turn_time:.2f}초 (+0.05초)")
        elif key == "4":
            turn_time = self.config.adjust_turn_hold_time(-1)  # -0.05초
            print(f"\n✓ 회전 지연 시간: {turn_time:.2f}초 (-0.05초)")
        elif key == "5":
            speed = self.config.adjust_high_turn_speed(-10)
            print(f"\n✓ 강한 회전 속도: {speed}%")
        elif key == "6":
            speed = self.config.adjust_high_turn_speed(10)
            print(f"\n✓ 강한 회전 속도: {speed}%")
        elif key == "7":
            distance = self.config.adjust_safe_distance(-5)
            print(f"\n✓ 안전 거리: {distance}cm")
        elif key == "8":
            distance = self.config.adjust_safe_distance(5)
            print(f"\n✓ 안전 거리: {distance}cm")
        elif key == "9":
            time_val = self.config.adjust_avoid_time(-1)
            print(f"\n✓ 회피 시간: {time_val:.1f}s")
        elif key == "0":
            time_val = self.config.adjust_avoid_time(1)
            print(f"\n✓ 회피 시간: {time_val:.1f}s")
        elif key == "<":
            # DEFAULT_AVOID_TIME -0.2초 (신기능)
            avoid_time = self.config.adjust_default_avoid_time(-1)
            print(f"\n✓ 기본 회피 시간: {avoid_time:.1f}초 (-0.2초)")
        elif key == ">":
            # DEFAULT_AVOID_TIME +0.2초 (신기능)
            avoid_time = self.config.adjust_default_avoid_time(1)
            print(f"\n✓ 기본 회피 시간: {avoid_time:.1f}초 (+0.2초)")
        else:
            return True  # 처리하지 않은 키
        return False

    def _handle_debug_keys(self, key: str) -> bool:
        """디버깅 키 처리 (x, z, t)"""
        if key == "x":
            print("\n🔍 라인 센서 상태 확인 중 (3초)...")
            self.sensor_monitor.show_line_sensor_status(3)
        elif key == "z":
            print("\n🔍 거리 센서 상태 확인 중...")
            self.sensor_monitor.show_distance_sensor_status(5)
        elif key == "t":
            print("\n🧪 조향 테스트 시퀀스 시작")
            self.manual_controller.test_steering_sequence()
        elif key == "u":
            # 초음파 센서 on/off 토글
            status = self.config.toggle_ultrasonic_sensor()
            status_text = "활성화" if status else "비활성화"
            status_icon = "🔊" if status else "🔇"
            print(f"\n{status_icon} 초음파 센서: {status_text}")
        elif key == "y":
            # 초음파 센서 측정 모드 전환 (신기능)
            mode = self.config.cycle_ultrasonic_mode()
            description = self.config.get_ultrasonic_mode_description()
            print(f"\n🔧 초음파 센서 모드: {mode} ({description})")
        elif key == "h":
            # 종합 도움말 표시
            self.show_comprehensive_help()
        else:
            return True  # 처리하지 않은 키
        return False

    def _handle_manual_movement_keys(self, key: str) -> bool:
        """수동 이동 키 처리 (w/a/s/d, 화살표)"""
        if (
            key in ["w", "a", "d", "s", "j", "k", "up", "down", "left", "right"]
            and not self.autonomous_mode
        ):
            self.manual_control_active = True
            if key in ["w", "up"]:
                print("\n🔼 수동 전진")
                self.manual_controller.manual_forward()
            elif key in ["s", "down"]:
                print("\n🔽 수동 후진")
                self.manual_controller.manual_backward()
            elif key in ["a", "left"]:
                print("\n◀️ 수동 좌회전")
                self.manual_controller.manual_turn_left()
            elif key in ["d", "right"]:
                print("\n▶️ 수동 우회전")
                self.manual_controller.manual_turn_right()
            elif key in ["k"]:
                print("\n▶️ 수동 우회전")
                self.manual_controller.manual_slight_right()
            elif key in ["j"]:
                print("\n▶️ 수동 좌회전")
                self.manual_controller.manual_slight_left()
            return False
        return True

    def cleanup(self) -> None:
        """완전 초기화 - Ctrl+C 시 안전한 종료"""
        try:
            print("\n🛑 안전한 종료 중...")

            # 상태 초기화
            self.running = False
            self.autonomous_mode = False
            self.manual_control_active = False

            # 긴급 정지
            self.manual_controller.emergency_stop()

            # 현재 설정값 표시
            self.menu.print_final_settings()

            # 터미널 설정 복원
            try:
                termios.tcsetattr(
                    sys.stdin, termios.TCSADRAIN, termios.tcgetattr(sys.stdin)
                )
            except:
                pass

            # 하드웨어 정리
            self._cleanup_hardware()

            print("✅ 안전한 종료 완료")

        except Exception as e:
            print(f"⚠️ 종료 중 오류: {e}")
        finally:
            print("\n")

    def show_comprehensive_help(self) -> None:
        """종합 도움말 표시 - 모든 최신 기능 포함"""
        print("\n" + "=" * 80)
        print("🆘 Ultra Simple Car - 종합 도움말 (최신 업데이트 2024)")
        print("=" * 80)

        print("\n🚗 기본 수동 조작:")
        print("  w/↑    : 전진 (설정 속도로)")
        print("  s/↓    : 후진")
        print("  a/←    : 좌회전 (강한 회전)")
        print("  d/→    : 우회전 (강한 회전)")
        print("  j      : 약한 좌회전")
        print("  k      : 약한 우회전")
        print("  스페이스: 긴급 정지")

        print("\n⚙️ 실시간 설정 조절 (Enter 불필요):")
        print("  1,2    : 전진 속도 -10%/+10%")
        print("  3,4    : 회전 지연 시간 -0.05초/+0.05초 ⭐ 새기능")
        print("  5,6    : 강한 회전 속도 -10%/+10%")
        print("  7,8    : 안전 거리 -5cm/+5cm")
        print("  9,0    : 회피 시간 -0.1초/+0.1초")
        print("  <,>    : 기본 회피 시간 -0.2초/+0.2초 (1.0~2.6초) ⭐ 새기능")

        print("\n🤖 자율주행 모드:")
        print("  Enter  : 자율주행 시작/정지")
        print("  자율주행 중에도 1-0키로 실시간 설정 조절 가능")

        print("\n🔧 고급 기능:")
        print("  u      : 초음파 센서 on/off 토글 ⭐ 새기능")
        current_ultrasonic = (
            "🔊 활성화" if self.config.ultrasonic_enabled else "🔇 비활성화"
        )
        print(f"           (현재 상태: {current_ultrasonic})")
        print("  y      : 초음파 센서 측정 모드 전환 ⭐ 새기능")
        current_mode = self.config.get_ultrasonic_mode_description()
        print(f"           (현재 모드: {current_mode})")
        print("  m      : 모터 캘리브레이션 (직진 보정)")
        print("  r      : 모든 설정 기본값으로 초기화")

        print("\n🔍 센서 모니터링:")
        print("  x      : 라인 센서 실시간 상태 확인")
        print("  z      : 거리 센서 실시간 상태 확인")

        print("\n🧪 테스트 및 디버깅:")
        print("  t      : 조향 테스트 시퀀스")
        print("  기타 테스트 함수들은 manual_controller에서 직접 호출")

        print("\n✨ 최신 추가 기능들:")
        print("  🎯 적응형 라인 팔로잉:")
        print("     - 라인 위치에 따른 4단계 회전 강도 자동 조절")
        print("     - 미세조정(0.08초) → 약함(0.12초) → 보통(0.18초) → 강함(0.25초)")

        print("  🛡️ 장애물 회피 개선:")
        print("     - 초음파 센서 40cm 조기 감지")
        print("     - 정지(0.1초) → 후진(0.1초) → 좌회전 안정적 시퀀스")
        print("     - 111 패턴(모든 센서) 처리로 선 이탈 방지")

        print("  ⏱️ 회전 시간 미세 조정:")
        print("     - 3,4키로 0.05초 단위 조절 (0.1~0.5초 범위)")
        print("     - 자율주행 중 실시간 적용")

        print("  🔊/🔇 초음파 센서 토글:")
        print("     - u키로 장애물 감지 기능 on/off")
        print("     - 성능 최적화 및 트랙별 맞춤 설정")

        print("  📡 초음파 센서 측정 모드 (y키):")
        print("     - single: 단일 측정 (최고 속도, 기본)")
        print("     - fast: 3회 측정 중간값 (빠름+정확)")
        print("     - stable: 5회 측정 평균값 (느림+안정)")
        print(f"     - 현재: {self.config.ultrasonic_mode} 모드")

        print("\n📊 현재 설정 요약:")
        settings = self.config.get_current_settings()
        print(f"  전진 속도: {settings['forward_speed']}%")
        print(f"  회전 지연: {settings['turn_hold_seconds']:.2f}초")
        print(f"  안전 거리: {settings['safe_distance']}cm")
        print(
            f"  기본 회피 시간: {self.config.DEFAULT_AVOID_TIME:.1f}초 (범위: {self.config.AVOID_TIME_MIN:.1f}~{self.config.AVOID_TIME_MAX:.1f}초)"
        )
        ultrasonic_text = "활성화" if settings["ultrasonic_enabled"] else "비활성화"
        print(f"  초음파 센서: {ultrasonic_text}")
        print(
            f"  센서 측정 모드: {self.config.ultrasonic_mode} ({self.config.get_ultrasonic_mode_description()})"
        )

        # 변경된 설정이 있으면 표시
        changes = self.config.get_changed_settings()
        if changes:
            print("\n📝 기본값에서 변경된 설정:")
            for change in changes:
                print(f"  • {change}")
        else:
            print("\n📝 모든 설정이 기본값 상태")

        print("\n💡 주요 팁:")
        print("  • 자율주행 중에도 대부분의 설정을 실시간 조절 가능")
        print("  • 트랙이 단순하면 u키로 초음파 센서 off → 빠른 주행")
        print("  • y키로 센서 모드 조절: single(최고속도) → fast(균형) → stable(정확)")
        print("  • 회전이 부족/과다하면 3,4키로 회전 시간 미세 조정")
        print("  • 111 패턴에서 선 이탈시 자동으로 안정적 처리 수행")

        print("\n🆘 문제해결:")
        print("  • 직진 안됨 → m키로 모터 캘리브레이션")
        print("  • 회전 부족/과다 → 3,4키로 회전 시간 조절")
        print("  • 장애물 오감지 → u키로 초음파 센서 off")
        print("  • 센서 측정 불안정 → y키로 stable 모드 전환")
        print("  • 반응 속도 느림 → y키로 single 모드 전환")
        print("  • 설정 꼬임 → r키로 전체 초기화")

        print("\n" + "=" * 80)
        print("🎮 언제든 h키를 눌러 이 도움말을 다시 볼 수 있습니다!")
        print("=" * 80)

    def _cleanup_hardware(self) -> None:
        """하드웨어 서비스 정리"""
        services = [
            (self.line_service, "라인 센서"),
            (self.motor_service, "모터 컨트롤러"),
            (self.ultrasonic_service, "초음파 센서"),
        ]

        for service, name in services:
            try:
                if service and hasattr(service, "cleanup"):
                    service.cleanup()
                    print(f"✓ {name} 정리")
            except:
                pass

    def run(self) -> None:
        """메인 실행 함수"""
        print("Ultra Simple Autonomous Car - 노란선 추적 주행 버전")
        print("=" * 60)
        print("🛣️ 도로: 검정색 / 라인: 노란색")
        print("🎯 기능: 노란선 추적 + 장애물 회피 + 키보드 제어")
        print("🔧 센서: test_line_sensors.py 로직 기반 정확한 라인 감지")
        print("=" * 60)

        settings = self.config.get_current_settings()
        print("초기 설정:")
        print(f"  🚗 전진 속도: {settings['forward_speed']}%")
        print(
            f"  🔄 회전 속도: 약함={settings['low_turn_speed']}%, 강함={settings['high_turn_speed']}%"
        )
        print(f"  🛡️ 안전 거리: {settings['safe_distance']}cm")
        print(f"  ⏱️ 회피 시간: {settings['avoid_time']}s")
        print("=" * 60)

        if not self.setup():
            print("Setup failed")
            return

        try:
            print("\n🎮 키보드 제어 모드 시작")
            print("'h' 키를 눌러 제어 방법을 확인하세요")

            # 제어 가이드 출력
            self.menu.print_control_menu()

            # 키보드 입력 스레드 시작
            keyboard_thread = threading.Thread(
                target=self.handle_keyboard_input, daemon=True
            )
            keyboard_thread.start()

            # 메인 루프
            while self.running:
                try:
                    if self.autonomous_mode:
                        # 자동 주행 모드 (더 빠른 루프)
                        self.auto_driver.drive_step()
                        time.sleep(self.config.DEFAULT_AUTO_LOOP_INTERVAL)
                    else:
                        # 수동 모드 - 키보드 입력만 처리
                        time.sleep(0.02)
                except KeyboardInterrupt:
                    print("\n\n⚠️ Ctrl+C 감지 - 긴급 정지 중...")
                    self.manual_controller.emergency_stop()
                    self.running = False
                    break

        except KeyboardInterrupt:
            print("\n\n⚠️ Ctrl+C 감지 - 안전 종료 중...")
            self.manual_controller.emergency_stop()
            self.running = False
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            self.manual_controller.emergency_stop()
            self.running = False
        finally:
            # 항상 완전 초기화 실행
            self.cleanup()
            print("🏁 프로그램 완전 종료")


def main():
    """메인 함수"""
    controller = UltraSimpleCarController()
    controller.run()


if __name__ == "__main__":
    main()
