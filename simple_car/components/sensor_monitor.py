#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
센서 모니터링 모듈
- 라인 센서 실시간 상태 표시
- 초음파 센서 거리 모니터링
- 센서 데이터 수집 및 표시
"""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .line_sensor_service import LineSensorService
    from .ultrasonic_service import UltrasonicSensorService
    from .config_service import ConfigurationService


class SensorMonitor:
    """센서 모니터링 담당 클래스"""

    def __init__(
        self,
        line_service: "LineSensorService",
        ultrasonic_service: "UltrasonicSensorService",
        config_service: "ConfigurationService",
    ):
        self.line = line_service
        self.ultrasonic = ultrasonic_service
        self.config = config_service

    def show_line_sensor_status(self, duration_seconds: int = 20) -> None:
        """라인 센서 상태 실시간 표시"""
        print("=" * 50)
        print(f"📍 라인 센서 상태 모니터링 ({duration_seconds}초간)")
        print("=" * 50)

        if not self.line or not getattr(self.line, "controller", None):
            print("시뮬레이션 모드 - 실제 센서 없음")
            print("=" * 50)
            return

        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            try:
                line_info = self.line.get_position_info()
                if isinstance(line_info, dict):
                    sensors = line_info.get("sensors", {})
                    left = sensors.get("left", False)
                    middle = sensors.get("middle", False)
                    right = sensors.get("right", False)
                    position = line_info.get("position")
                    pattern = line_info.get("pattern", "N/A")
                    description = line_info.get("description", "N/A")

                    print(
                        f"\r센서: L[{'●' if left else '○'}] M[{'●' if middle else '○'}] R[{'●' if right else '○'}] | "
                        f"위치: {position if position is not None else 'None':>5} | "
                        f"패턴: {pattern} | {description:15s}",
                        end="",
                        flush=True,
                    )
                else:
                    print(
                        f"\r센서 데이터 형식 오류: {type(line_info)}",
                        end="",
                        flush=True,
                    )

                time.sleep(0.2)
            except Exception as e:
                print(f"\r센서 읽기 오류: {e}", end="", flush=True)
                break

        print("\n" + "=" * 50)

    def show_distance_sensor_status(self, timeout_seconds: int = 10) -> None:
        """거리 센서 상태 실시간 표시"""
        print("=" * 50)
        print(f"📏 거리 센서 상태 모니터링 ({timeout_seconds}초간)")
        print("=" * 50)

        if not self.ultrasonic or not getattr(self.ultrasonic, "sensor", None):
            print("시뮬레이션 모드 - 실제 센서 없음")
            print("=" * 50)
            return

        start_time = time.time()
        distances = []

        while time.time() - start_time < timeout_seconds:
            try:
                distance = self.ultrasonic.read_distance_cm()
                if distance:
                    distances.append(distance)
                    # 최근 10개 평균 계산
                    avg_distance = sum(distances[-10:]) / len(distances[-10:])
                    status = (
                        "🚫 장애물!"
                        if distance < self.config.safe_distance
                        else "✅ 안전"
                    )

                    print(
                        f"\r현재 거리: {distance:5.1f}cm | 평균: {avg_distance:5.1f}cm | "
                        f"안전거리: {self.config.safe_distance}cm | {status}",
                        end="",
                        flush=True,
                    )
                else:
                    print(f"\r거리 측정 실패", end="", flush=True)

                time.sleep(0.3)
            except Exception as e:
                print(f"\r거리 센서 오류: {e}", end="", flush=True)
                break

        print("\n" + "=" * 50)

    def get_sensor_summary(self) -> str:
        """현재 센서 상태 요약 반환"""
        line_status = (
            "연결됨"
            if (self.line and getattr(self.line, "controller", None))
            else "시뮬레이션"
        )
        ultra_status = (
            "연결됨"
            if (self.ultrasonic and getattr(self.ultrasonic, "sensor", None))
            else "시뮬레이션"
        )

        return f"라인센서: {line_status}, 초음파센서: {ultra_status}"
