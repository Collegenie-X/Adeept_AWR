#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
카메라 기반 자동 주행 로직 모듈
- 카메라 비전을 이용한 노란색 라인 추적
- 히스토그램 분석 기반 방향 판단
- 장애물 회피 로직 유지
"""

import time
import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .motor_service import MotorControlService
    from .ultrasonic_service import UltrasonicSensorService
    from .config_service import ConfigurationService
    from .manual_controller import ManualController
    from .camera_vision_service import CameraVisionService
    from .yellow_line_detector import YellowLineDetector


class CameraAutonomousDriver:
    """카메라 기반 자동 주행 로직 담당 클래스"""

    def __init__(
        self,
        motor_service: "MotorControlService",
        camera_service: "CameraVisionService",
        detector_service: "YellowLineDetector",
        ultrasonic_service: "UltrasonicSensorService",
        config_service: "ConfigurationService",
        manual_controller: Optional["ManualController"] = None,
    ):
        self.motor = motor_service
        self.camera = camera_service
        self.detector = detector_service
        self.ultrasonic = ultrasonic_service
        self.config = config_service
        self.manual = manual_controller

        # 상태 추적 변수
        self.last_turn_direction = "none"  # "left", "right", "none"
        self.last_camera_direction = "UP"
        self.consecutive_same_direction = 0
        
        # 히스테리시스 카운터 (방향 안정화)
        self._cnt_left = 0
        self._cnt_right = 0
        self._cnt_up = 0
        
        # 성능 모니터링
        self.frame_process_time = 0.0
        self.total_frames = 0

    def read_camera_direction(self) -> str:
        """카메라로부터 방향 정보 읽기"""
        if not self.camera or not self.camera.is_initialized:
            # 시뮬레이션 모드
            return random.choice(["LEFT", "RIGHT", "UP"])

        try:
            # 1단계: 프레임 캡처 (320x240)
            start_time = time.time()
            frame = self.camera.capture_frame()
            if frame is None:
                print("⚠️ Frame capture failed")
                return "UP"

            # 2단계: ROI 추출 (상위 영역)
            roi_frame = self.camera.extract_roi(frame)
            if roi_frame is None or roi_frame.size == 0:
                print("⚠️ ROI extraction failed")
                return "UP"

            # 3단계: 노란색 라인 감지 및 방향 판단
            result = self.detector.process_frame_for_direction(roi_frame)
            direction = result.get("direction", "UP")
            
            # 성능 측정
            self.frame_process_time = time.time() - start_time
            self.total_frames += 1
            
            # 디버그 정보 출력
            if self.total_frames % 30 == 0:  # 30프레임마다
                histogram_data = result.get("histogram_data", {})
                left_sum = histogram_data.get("left_sum", 0)
                right_sum = histogram_data.get("right_sum", 0)
                print(f"📷 Frame#{self.total_frames}: {direction} (L:{left_sum}, R:{right_sum}) - {self.frame_process_time:.3f}s")

            # 디버그 시각화 (설정된 경우)
            if self.detector.show_debug_windows:
                self.detector.visualize_detection(
                    roi_frame, 
                    result.get("yellow_mask"), 
                    result.get("histogram_data", {}), 
                    direction
                )

            return direction

        except Exception as e:
            print(f"❌ Camera direction reading error: {e}")
            return "UP"

    def read_distance(self) -> float:
        """초음파 센서로 거리 읽기 (기존 로직 유지)"""
        if not self.ultrasonic or not getattr(self.ultrasonic, "sensor", None):
            # 시뮬레이션 모드
            if random.random() < 0.1:  # 10% 장애물 확률
                return random.randint(5, self.config.safe_distance - 1)
            else:
                return random.randint(self.config.safe_distance + 10, 100)

        distance = self.ultrasonic.read_distance_cm()
        return distance if distance else 999

    def go_forward(self) -> None:
        """직진"""
        if self.manual:
            self.manual.drive_motion("forward")
        else:
            self.motor.set_speeds(
                self.config.forward_speed, self.config.forward_speed
            )
        print(f"📷 Forward at {self.config.forward_speed}%")

    def turn_left(self) -> None:
        """좌회전 (카메라 기준)"""
        if self.manual:
            self.manual.drive_motion("left")
        else:
            self.motor.set_speeds(self.config.high_turn_speed, -10)
        print("📷 Turn left")
        time.sleep(self.config.DEFAULT_TURN_HOLD_SECONDS)
        self.last_turn_direction = "left"

    def turn_right(self) -> None:
        """우회전 (카메라 기준)"""
        if self.manual:
            self.manual.drive_motion("right")
        else:
            self.motor.set_speeds(0, self.config.high_turn_speed + 10)
        print("📷 Turn right")
        time.sleep(self.config.DEFAULT_TURN_HOLD_SECONDS)
        self.last_turn_direction = "right"

    def slight_left(self) -> None:
        """약한 좌회전"""
        if self.manual:
            self.manual.drive_motion("slight_left")
        else:
            self.motor.set_speeds(self.config.forward_speed, self.config.low_turn_speed)
        print("📷 Slight left")
        self.last_turn_direction = "left"

    def slight_right(self) -> None:
        """약한 우회전"""
        if self.manual:
            self.manual.drive_motion("slight_right")
        else:
            self.motor.set_speeds(self.config.low_turn_speed, self.config.forward_speed)
        print("📷 Slight right")
        self.last_turn_direction = "right"

    def avoid_obstacle(self) -> None:
        """장애물 피하기 (좌회전 → 직진 → 우회전)"""
        avoid_time = self.config.get_avoid_time_seconds()
        print(f"📷 Obstacle avoidance started! (avoid time: {avoid_time:.1f}s)")

        # 1단계: 좌회전
        print("  1. Avoid by turning left")
        self.turn_left()
        time.sleep(avoid_time)

        # 2단계: 직진으로 지나가기
        print("  2. Go straight to pass")
        self.go_forward()
        time.sleep(avoid_time)

        # 3단계: 우회전으로 원래 방향
        print("  3. Turn right to return")
        self.turn_right()
        time.sleep(avoid_time)

        print("📷 Obstacle avoidance completed!")

    def drive_step(self) -> None:
        """한 스텝의 카메라 기반 자동 주행 로직 실행"""
        try:
            # 1) 장애물 확인 (선택적 활성화)
            # distance = self.read_distance()
            # if distance < self.config.safe_distance:
            #     print(f"🚫 장애물 감지 {distance}cm (안전거리: {self.config.safe_distance}cm)")
            #     self.avoid_obstacle()
            #     return

            # 2) 카메라 기반 차선 유지 로직
            direction = self.read_camera_direction()
            
            # 방향 변화 감지
            if direction != self.last_camera_direction:
                print(f"📷🛣️ Direction changed: {self.last_camera_direction} → {direction}")
                self.last_camera_direction = direction
                self.consecutive_same_direction = 0
            else:
                self.consecutive_same_direction += 1

            # 히스테리시스 카운터 업데이트 (방향 안정화)
            self._cnt_left = self._cnt_left + 1 if direction == "LEFT" else 0
            self._cnt_right = self._cnt_right + 1 if direction == "RIGHT" else 0
            self._cnt_up = self._cnt_up + 1 if direction == "UP" else 0

            # Early return 패턴으로 동작 결정
            if direction == "LEFT":
                # 안정화된 좌회전
                if self._cnt_left >= 2 or self.consecutive_same_direction >= 3:
                    self.turn_left()
                else:
                    self.slight_left()
                return

            if direction == "RIGHT":
                # 안정화된 우회전
                if self._cnt_right >= 2 or self.consecutive_same_direction >= 3:
                    self.turn_right()
                else:
                    self.slight_right()
                return

            # direction == "UP" (직진)
            self.go_forward()
            self.last_turn_direction = "none"

        except Exception as e:
            print(f"❌ Camera driving step error: {e}")
            # 오류 시 안전하게 직진
            self.go_forward()

    def get_status_info(self) -> dict:
        """현재 상태 정보 반환"""
        return {
            "last_turn_direction": self.last_turn_direction,
            "last_camera_direction": self.last_camera_direction,
            "consecutive_same_direction": self.consecutive_same_direction,
            "frame_process_time": self.frame_process_time,
            "total_frames": self.total_frames,
            "camera_initialized": self.camera.is_initialized if self.camera else False,
            "detector_debug": self.detector.debug_mode if self.detector else False
        }

    def set_debug_mode(self, debug: bool = True, show_windows: bool = False) -> None:
        """디버그 모드 설정"""
        if self.detector:
            self.detector.debug_mode = debug
            self.detector.show_debug_windows = show_windows
        print(f"📷 Debug mode: {debug}, Show windows: {show_windows}")

    def update_detection_params(self, **kwargs) -> None:
        """감지 파라미터 업데이트"""
        if self.detector:
            self.detector.set_detection_parameters(**kwargs)
            print(f"📷 Detection parameters updated: {kwargs}")

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            if self.camera:
                self.camera.cleanup()
            if self.detector:
                self.detector.cleanup()
            print("📷 Camera autonomous system cleanup completed")
        except Exception as e:
            print(f"⚠️ Camera system cleanup error: {e}")
