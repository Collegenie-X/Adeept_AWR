#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
설정 관리 서비스 모듈
- 속도, 거리, 시간 등 실시간 조절 가능한 설정값 관리
- 설정값 유효성 검증 및 범위 제한
"""

from typing import Dict, Any


class ConfigurationService:
    """자율주행차 설정 관리 클래스"""

    def __init__(self):
        # 기본 설정값 (상수)
        self.DEFAULT_FORWARD_SPEED = 60
        self.DEFAULT_LOW_TURN_SPEED = 30
        self.DEFAULT_HIGH_TURN_SPEED = 60
        self.DEFAULT_SAFE_DISTANCE = 15
        self.DEFAULT_AVOID_TIME = 0.6
        self.DEFAULT_MOTOR_SLEEP_TIME = 0.1
        self.DEFAULT_AUTO_LOOP_INTERVAL = 0.01
        self.DEFAULT_SLIGHT_TURN_THRESHOLD = 1
        self.DEFAULT_TURN_HOLD_SECONDS = 0.2
        self.DEFAULT_SLOW_FORWARD_DIVISOR = 2

        # 현재 설정값 (변경 가능)
        self.forward_speed = self.DEFAULT_FORWARD_SPEED
        self.low_turn_speed = self.DEFAULT_LOW_TURN_SPEED
        self.high_turn_speed = self.DEFAULT_HIGH_TURN_SPEED
        self.safe_distance = self.DEFAULT_SAFE_DISTANCE
        self.avoid_time_tenths = int(self.DEFAULT_AVOID_TIME * 10)  # 0.1초 단위
        self.manual_pulse_tenths = int(self.DEFAULT_MOTOR_SLEEP_TIME * 10)  # 0.1초 단위

        # 설정값 범위
        self.SPEED_MIN, self.SPEED_MAX = 10, 100
        self.DISTANCE_MIN, self.DISTANCE_MAX = 5, 50
        self.TIME_MIN, self.TIME_MAX = 1, 20  # 0.1초 단위

    def adjust_forward_speed(self, delta: int) -> int:
        """전진 속도 조절 (±10% 단위)"""
        self.forward_speed = max(
            self.SPEED_MIN, min(self.SPEED_MAX, self.forward_speed + delta)
        )
        return self.forward_speed

    def adjust_low_turn_speed(self, delta: int) -> int:
        """약한 회전 속도 조절"""
        self.low_turn_speed = max(
            self.SPEED_MIN, min(self.SPEED_MAX, self.low_turn_speed + delta)
        )
        return self.low_turn_speed

    def adjust_high_turn_speed(self, delta: int) -> int:
        """강한 회전 속도 조절"""
        self.high_turn_speed = max(
            self.SPEED_MIN, min(self.SPEED_MAX, self.high_turn_speed + delta)
        )
        return self.high_turn_speed

    def adjust_safe_distance(self, delta: int) -> int:
        """안전 거리 조절 (±5cm 단위)"""
        self.safe_distance = max(
            self.DISTANCE_MIN, min(self.DISTANCE_MAX, self.safe_distance + delta)
        )
        return self.safe_distance

    def adjust_avoid_time(self, delta: int) -> float:
        """회피 시간 조절 (±0.1초 단위)"""
        self.avoid_time_tenths = max(
            self.TIME_MIN, min(self.TIME_MAX, self.avoid_time_tenths + delta)
        )
        return self.avoid_time_tenths / 10.0

    def adjust_manual_pulse_time(self, delta: int) -> float:
        """수동 펄스 시간 조절 (±0.1초 단위)"""
        self.manual_pulse_tenths = max(
            self.TIME_MIN, min(self.TIME_MAX, self.manual_pulse_tenths + delta)
        )
        return self.manual_pulse_tenths / 10.0

    def get_avoid_time_seconds(self) -> float:
        """회피 시간을 초 단위로 반환"""
        return self.avoid_time_tenths / 10.0

    def get_manual_pulse_seconds(self) -> float:
        """수동 펄스 시간을 초 단위로 반환"""
        return self.manual_pulse_tenths / 10.0

    def get_turn_hold_seconds(self) -> float:
        """좌/우 회전 유지 시간을 초 단위로 반환"""
        return self.DEFAULT_TURN_HOLD_SECONDS

    def get_current_settings(self) -> Dict[str, Any]:
        """현재 설정값 딕셔너리 반환"""
        return {
            "forward_speed": self.forward_speed,
            "low_turn_speed": self.low_turn_speed,
            "high_turn_speed": self.high_turn_speed,
            "safe_distance": self.safe_distance,
            "avoid_time": self.get_avoid_time_seconds(),
            "motor_sleep_time": self.get_manual_pulse_seconds(),
            "auto_loop_interval": self.DEFAULT_AUTO_LOOP_INTERVAL,
            "slight_turn_threshold": self.DEFAULT_SLIGHT_TURN_THRESHOLD,
            "turn_hold_seconds": self.DEFAULT_TURN_HOLD_SECONDS,
            "slow_forward_divisor": self.DEFAULT_SLOW_FORWARD_DIVISOR,
        }

    def get_changed_settings(self) -> Dict[str, str]:
        """기본값에서 변경된 설정값 목록 반환"""
        changes = []

        if self.forward_speed != self.DEFAULT_FORWARD_SPEED:
            changes.append(
                f"전진속도: {self.DEFAULT_FORWARD_SPEED}% → {self.forward_speed}%"
            )
        if self.low_turn_speed != self.DEFAULT_LOW_TURN_SPEED:
            changes.append(
                f"약한회전: {self.DEFAULT_LOW_TURN_SPEED}% → {self.low_turn_speed}%"
            )
        if self.high_turn_speed != self.DEFAULT_HIGH_TURN_SPEED:
            changes.append(
                f"강한회전: {self.DEFAULT_HIGH_TURN_SPEED}% → {self.high_turn_speed}%"
            )
        if self.safe_distance != self.DEFAULT_SAFE_DISTANCE:
            changes.append(
                f"안전거리: {self.DEFAULT_SAFE_DISTANCE}cm → {self.safe_distance}cm"
            )
        if self.avoid_time_tenths != int(self.DEFAULT_AVOID_TIME * 10):
            changes.append(
                f"회피시간: {self.DEFAULT_AVOID_TIME:.1f}s → {self.get_avoid_time_seconds():.1f}s"
            )
        if self.manual_pulse_tenths != int(self.DEFAULT_MOTOR_SLEEP_TIME * 10):
            changes.append(
                f"수동펄스: {self.DEFAULT_MOTOR_SLEEP_TIME:.1f}s → {self.get_manual_pulse_seconds():.1f}s"
            )

        return changes

    def reset_to_defaults(self) -> None:
        """모든 설정을 기본값으로 초기화"""
        self.forward_speed = self.DEFAULT_FORWARD_SPEED
        self.low_turn_speed = self.DEFAULT_LOW_TURN_SPEED
        self.high_turn_speed = self.DEFAULT_HIGH_TURN_SPEED
        self.safe_distance = self.DEFAULT_SAFE_DISTANCE
        self.avoid_time_tenths = int(self.DEFAULT_AVOID_TIME * 10)
