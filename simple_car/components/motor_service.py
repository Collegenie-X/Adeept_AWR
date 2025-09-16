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
    """

    def __init__(self) -> None:
        self.controller: Optional[GearMotorController] = None
        self._last_right: Optional[int] = None
        self._last_left: Optional[int] = None

        if _HARDWARE:
            try:
                self.controller = GearMotorController()
            except Exception:
                self.controller = None

    def set_speeds(self, right_speed: int, left_speed: int) -> None:
        """양 바퀴 속도 설정 (중복 전송 방지 캐시 포함)"""
        # Early return for simulation mode
        if self.controller is None:
            self._last_right, self._last_left = right_speed, left_speed
            return

        # Early return for duplicate speeds
        if right_speed == self._last_right and left_speed == self._last_left:
            return

        # 실제 모터 제어
        self.controller.set_motor_speed("A", right_speed)
        self.controller.set_motor_speed("B", left_speed)
        self._last_right, self._last_left = right_speed, left_speed

    def stop(self) -> None:
        if self.controller:
            self.controller.motor_stop()
        self._last_right, self._last_left = 0, 0

    def cleanup(self) -> None:
        try:
            if self.controller:
                self.controller.cleanup()
        except Exception:
            pass


