#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
자동 주행 로직 모듈
- 라인 추적 알고리즘
- 장애물 회피 로직
- 방향 상태 추적 및 히스테리시스
"""

import time
import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .motor_service import MotorControlService
    from .line_sensor_service import LineSensorService
    from .ultrasonic_service import UltrasonicSensorService
    from .config_service import ConfigurationService
    from .manual_controller import ManualController


class AutonomousDriver:
    """자동 주행 로직 담당 클래스"""

    def __init__(
        self,
        motor_service: "MotorControlService",
        line_service: "LineSensorService",
        ultrasonic_service: "UltrasonicSensorService",
        config_service: "ConfigurationService",
        manual_controller: Optional["ManualController"] = None,
    ):
        self.motor = motor_service
        self.line = line_service
        self.ultrasonic = ultrasonic_service
        self.config = config_service
        self.manual = manual_controller

        # 상태 추적 변수
        self.last_turn_direction = "none"  # "left", "right", "none"
        self.turn_recovery_count = 0
        self.last_line_status = "none"

        # 히스테리시스 카운터
        self._cnt_left = 0
        self._cnt_right = 0
        self._cnt_center = 0
        self._cnt_none = 0
        self._cnt_both = 0

    def read_line_status(self) -> str:
        """라인 센서 상태를 간단한 문자열로 반환"""
        if not self.line or not getattr(self.line, "controller", None):
            # 시뮬레이션 모드
            return random.choice(["none", "left_line", "right_line", "center_line"])

        try:
            line_info = self.line.get_position_info()

            if isinstance(line_info, dict):
                sensors = line_info.get("sensors", {})
                left = int(sensors.get("left", 1))
                middle = int(sensors.get("middle", 1))
                right = int(sensors.get("right", 1))

                # LOW(0) = 노란 라인 감지
                # 우선순위: 양쪽(둘다) → 왼쪽 → 오른쪽 → 가운데 → 없음
                if left == 0 and right == 0:
                    return "both_lines"
                if left == 0:
                    return "left_line"
                if right == 0:
                    return "right_line"
                if middle == 0:
                    return "center_line"
                return "none"

            # fallback: 위치 기반
            position = line_info.get("position") if hasattr(line_info, "get") else None
            if position is None:
                return "none"
            if position <= -0.25:
                return "left_line"
            if position >= 0.25:
                return "right_line"
            return "center_line"

        except Exception as e:
            print(f"라인 센서 읽기 오류: {e}")
            return "none"

    def read_distance(self) -> float:
        """초음파 센서로 거리 읽기"""
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
            # self.motor.set_speeds(
            #     self.config.forward_speed, self.config.forward_speed
            # )
            self.manual.drive_motion("forward")
        else:
            self.motor.set_speeds(self.config.forward_speed, self.config.forward_speed)
        print(f"Forward at {self.config.forward_speed}%")

    def turn_left(self) -> None:
        """좌회전 (오른쪽 경계선에서 벗어나기)"""
        if self.manual:
            self.manual.drive_motion("left")
        else:
            self.motor.set_speeds(self.config.high_turn_speed, -10)
        print("Turn left")
        time.sleep(self.config.get_turn_hold_seconds())
        self.last_turn_direction = "left"
        self.turn_recovery_count = 0

    def turn_right(self) -> None:
        """우회전 (왼쪽 경계선에서 벗어나기)"""
        if self.manual:
            self.manual.drive_motion("right")
        else:
            self.motor.set_speeds(0, self.config.high_turn_speed + 10)
        print("Turn right")
        time.sleep(self.config.get_turn_hold_seconds())
        self.last_turn_direction = "right"
        self.turn_recovery_count = 0

    def handle_all_sensors_detected(self) -> None:
        """모든 센서 감지시 안정적 처리: 정지 → 후진 → 좌회전"""
        print("⚠️ 모든 센서 감지 - 안정적 처리 시작")

        # 1단계: 확실한 정지 (0.1초)
        print("1️⃣ 완전 정지 (0.1초)")
  
        self.motor.set_speeds(0, 0)
        time.sleep(0.1)


        # 2단계: 후진 (0.1초)
        print("2️⃣ 후진 이동 (0.1초)")
 
        self.motor.set_speeds(
            -self.config.forward_speed, -self.config.forward_speed
        )
        time.sleep(0.25)
        self.motor.set_speeds(0, 0)
        time.sleep(0.05)  # 안정화


        # 3단계: 좌회전 (제자리 회전)
        print("3️⃣ 좌회전 시작")
   
        self.motor.set_speeds(
            self.config.high_turn_speed+10,-20
        )
        time.sleep(0.3)
        self.motor.set_speeds(0, 0)

        time.sleep(0.05)  # 안정화
        print("✅ 모든 센서 감지 처리 완료")

        self.last_turn_direction = "left"
        self.turn_recovery_count = 0

    def slight_left(self) -> None:
        """약한 좌회전 (중앙선 회피용)"""
        if self.manual:
            self.manual.drive_motion("slight_left")
        else:
            self.motor.set_speeds(self.config.forward_speed, self.config.low_turn_speed)
        print("Slight left")
        self.last_turn_direction = "left"

    def slight_right(self) -> None:
        """약한 우회전 (중앙선 회피용)"""
        if self.manual:
            self.manual.drive_motion("slight_right")
        else:
            self.motor.set_speeds(self.config.low_turn_speed, self.config.forward_speed)
        print("Slight right")
        self.last_turn_direction = "right"

    def avoid_obstacle(self) -> None:
        """장애물 피하기 (좌회전 → 직진 → 우회전)"""
        avoid_time = self.config.get_avoid_time_seconds()
        print(f"Obstacle avoidance started! (avoid time: {avoid_time:.1f}s)")

        self.motor.set_speeds(0, 0)
        time.sleep(0.2)  # 안정화

        # 1단계: 좌회전
        print("  1. Avoid by turning left")
        self.motor.set_speeds(0,self.config.high_turn_speed+20)
        time.sleep(avoid_time)

        # 2단계: 직진으로 지나가기
        print("  2. Go straight to pass")
        self.go_forward()
        time.sleep(0.5)

        # self.motor.set_speeds(0, 0)
        # time.sleep(0.1)  # 안정화

        self.motor.set_speeds(self.config.high_turn_speed+10,0)
        time.sleep(avoid_time)

        print("Obstacle avoidance completed!")

    def drive_step(self) -> None:
        """한 스텝의 자동 주행 로직 실행"""
        # 1) 장애물 확인 (설정에 따라 on/off 가능)
        if self.config.is_ultrasonic_enabled():
            distance = self.read_distance()
            if distance < self.config.safe_distance:
                print(
                    f"🚫 장애물 감지 {distance:.1f}cm (안전거리: {self.config.safe_distance}cm)"
                )
                self.avoid_obstacle()
                return

        # 2) 차선 유지 로직
        # 먼저 원시 센서 패턴을 확인하여 좌+중앙/우+중앙 조합을 빠르게 처리
        if self.line and getattr(self.line, "controller", None):
            try:
                info = self.line.get_position_info()
                if isinstance(info, dict):
                    sensors = info.get("sensors", {})
                    left0 = int(sensors.get("left", 1)) == 0
                    mid0 = int(sensors.get("middle", 1)) == 0
                    right0 = int(sensors.get("right", 1)) == 0

                    # 좌+중앙 감지 → 약한 좌회전
                    if left0 and mid0 and not right0:
                        print("↙️ 좌+중앙 → 약좌")
                        self.turn_left()
                        time.sleep(0.2)
                        return

                    # 우+중앙 감지 → 약한 우회전
                    if right0 and mid0 and not left0:
                        print("↘️ 우+중앙 → 약우")
                        self.turn_right()
                        time.sleep(0.2)
                        return

                    raw_checked = True
            except Exception:
                pass

        # 원시 패턴에서 처리되지 않았다면 간단 상태 기반으로 진행
        status = self.read_line_status()

        if status != self.last_line_status:
            print(f"🛣️ 라인 상태: {status}, 이전 방향: {self.last_turn_direction}")
            self.last_line_status = status

        # 카운터 업데이트 (히스테리시스)
        self._cnt_left = self._cnt_left + 1 if status == "left_line" else 0
        self._cnt_right = self._cnt_right + 1 if status == "right_line" else 0
        self._cnt_center = self._cnt_center + 1 if status == "center_line" else 0
        self._cnt_both = self._cnt_both + 1 if status == "both_lines" else 0
        self._cnt_none = self._cnt_none + 1 if status == "none" else 0

        # Early return 패턴으로 동작 결정
        if status == "left_line":
            # 직진하면 좌측 차선을 밟으므로 우측으로 이동
            if self._cnt_left >= self.config.DEFAULT_SLIGHT_TURN_THRESHOLD:
                self.turn_right()

            else:
                self.turn_right()
            return

        if status == "right_line":
            if self._cnt_right >= self.config.DEFAULT_SLIGHT_TURN_THRESHOLD:
                self.turn_left()
            else:
                self.turn_left()
            return

        if status == "center_line":
            # 요구사항: 가운데는 좌 그룹으로 간주 → 좌로 동작
            self.go_forward()
            return

        if status == "both_lines":
            # 요구사항: 모두 인식 시 안정적 처리 (정지→후진→좌회전)
            self.handle_all_sensors_detected()
            return

        # none: 둘 다 감지되지 않음 → 직진 유지
        self.go_forward()
        # time.sleep(self.config.DEFAULT_MOTOR_SLEEP_TIME)
        self.last_turn_direction = "none"
        self.turn_recovery_count = 0
