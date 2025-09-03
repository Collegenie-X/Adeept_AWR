#!/usr/bin/env python3
# 파일명: main.py
# 설명: 라즈베리파이 자율주행 로봇 메인 실행 파일
# 작성일: 2024
"""
🤖 라즈베리파이 기반 자율주행 로봇 메인 프로그램

주요 기능:
- 라인 추적을 통한 자율주행
- 초음파 센서를 이용한 장애물 회피
- LED를 통한 상태 표시
- 안전한 시스템 종료

사용법:
    python3 main.py

제어 명령:
    's' - 자율주행 시작
    'q' - 프로그램 종료
    'e' - 비상 정지
    't' - 상태 확인
    'r' - 시스템 재시작
"""

import sys
import time
import threading
from typing import Optional

# 자율주행 로봇 모듈 임포트
try:
    from autonomous_robot.controllers.autonomous_controller import (
        AutonomousController,
        AutonomousMode,
    )
    from autonomous_robot import print_package_info, get_package_info
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print("라즈베리파이 환경에서 실행하거나 필요한 라이브러리를 설치하세요.")
    sys.exit(1)


class RobotMainApplication:
    """자율주행 로봇 메인 애플리케이션 클래스"""

    def __init__(self):
        """메인 애플리케이션 초기화"""
        self.robot: Optional[AutonomousController] = None
        self.is_running = False
        self.user_input_thread: Optional[threading.Thread] = None

        print("🤖 라즈베리파이 자율주행 로봇 시스템")
        print("=" * 50)

        # 패키지 정보 출력
        print_package_info()
        print("=" * 50)

    def initialize_robot(self) -> bool:
        """로봇 시스템 초기화"""
        print("\n🔧 로봇 시스템 초기화 중...")

        try:
            # 자율주행 컨트롤러 생성
            self.robot = AutonomousController()

            # 모든 컴포넌트 초기화
            if self.robot.initialize_all_components():
                print("✅ 로봇 시스템 초기화 성공!")
                return True
            else:
                print("❌ 일부 컴포넌트 초기화 실패")
                return False

        except Exception as e:
            print(f"❌ 로봇 초기화 중 오류 발생: {e}")
            return False

    def show_help_menu(self) -> None:
        """도움말 메뉴 출력"""
        print("\n📋 제어 명령어:")
        print("  's' - 자율주행 시작")
        print("  'q' - 프로그램 종료")
        print("  'e' - 비상 정지")
        print("  't' - 현재 상태 확인")
        print("  'r' - 시스템 재시작")
        print("  'h' - 도움말 보기")
        print("  'i' - 시스템 정보 확인")

    def handle_user_input(self) -> None:
        """사용자 입력 처리 스레드"""
        while self.is_running:
            try:
                command = input("\n🎮 명령 입력 (h:도움말): ").strip().lower()

                if command == "s":
                    self.start_autonomous_driving()
                elif command == "q":
                    self.shutdown_system()
                    break
                elif command == "e":
                    self.emergency_stop()
                elif command == "t":
                    self.show_status()
                elif command == "r":
                    self.restart_system()
                elif command == "h":
                    self.show_help_menu()
                elif command == "i":
                    self.show_system_info()
                else:
                    print(
                        "❓ 알 수 없는 명령입니다. 'h'를 입력하여 도움말을 확인하세요."
                    )

            except EOFError:
                # Ctrl+D 입력 시
                break
            except KeyboardInterrupt:
                # Ctrl+C 입력 시
                self.emergency_stop()
                break
            except Exception as e:
                print(f"⚠️ 입력 처리 중 오류: {e}")

    def start_autonomous_driving(self) -> None:
        """자율주행 시작"""
        if not self.robot:
            print("❌ 로봇이 초기화되지 않았습니다.")
            return

        print("\n🚗 자율주행을 시작합니다...")
        print("⚠️ 안전을 위해 로봇 주변을 확인하세요!")
        print("🛑 비상 정지: 'e' 키를 누르거나 Ctrl+C")

        # 3초 카운트다운
        for i in range(3, 0, -1):
            print(f"⏰ {i}초 후 시작...")
            time.sleep(1)

        if self.robot.start_autonomous_driving(AutonomousMode.LINE_FOLLOWING):
            print("✅ 자율주행이 시작되었습니다!")
        else:
            print("❌ 자율주행 시작에 실패했습니다.")

    def emergency_stop(self) -> None:
        """비상 정지"""
        if self.robot:
            print("\n🛑 비상 정지 실행!")
            self.robot.emergency_stop()
            print("✅ 로봇이 안전하게 정지되었습니다.")
        else:
            print("❌ 로봇이 초기화되지 않았습니다.")

    def show_status(self) -> None:
        """현재 상태 확인"""
        if not self.robot:
            print("❌ 로봇이 초기화되지 않았습니다.")
            return

        print("\n📊 로봇 상태 정보:")
        self.robot.print_status()

        # 성능 통계
        stats = self.robot.get_performance_stats()
        if stats:
            print(f"\n📈 성능 통계:")
            print(f"  평균 루프 주파수: {stats['average_loop_rate_hz']:.1f} Hz")
            print(f"  총 실행 시간: {stats['runtime_seconds']:.1f}초")

    def restart_system(self) -> None:
        """시스템 재시작"""
        print("\n🔄 시스템을 재시작합니다...")

        # 기존 시스템 정리
        if self.robot:
            self.robot.cleanup()

        # 새로운 시스템 초기화
        if self.initialize_robot():
            print("✅ 시스템 재시작 완료!")
        else:
            print("❌ 시스템 재시작 실패")

    def show_system_info(self) -> None:
        """시스템 정보 출력"""
        print("\n💻 시스템 정보:")

        # 패키지 정보
        info = get_package_info()
        print(f"  버전: {info['version']}")
        print(f"  Python 버전: {sys.version}")

        # 하드웨어 정보 (라즈베리파이에서만)
        try:
            import platform

            print(f"  플랫폼: {platform.platform()}")
            print(f"  아키텍처: {platform.architecture()[0]}")

            # 라즈베리파이 특정 정보
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "Model" in line:
                            print(f"  모델: {line.split(':')[1].strip()}")
                            break
            except:
                pass

        except Exception as e:
            print(f"  시스템 정보 가져오기 실패: {e}")

    def shutdown_system(self) -> None:
        """시스템 종료"""
        print("\n🔌 시스템을 종료합니다...")

        self.is_running = False

        if self.robot:
            # 자율주행 정지
            self.robot.stop_autonomous_driving()

            # 리소스 정리
            self.robot.cleanup()
            print("✅ 로봇 시스템이 안전하게 종료되었습니다.")

        print("👋 프로그램을 종료합니다. 안전한 하루 되세요!")

    def run(self) -> None:
        """메인 실행 루프"""
        try:
            # 로봇 초기화
            if not self.initialize_robot():
                print("❌ 로봇 초기화 실패로 프로그램을 종료합니다.")
                return

            self.is_running = True

            # 환영 메시지
            print("\n🎉 로봇이 준비되었습니다!")
            self.show_help_menu()

            # 사용자 입력 처리 스레드 시작
            self.user_input_thread = threading.Thread(
                target=self.handle_user_input, daemon=True
            )
            self.user_input_thread.start()

            # 메인 루프 (사용자 입력 스레드가 종료될 때까지 대기)
            while self.is_running:
                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n⚠️ Ctrl+C 감지 - 비상 정지")
            self.emergency_stop()
        except Exception as e:
            print(f"❌ 예상치 못한 오류 발생: {e}")
            self.emergency_stop()
        finally:
            self.shutdown_system()


def main():
    """메인 함수"""
    print("🤖 라즈베리파이 자율주행 로봇 시작")
    print("=" * 60)

    # 실행 환경 체크
    try:
        import RPi.GPIO as GPIO

        print("✅ 라즈베리파이 환경 감지")
    except ImportError:
        print("⚠️ 라즈베리파이가 아닌 환경에서 실행 중")
        print("   일부 기능이 제한될 수 있습니다.")

    # 메인 애플리케이션 실행
    app = RobotMainApplication()
    app.run()


if __name__ == "__main__":
    main()
