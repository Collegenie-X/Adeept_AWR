#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
수동 제어 모듈
- 키보드를 통한 수동 조작
- 조향 테스트 시퀀스
- 시간 제한 동작 제어
"""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .motor_service import MotorControlService
    from .line_sensor_service import LineSensorService
    from .config_service import ConfigurationService


class ManualController:
    """수동 제어 담당 클래스"""

    def __init__(
        self,
        motor_service: "MotorControlService",
        line_service: "LineSensorService",
        config_service: "ConfigurationService",
    ):
        self.motor = motor_service
        self.line = line_service
        self.config = config_service

    def get_line_sensor_snapshot(self, prefix: str = "센서") -> str:
        """라인 센서 스냅샷을 한 줄 텍스트로 반환"""
        try:
            if not self.line or not getattr(self.line, "controller", None):
                return f"{prefix}: 시뮬레이션 - 실제 센서 없음"

            info = self.line.get_position_info()
            if isinstance(info, dict):
                sensors = info.get("sensors", {})
                left = int(sensors.get("left", 1))
                middle = int(sensors.get("middle", 1))
                right = int(sensors.get("right", 1))
                pattern = info.get("pattern", f"{left}{middle}{right}")
                position = info.get("position")
            else:
                left = middle = right = 1
                pattern = "N/A"
                position = None

            # 간단한 상태 계산
            simple_status = "none"
            if middle == 0:
                simple_status = "center_line"
            elif left == 0 and right == 0:
                simple_status = "both_lines"
            elif left == 0:
                simple_status = "left_line"
            elif right == 0:
                simple_status = "right_line"

            return (
                f"{prefix}: 상태={simple_status} | "
                f"L[{'●' if left == 0 else '○'}] M[{'●' if middle == 0 else '○'}] R[{'●' if right == 0 else '○'}] | "
                f"패턴:{pattern} | 위치:{position if position is not None else 'None'}"
            )
        except Exception as e:
            return f"{prefix}: 센서 오류: {e}"

    def drive_motion(
        self, action: str, duration_seconds: float = None, label: str = "수동"
    ) -> None:
        """자동/수동 공용 모터 제어 함수"""
        try:
            # Early return for invalid action
            if action not in [
                "forward",
                "backward",
                "left",
                "right",
                "slight_left",
                "slight_right",
                "stop",
            ]:
                print(f"알 수 없는 동작: {action}")
                return

            # 동작 실행
            if action == "forward":
                self.motor.set_speeds(
                    self.config.forward_speed, self.config.forward_speed
                )
            elif action == "backward":
                self.motor.set_speeds(
                    -self.config.forward_speed, -self.config.forward_speed
                )
            elif action == "left":
                self.motor.set_speeds(self.config.high_turn_speed, -10)
            elif action == "right":
                self.motor.set_speeds(0, self.config.high_turn_speed)
                time.sleep(0.1)
            elif action == "slight_left":
                self.motor.set_speeds(self.config.high_turn_speed - 10, 0)
            elif action == "slight_right":
                self.motor.set_speeds(0, self.config.high_turn_speed - 10)
            elif action == "stop":
                self.motor.set_speeds(0, 0)

            # 지속 시간이 있으면 시간 제한 동작 (회전 동작은 회전 유지 시간 추가 고려)
            if duration_seconds is not None:
                print(self.get_line_sensor_snapshot(f"[{label} {action}-이전]"))
                hold_extra = 0.0
                if action in ("left", "right"):
                    hold_extra = max(0.0, self.config.get_turn_hold_seconds())
                time.sleep(duration_seconds + hold_extra)
                self.motor.set_speeds(0, 0)
                print(f"⏹️ {label} {action} 정지")
                print(self.get_line_sensor_snapshot(f"[{label} {action}-이후]"))

        except Exception as e:
            print(f"모터 제어 오류({action}): {e}")

    def manual_forward(self) -> None:
        """수동 전진 (설정된 시간 동작 후 자동 정지)"""
        if self.motor and getattr(self.motor, "controller", None):
            self.drive_motion(
                "forward", self.config.get_manual_pulse_seconds(), label="수동"
            )
        else:
            print(
                f"Simulation: Forward at {self.config.forward_speed}% for {self.config.get_manual_pulse_seconds()} second"
            )
            time.sleep(self.config.get_manual_pulse_seconds())
            print("Simulation: Forward stopped")

    def manual_backward(self) -> None:
        """수동 후진"""
        if self.motor and getattr(self.motor, "controller", None):
            self.drive_motion(
                "backward", self.config.get_manual_pulse_seconds(), label="수동"
            )
        else:
            print(
                f"Simulation: Backward at {self.config.forward_speed}% for {self.config.get_manual_pulse_seconds()} second"
            )
            time.sleep(self.config.get_manual_pulse_seconds())
            print("Simulation: Backward stopped")

    def manual_turn_left(self) -> None:
        """수동 좌회전"""
        if self.motor and getattr(self.motor, "controller", None):
            self.drive_motion(
                "left", self.config.get_manual_pulse_seconds(), label="수동"
            )
        else:
            print(
                f"Simulation: Turn left at {self.config.high_turn_speed}% for {self.config.get_manual_pulse_seconds()} second"
            )
            time.sleep(self.config.get_manual_pulse_seconds())
            print("Simulation: Turn left stopped")

    def manual_turn_right(self) -> None:
        """수동 우회전"""
        if self.motor and getattr(self.motor, "controller", None):
            self.drive_motion(
                "right", self.config.get_manual_pulse_seconds(), label="수동"
            )
        else:
            print(
                f"Simulation: Turn right at {self.config.high_turn_speed}% for {self.config.get_manual_pulse_seconds()} second"
            )
            time.sleep(self.config.get_manual_pulse_seconds())
            print("Simulation: Turn right stopped")

    def manual_slight_left(self) -> None:
        """수동 약한 좌회전"""
        if self.motor and getattr(self.motor, "controller", None):
            self.drive_motion(
                "slight_left", self.config.get_manual_pulse_seconds(), label="수동"
            )
        else:
            print(
                f"Simulation: Slight left at {self.config.high_turn_speed}% for {self.config.get_manual_pulse_seconds()} second"
            )
            time.sleep(self.config.get_manual_pulse_seconds())
            print("Simulation: Slight left stopped")

    def manual_slight_right(self) -> None:
        """수동 약한 우회전"""
        if self.motor and getattr(self.motor, "controller", None):
            self.drive_motion(
                "slight_right", self.config.get_manual_pulse_seconds(), label="수동"
            )
        else:
            print(
                f"Simulation: Slight right at {self.config.high_turn_speed}% for {self.config.get_manual_pulse_seconds()} second"
            )
            time.sleep(self.config.get_manual_pulse_seconds())
            print("Simulation: Slight right stopped")

    def test_steering_sequence(self) -> None:
        """조향 테스트: 좌→우→약좌→약우→전진→후진 순서로 각각 0.5s 동작"""
        sequence = [
            ("forward", 0.2),
            ("backward", 0.2),
            ("stop", 0.0),
            ("left", 0.2),
            ("right", 0.2),
            ("slight_left", 0.3),
            ("slight_right", 0.3),
            ("stop", 0.0),
        ]

        for action, duration in sequence:
            if duration > 0:
                self.drive_motion(action, duration, label="테스트")
            else:
                self.drive_motion(action)
            time.sleep(0.2)

    def emergency_stop(self) -> None:
        """긴급 정지 - 모든 모터 즉시 정지"""
        try:
            if self.motor and getattr(self.motor, "controller", None):
                self.motor.stop()
                print("✓ 모터 긴급 정지")
        except Exception:
            pass
