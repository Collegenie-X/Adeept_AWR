#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
기어 모터 제어 서비스 모듈
- 하드웨어 컨트롤러(`hardware.test_gear_motors.GearMotorController`)를 감싸
  간단한 API를 제공하여 상위 로직의 유지보수를 쉽게 함.
"""

from typing import Optional

try:
    from hardware.test_gear_motors import GearMotorController
    _HARDWARE = True
except Exception:
    GearMotorController = None  # type: ignore
    _HARDWARE = False


class MotorControlService:
    """모터 제어 서비스 클래스 (단순 API)

    - set_speeds(right, left): 양쪽 바퀴 속도 설정
    - stop(): 정지
    - cleanup(): 리소스 정리
    - 좌우 모터 출력 차이 보정 기능
    """

    def __init__(self) -> None:
        self.controller: Optional[GearMotorController] = None
        self._last_right: Optional[int] = None
        self._last_left: Optional[int] = None
        
        # 모터 출력 보정값 (기본값: 보정 없음)
        # 오른쪽이 강하면 right_correction을 음수로, 왼쪽이 강하면 양수로 설정
        self.right_correction = 0  # -10 ~ +10 범위 권장
        self.left_correction = 0   # -10 ~ +10 범위 권장

        if _HARDWARE:
            try:
                self.controller = GearMotorController()
            except Exception:
                self.controller = None

    def set_speeds(self, right_speed: int, left_speed: int) -> None:
        """양 바퀴 속도 설정 (보정값 적용 + 중복 전송 방지 캐시 포함)"""
        # 보정값 적용
        corrected_right = max(-100, min(100, right_speed + self.right_correction))
        corrected_left = max(-100, min(100, left_speed + self.left_correction))
        
        # Early return for simulation mode
        if self.controller is None:
            self._last_right, self._last_left = corrected_right, corrected_left
            return

        # Early return for duplicate speeds
        if corrected_right == self._last_right and corrected_left == self._last_left:
            return

        # 실제 모터 제어 (보정된 값 사용)
        self.controller.set_motor_speed("A", corrected_right)
        self.controller.set_motor_speed("B", corrected_left)
        self._last_right, self._last_left = corrected_right, corrected_left

    def stop(self) -> None:
        if self.controller:
            self.controller.motor_stop()
        self._last_right, self._last_left = 0, 0

    def set_motor_calibration(self, right_correction: int, left_correction: int) -> None:
        """모터 출력 보정값 설정 (-10 ~ +10 권장)"""
        self.right_correction = max(-20, min(20, right_correction))
        self.left_correction = max(-20, min(20, left_correction))
        print(f"✓ 모터 보정값 설정: 오른쪽={self.right_correction}, 왼쪽={self.left_correction}")

    def get_motor_calibration(self) -> tuple[int, int]:
        """현재 모터 보정값 반환 (right, left)"""
        return self.right_correction, self.left_correction

    def cleanup(self) -> None:
        try:
            if self.controller:
                self.controller.cleanup()
        except Exception:
            pass


