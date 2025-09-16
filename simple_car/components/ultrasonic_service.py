#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
초음파 센서 서비스 모듈
- 하드웨어 컨트롤러(`hardware.test_ultrasonic_sensor.UltrasonicSensor`) 래핑
"""

from typing import Optional

try:
    from hardware.test_ultrasonic_sensor import UltrasonicSensor
    _HARDWARE = True
except Exception:
    UltrasonicSensor = None  # type: ignore
    _HARDWARE = False


class UltrasonicSensorService:
    """초음파 센서 서비스 클래스"""

    def __init__(self) -> None:
        self.sensor: Optional[UltrasonicSensor] = None
        if _HARDWARE:
            try:
                self.sensor = UltrasonicSensor()
            except Exception:
                self.sensor = None

    def read_distance_cm(self) -> Optional[float]:
        if self.sensor is None:
            return None
        try:
            return self.sensor.measure_distance()
        except Exception:
            return None

    def cleanup(self) -> None:
        try:
            if self.sensor:
                self.sensor.cleanup()
        except Exception:
            pass


