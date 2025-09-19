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
        """단일 거리 측정 (기본 함수)"""
        if self.sensor is None:
            return None
        try:
            return self.sensor.measure_distance()
        except Exception:
            return None

    def read_distance_fast(self, samples: int = 3) -> Optional[float]:
        """빠른 다중 샘플링으로 정확도 향상

        Args:
            samples: 측정 횟수 (기본 3회)

        Returns:
            중간값 또는 None
        """
        if self.sensor is None:
            return None

        measurements = []
        for _ in range(samples):
            try:
                distance = self.sensor.measure_distance()
                if distance is not None:
                    measurements.append(distance)
            except Exception:
                continue

        if not measurements:
            return None

        # 중간값 반환 (노이즈 제거)
        measurements.sort()
        return measurements[len(measurements) // 2]

    def read_distance_averaged(self, samples: int = 5) -> Optional[float]:
        """평균값 기반 안정적 측정

        Args:
            samples: 측정 횟수 (기본 5회)

        Returns:
            평균값 또는 None
        """
        if self.sensor is None:
            return None

        measurements = []
        for _ in range(samples):
            try:
                distance = self.sensor.measure_distance()
                if distance is not None and 2 <= distance <= 400:
                    measurements.append(distance)
            except Exception:
                continue

        if len(measurements) < samples // 2:  # 절반 이상 성공해야 유효
            return None

        return sum(measurements) / len(measurements)

    def cleanup(self) -> None:
        try:
            if self.sensor:
                self.sensor.cleanup()
        except Exception:
            pass
