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
        self.DEFAULT_FORWARD_SPEED = 40
        self.DEFAULT_LOW_TURN_SPEED = 20
        self.DEFAULT_HIGH_TURN_SPEED = 50
        self.DEFAULT_SAFE_DISTANCE = 25
        self.DEFAULT_AVOID_TIME = 1
        self.DEFAULT_MOTOR_SLEEP_TIME = 0.05
        self.DEFAULT_AUTO_LOOP_INTERVAL = 0.1
        self.DEFAULT_SLIGHT_TURN_THRESHOLD = 1
        self.DEFAULT_TURN_HOLD_SECONDS = 0.25
        self.DEFAULT_SLOW_FORWARD_DIVISOR = 2

        # 장애물 회피 관련 설정값
        self.DEFAULT_OBSTACLE_AVOID_SPEED = 60  # 장애물 회피 회전 속도
        self.DEFAULT_OBSTACLE_AVOID_TIME = 1.5  # 장애물 회피 회전 시간
        self.DEFAULT_OBSTACLE_FORWARD_TIME = 1.0  # 장애물 회피 후 전진 시간
        self.DEFAULT_EARLY_DETECTION_DISTANCE = 40  # 조기 감지 거리 (더 먼 거리)
        self.DEFAULT_WARNING_DISTANCE = 35  # 경고 거리 (속도 감소)
        self.DEFAULT_CRITICAL_DISTANCE = 25  # 위험 거리 (즉시 회피, 기존 safe_distance)

        # 현재 설정값 (변경 가능)
        self.forward_speed = self.DEFAULT_FORWARD_SPEED
        self.low_turn_speed = self.DEFAULT_LOW_TURN_SPEED
        self.high_turn_speed = self.DEFAULT_HIGH_TURN_SPEED
        self.safe_distance = self.DEFAULT_SAFE_DISTANCE
        self.avoid_time_tenths = int(self.DEFAULT_AVOID_TIME * 10)  # 0.1초 단위
        self.manual_pulse_tenths = int(self.DEFAULT_MOTOR_SLEEP_TIME * 10)  # 0.1초 단위

        # 장애물 회피 관련 현재 설정값
        self.obstacle_avoid_speed = self.DEFAULT_OBSTACLE_AVOID_SPEED
        self.obstacle_avoid_time = self.DEFAULT_OBSTACLE_AVOID_TIME
        self.obstacle_forward_time = self.DEFAULT_OBSTACLE_FORWARD_TIME
        self.early_detection_distance = self.DEFAULT_EARLY_DETECTION_DISTANCE
        self.warning_distance = self.DEFAULT_WARNING_DISTANCE
        self.critical_distance = self.DEFAULT_CRITICAL_DISTANCE

        # 회전 유지 시간 (조절 가능)
        self.turn_hold_seconds = self.DEFAULT_TURN_HOLD_SECONDS

        # 초음파 센서 on/off 설정
        self.ultrasonic_enabled = True  # 기본값: 활성화

        # 적응형 라인 팔로잉 설정
        self.DEFAULT_MICRO_TURN_TIME = 0.08  # 미세 조정 (중앙 근처)
        self.DEFAULT_SLIGHT_TURN_TIME = 0.12  # 약한 회전 (약간 벗어남)
        self.DEFAULT_NORMAL_TURN_TIME = 0.18  # 보통 회전 (많이 벗어남)
        self.DEFAULT_STRONG_TURN_TIME = 0.25  # 강한 회전 (완전 이탈)

        # 적응형 회전 시간 (조절 가능)
        self.micro_turn_time = self.DEFAULT_MICRO_TURN_TIME
        self.slight_turn_time = self.DEFAULT_SLIGHT_TURN_TIME
        self.normal_turn_time = self.DEFAULT_NORMAL_TURN_TIME
        self.strong_turn_time = self.DEFAULT_STRONG_TURN_TIME

        # 설정값 범위
        self.SPEED_MIN, self.SPEED_MAX = 10, 100
        self.DISTANCE_MIN, self.DISTANCE_MAX = 5, 50
        self.TIME_MIN, self.TIME_MAX = 1, 20  # 0.1초 단위
        self.TURN_HOLD_MIN, self.TURN_HOLD_MAX = 0.1, 0.5  # 회전 시간 범위

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

    def adjust_turn_hold_time(self, delta_hundredths: int) -> float:
        """회전 유지 시간 조절 (±0.05초 단위)

        Args:
            delta_hundredths: 변경량 (1 = +0.05초, -1 = -0.05초)

        Returns:
            조절된 회전 시간 (초)
        """
        # 0.05초 단위로 조절
        delta_seconds = delta_hundredths * 0.05
        new_time = self.turn_hold_seconds + delta_seconds

        # 범위 제한 (0.1 ~ 0.5초)
        self.turn_hold_seconds = max(
            self.TURN_HOLD_MIN, min(self.TURN_HOLD_MAX, new_time)
        )
        return self.turn_hold_seconds

    def get_avoid_time_seconds(self) -> float:
        """회피 시간을 초 단위로 반환"""
        return self.avoid_time_tenths / 10.0

    def get_manual_pulse_seconds(self) -> float:
        """수동 펄스 시간을 초 단위로 반환"""
        return self.manual_pulse_tenths / 10.0

    def get_turn_hold_seconds(self) -> float:
        """좌/우 회전 유지 시간을 초 단위로 반환"""
        return self.turn_hold_seconds

    def toggle_ultrasonic_sensor(self) -> bool:
        """초음파 센서 on/off 토글

        Returns:
            토글 후 상태 (True: 활성화, False: 비활성화)
        """
        self.ultrasonic_enabled = not self.ultrasonic_enabled
        return self.ultrasonic_enabled

    def is_ultrasonic_enabled(self) -> bool:
        """초음파 센서 활성화 상태 확인

        Returns:
            True: 활성화, False: 비활성화
        """
        return self.ultrasonic_enabled

    def get_adaptive_turn_time(self, line_position: str) -> float:
        """라인 위치에 따른 적응형 회전 시간 반환

        Args:
            line_position: "center", "slight_off", "far_off", "lost"

        Returns:
            적절한 회전 시간 (초)
        """
        position_map = {
            "center": self.micro_turn_time,  # 중앙 - 미세 조정
            "slight_off": self.slight_turn_time,  # 약간 벗어남 - 약한 회전
            "far_off": self.normal_turn_time,  # 많이 벗어남 - 보통 회전
            "lost": self.strong_turn_time,  # 라인 이탈 - 강한 회전
        }
        return position_map.get(line_position, self.normal_turn_time)

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
            "slow_forward_divisor": self.DEFAULT_SLOW_FORWARD_DIVISOR,
            "obstacle_avoid_speed": self.obstacle_avoid_speed,
            "obstacle_avoid_time": self.obstacle_avoid_time,
            "obstacle_forward_time": self.obstacle_forward_time,
            "early_detection_distance": self.early_detection_distance,
            "warning_distance": self.warning_distance,
            "critical_distance": self.critical_distance,
            "turn_hold_seconds": self.turn_hold_seconds,
            "ultrasonic_enabled": self.ultrasonic_enabled,
            "micro_turn_time": self.micro_turn_time,
            "slight_turn_time": self.slight_turn_time,
            "normal_turn_time": self.normal_turn_time,
            "strong_turn_time": self.strong_turn_time,
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
        if abs(self.turn_hold_seconds - self.DEFAULT_TURN_HOLD_SECONDS) > 0.001:
            changes.append(
                f"회전시간: {self.DEFAULT_TURN_HOLD_SECONDS:.2f}s → {self.turn_hold_seconds:.2f}s"
            )

        return changes

    def reset_to_defaults(self) -> None:
        """모든 설정을 기본값으로 초기화"""
        self.forward_speed = self.DEFAULT_FORWARD_SPEED
        self.low_turn_speed = self.DEFAULT_LOW_TURN_SPEED
        self.high_turn_speed = self.DEFAULT_HIGH_TURN_SPEED
        self.safe_distance = self.DEFAULT_SAFE_DISTANCE
        self.avoid_time_tenths = int(self.DEFAULT_AVOID_TIME * 10)
        self.manual_pulse_tenths = int(self.DEFAULT_MOTOR_SLEEP_TIME * 10)
        self.obstacle_avoid_speed = self.DEFAULT_OBSTACLE_AVOID_SPEED
        self.obstacle_avoid_time = self.DEFAULT_OBSTACLE_AVOID_TIME
        self.obstacle_forward_time = self.DEFAULT_OBSTACLE_FORWARD_TIME
        self.early_detection_distance = self.DEFAULT_EARLY_DETECTION_DISTANCE
        self.warning_distance = self.DEFAULT_WARNING_DISTANCE
        self.critical_distance = self.DEFAULT_CRITICAL_DISTANCE
        self.turn_hold_seconds = self.DEFAULT_TURN_HOLD_SECONDS
        self.ultrasonic_enabled = True  # 기본값: 활성화
        self.micro_turn_time = self.DEFAULT_MICRO_TURN_TIME
        self.slight_turn_time = self.DEFAULT_SLIGHT_TURN_TIME
        self.normal_turn_time = self.DEFAULT_NORMAL_TURN_TIME
        self.strong_turn_time = self.DEFAULT_STRONG_TURN_TIME
