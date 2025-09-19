#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenCV 카메라 기반 자율 주행차 - 메인 컨트롤러
Camera-based Autonomous Car with OpenCV - Main Controller

기능:
1. 카메라로 노란색 라인 감지 및 추적
2. 히스토그램 분석을 통한 방향 판단 (좌/우/직진)
3. 초음파 센서로 장애물 피하기 (선택적)
4. 키보드로 실시간 속도 및 파라미터 조절

모듈형 설계:
- CameraVisionService: 카메라 제어 및 이미지 처리
- YellowLineDetector: 노란색 라인 감지 및 방향 판단
- CameraAutonomousDriver: 카메라 기반 자동 주행 로직
- 기존 ultra_simple_car.py의 나머지 기능 그대로 유지
"""

import time
import threading
import os
import sys
import termios
import cv2

# 하드웨어/컴포넌트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 컴포넌트 서비스 임포트 (모듈형)
from simple_car.components import (
    MotorControlService,
    UltrasonicSensorService,
    KeyboardInputService,
    ConfigurationService,
    MenuService,
    ManualController,
    SensorMonitor,
    CameraVisionService,
    YellowLineDetector,
    CameraAutonomousDriver,
)


class OpenCVCarController:
    """OpenCV 카메라 기반 자율주행차 메인 컨트롤러"""

    def __init__(self):
        # 기본 서비스 초기화
        self.config = ConfigurationService()
        self.keyboard = KeyboardInputService()

        # 하드웨어 서비스
        self.motor_service = MotorControlService()
        self.ultrasonic_service = UltrasonicSensorService()

        # 카메라 비전 서비스
        self.camera_service = CameraVisionService(camera_id=0, width=320, height=240)
        self.detector_service = YellowLineDetector()

        # 기능별 컨트롤러
        self.menu = MenuService(self.config)
        self.manual_controller = ManualController(
            self.motor_service, None, self.config  # LineSensorService 대신 None
        )
        self.auto_driver = CameraAutonomousDriver(
            self.motor_service,
            self.camera_service,
            self.detector_service,
            self.ultrasonic_service,
            self.config,
            manual_controller=self.manual_controller,
        )
        self.sensor_monitor = SensorMonitor(
            None, self.ultrasonic_service, self.config  # LineSensorService 대신 None
        )

        # 상태 변수
        self.autonomous_mode = False
        self.running = True
        self.manual_control_active = False
        self.debug_mode = False

    def setup(self) -> bool:
        """서비스 준비 상태 확인"""
        try:
            # 카메라 초기화
            print("🔧 Attempting camera initialization...")
            camera_ready = self.camera_service.initialize_camera()
            if not camera_ready:
                print("❌ Camera initialization failed")
                print("🔍 Checking available cameras...")
                self._check_available_cameras()
                print("⚠️ Running in simulation mode without camera")
                camera_ready = False  # Continue without camera

            # 하드웨어 연결 상태 확인
            hw_motor = getattr(self.motor_service, "controller", None) is not None
            hw_ultra = getattr(self.ultrasonic_service, "sensor", None) is not None

            camera_status = "✅" if camera_ready else "❌(simulation)"
            print(f"Hardware(camera={camera_status}, motor={hw_motor}, ultrasonic={hw_ultra}) ready")
            
            if camera_ready:
                print(f"📷 Camera: {self.camera_service.width}x{self.camera_service.height}")
            else:
                print("📷 Camera: Simulation mode (no physical camera)")
                
            print(f"🎯 Detection: Yellow line tracking with histogram analysis")
            
            return True  # Continue even without camera
        except Exception as e:
            print(f"Hardware setup error: {e}")
            return False
    
    def _check_available_cameras(self) -> None:
        """사용 가능한 카메라 확인"""
        import cv2
        print("📹 Scanning for available cameras...")
        available_cameras = []
        
        for i in range(5):  # Check cameras 0-4
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
        
        if available_cameras:
            print(f"📹 Available cameras: {available_cameras}")
        else:
            print("📹 No cameras detected")
            print("💡 Tips:")
            print("   - Check if camera is connected")
            print("   - Try: sudo modprobe uvcvideo")
            print("   - Check permissions: sudo usermod -a -G video $USER")

    def handle_keyboard_input(self) -> None:
        """키보드 입력 처리 스레드"""
        print("\n🎮 Keyboard control activated - Keys respond immediately")
        print("Only 's' command needs Enter key, others respond instantly")
        print("Additional features: 'v' (vision debug), 'c' (camera settings)")
        print("Ctrl+C for safe shutdown")

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
                if not self._handle_camera_keys(key):  # 새로 추가
                    continue
                if not self._handle_manual_movement_keys(key):
                    continue

                # 알 수 없는 키
                if key and key.isprintable():
                    print(f"\n❌ Unknown command: '{key}'. Press 'h' for help")

            except KeyboardInterrupt:
                print("\nCtrl+C detected - Safe shutdown in progress...")
                self.running = False
                break
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(0.1)

    def _handle_control_keys(self, key: str) -> bool:
        """제어 키 처리 (h, q, Enter, space/p)"""
        if key == "h":
            print("\n")
            self.menu.print_control_menu()
            self._print_camera_control_menu()  # 카메라 관련 메뉴 추가
            return False
        elif key == "q":
            print("\n🚪 Program shutdown requested")
            self.menu.print_final_settings()
            self._print_camera_final_settings()  # 카메라 설정 출력
            self.running = False
            return False
        elif key == "\n":
            if not self.autonomous_mode:
                print("\n📷 Camera-based autonomous driving started")
                self.autonomous_mode = True
                self.manual_control_active = False
            else:
                print("\nAlready in autonomous mode")
            return False
        elif key in ["p", "space"]:
            print("\n🛑 Emergency stop - All operations halted")
            self.manual_controller.emergency_stop()
            if self.autonomous_mode:
                self.autonomous_mode = False
                self.manual_control_active = True
                print("Autonomous mode → Manual mode switched")
            else:
                self.manual_control_active = True
                print("All operations stopped in manual mode")
            return False
        elif key == "\x03":  # Ctrl+C
            print("\nCtrl+C detected - Safe shutdown in progress...")
            self.running = False
            return False
        return True

    def _handle_speed_adjustment_keys(self, key: str) -> bool:
        """속도 조절 키 처리 (기존과 동일)"""
        if key == "1":
            speed = self.config.adjust_forward_speed(-10)
            print(f"\n✓ Forward speed: {speed}%")
        elif key == "2":
            speed = self.config.adjust_forward_speed(10)
            print(f"\n✓ Forward speed: {speed}%")
        elif key == "3":
            speed = self.config.adjust_low_turn_speed(-10)
            print(f"\n✓ Low turn speed: {speed}%")
        elif key == "4":
            speed = self.config.adjust_low_turn_speed(10)
            print(f"\n✓ Low turn speed: {speed}%")
        elif key == "5":
            speed = self.config.adjust_high_turn_speed(-10)
            print(f"\n✓ High turn speed: {speed}%")
        elif key == "6":
            speed = self.config.adjust_high_turn_speed(10)
            print(f"\n✓ High turn speed: {speed}%")
        elif key == "7":
            distance = self.config.adjust_safe_distance(-5)
            print(f"\n✓ Safe distance: {distance}cm")
        elif key == "8":
            distance = self.config.adjust_safe_distance(5)
            print(f"\n✓ Safe distance: {distance}cm")
        elif key == "9":
            time_val = self.config.adjust_avoid_time(-1)
            print(f"\n✓ Avoidance time: {time_val:.1f}s")
        elif key == "0":
            time_val = self.config.adjust_avoid_time(1)
            print(f"\n✓ Avoidance time: {time_val:.1f}s")
        else:
            return True  # 처리하지 않은 키
        return False

    def _handle_debug_keys(self, key: str) -> bool:
        """디버깅 키 처리 (기존 + 카메라)"""
        if key == "z":
            print("\n🔍 Checking distance sensor status...")
            self.sensor_monitor.show_distance_sensor_status(5)
        elif key == "t":
            print("\n🧪 Starting steering test sequence")
            self.manual_controller.test_steering_sequence()
        else:
            return True  # 처리하지 않은 키
        return False

    def _handle_camera_keys(self, key: str) -> bool:
        """카메라 관련 키 처리 (새로 추가)"""
        if key == "v":
            # 비전 디버그 모드 토글
            self.debug_mode = not self.debug_mode
            self.auto_driver.set_debug_mode(self.debug_mode, self.debug_mode)
            print(f"\n📷 Vision debug mode: {'ON' if self.debug_mode else 'OFF'}")
            if self.debug_mode:
                print("  - Processing time, histogram data output")
                print("  - Detection result visualization in OpenCV windows")
            return False
        elif key == "c":
            # 카메라 상태 정보 출력
            print("\n📷 Camera system status:")
            camera_info = self.camera_service.get_camera_info()
            for k, v in camera_info.items():
                print(f"  {k}: {v}")
            
            detector_info = self.detector_service.get_detection_info()
            print("\n🎯 Detection settings:")
            for k, v in detector_info.items():
                print(f"  {k}: {v}")
                
            status_info = self.auto_driver.get_status_info()
            print("\n🚗 Driving status:")
            for k, v in status_info.items():
                print(f"  {k}: {v}")
            return False
        elif key == "n":
            # 노란색 감지 임계값 조정 (예시)
            threshold = getattr(self.detector_service, 'direction_threshold', 50000)
            threshold -= 10000
            self.detector_service.direction_threshold = max(1000, threshold)
            print(f"\n🎯 Direction threshold: {self.detector_service.direction_threshold}")
            return False
        elif key == "m":
            # 노란색 감지 임계값 증가 (예시)
            threshold = getattr(self.detector_service, 'direction_threshold', 50000)
            threshold += 10000
            self.detector_service.direction_threshold = min(200000, threshold)
            print(f"\n🎯 Direction threshold: {self.detector_service.direction_threshold}")
            return False
        else:
            return True  # 처리하지 않은 키
        return False

    def _handle_manual_movement_keys(self, key: str) -> bool:
        """수동 이동 키 처리 (기존과 동일)"""
        if (
            key in ["w", "a", "d", "s", "j", "k", "up", "down", "left", "right"]
            and not self.autonomous_mode
        ):
            self.manual_control_active = True
            if key in ["w", "up"]:
                print("\n🔼 Manual forward")
                self.manual_controller.manual_forward()
            elif key in ["s", "down"]:
                print("\n🔽 Manual backward")
                self.manual_controller.manual_backward()
            elif key in ["a", "left"]:
                print("\n◀️ Manual left turn")
                self.manual_controller.manual_turn_left()
            elif key in ["d", "right"]:
                print("\n▶️ Manual right turn")
                self.manual_controller.manual_turn_right()
            elif key in ["k"]:
                print("\n▶️ Manual slight right turn")
                self.manual_controller.manual_slight_right()
            elif key in ["j"]:
                print("\n◀️ Manual slight left turn")
                self.manual_controller.manual_slight_left()
            return False
        return True

    def _print_camera_control_menu(self) -> None:
        """카메라 관련 제어 메뉴 출력"""
        print("\n📷 === Camera Control === ")
        print("  v     : Vision debug mode ON/OFF")
        print("  c     : Check camera system status")
        print("  n/m   : Adjust direction threshold (-/+)")

    def _print_camera_final_settings(self) -> None:
        """최종 카메라 설정 출력"""
        print("\n📷 Camera Settings:")
        camera_info = self.camera_service.get_camera_info()
        print(f"  Resolution: {camera_info['width']}x{camera_info['height']}")
        print(f"  Brightness: {camera_info['brightness']}")
        print(f"  Contrast: {camera_info['contrast']}")
        
        detector_info = self.detector_service.get_detection_info()
        print(f"  Direction threshold: {detector_info['direction_threshold']}")
        print(f"  Debug mode: {detector_info['debug_mode']}")

    def cleanup(self) -> None:
        """완전 초기화 - Ctrl+C 시 안전한 종료"""
        try:
            print("\n🛑 Safe shutdown in progress...")

            # 상태 초기화
            self.running = False
            self.autonomous_mode = False
            self.manual_control_active = False

            # 긴급 정지
            self.manual_controller.emergency_stop()

            # 현재 설정값 표시
            self.menu.print_final_settings()
            self._print_camera_final_settings()

            # 터미널 설정 복원
            try:
                termios.tcsetattr(
                    sys.stdin, termios.TCSADRAIN, termios.tcgetattr(sys.stdin)
                )
            except:
                pass

            # 하드웨어 정리
            self._cleanup_hardware()

            print("✅ Safe shutdown completed")

        except Exception as e:
            print(f"⚠️ Shutdown error: {e}")
        finally:
            print("\n")

    def _cleanup_hardware(self) -> None:
        """하드웨어 서비스 정리"""
        services = [
            (self.motor_service, "Motor Controller"),
            (self.ultrasonic_service, "Ultrasonic Sensor"),
            (self.camera_service, "Camera Service"),
            (self.detector_service, "Line Detector"),
            (self.auto_driver, "Autonomous Driving System"),
        ]

        for service, name in services:
            try:
                if service and hasattr(service, "cleanup"):
                    service.cleanup()
                    print(f"✓ {name} cleaned up")
            except:
                pass

    def run(self) -> None:
        """메인 실행 함수"""
        print("OpenCV Camera-based Autonomous Car - Yellow Line Tracking")
        print("=" * 70)
        print("🛣️ Road: Black / Line: Yellow")
        print("📷 Sensor: OpenCV Camera (320x240)")
        print("🎯 Functions: Yellow line tracking + Obstacle avoidance + Keyboard control")
        print("🔧 Algorithm: Histogram analysis-based direction detection")
        print("=" * 70)

        settings = self.config.get_current_settings()
        print("Initial Settings:")
        print(f"  🚗 Forward speed: {settings['forward_speed']}%")
        print(
            f"  🔄 Turn speed: Low={settings['low_turn_speed']}%, High={settings['high_turn_speed']}%"
        )
        print(f"  🛡️ Safe distance: {settings['safe_distance']}cm")
        print(f"  ⏱️ Avoidance time: {settings['avoid_time']}s")
        print("=" * 70)

        if not self.setup():
            print("Setup failed")
            return

        try:
            print("\n🎮 Keyboard control mode started")
            print("Press 'h' key to check control methods")

            # 제어 가이드 출력
            self.menu.print_control_menu()
            self._print_camera_control_menu()

            # 키보드 입력 스레드 시작
            keyboard_thread = threading.Thread(
                target=self.handle_keyboard_input, daemon=True
            )
            keyboard_thread.start()

            # 메인 루프
            while self.running:
                try:
                    if self.autonomous_mode:
                        # 카메라 기반 자동 주행 모드
                        self.auto_driver.drive_step()
                        time.sleep(self.config.DEFAULT_AUTO_LOOP_INTERVAL)
                    else:
                        # 수동 모드 - 키보드 입력만 처리
                        time.sleep(0.02)
                        
                    # OpenCV 이벤트 처리 (디버그 윈도우용)
                    if self.debug_mode:
                        cv2.waitKey(1)  # OpenCV 윈도우 업데이트
                        
                except KeyboardInterrupt:
                    print("\n\n⚠️ Ctrl+C detected - Emergency stop in progress...")
                    self.manual_controller.emergency_stop()
                    self.running = False
                    break

        except KeyboardInterrupt:
            print("\n\n⚠️ Ctrl+C detected - Safe shutdown in progress...")
            self.manual_controller.emergency_stop()
            self.running = False
        except Exception as e:
            print(f"\n❌ Error occurred: {e}")
            self.manual_controller.emergency_stop()
            self.running = False
        finally:
            # 항상 완전 초기화 실행
            self.cleanup()
            print("🏁 Program completely terminated")


def main():
    """메인 함수"""
    controller = OpenCVCarController()
    controller.run()


if __name__ == "__main__":
    main()
