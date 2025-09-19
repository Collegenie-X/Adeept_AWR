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
    from .ultrasonic_service import UltrasonicSensorService


class ManualController:
    """수동 제어 담당 클래스"""

    def __init__(
        self,
        motor_service: "MotorControlService",
        line_service: "LineSensorService",
        config_service: "ConfigurationService",
        ultrasonic_service: "UltrasonicSensorService" = None,
    ):
        self.motor = motor_service
        self.line = line_service
        self.config = config_service
        self.ultrasonic = ultrasonic_service

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
                self.motor.set_speeds(0, self.config.high_turn_speed+5)
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

    def test_obstacle_avoidance_sequence(self) -> None:
        """개선된 장애물 회피 기능 테스트 시퀀스"""
        print("🧪 개선된 장애물 회피 기능 테스트 시작")
        print("=" * 60)

        # 1. 현재 거리 측정 및 상태 분석 테스트
        distance = self.check_obstacle_distance()
        status, _ = self.get_obstacle_status()
        print(f"1️⃣ 현재 거리: {distance:.1f}cm, 상태: {status}")
        print(f"   - 조기감지: {self.config.early_detection_distance}cm")
        print(f"   - 경고: {self.config.warning_distance}cm")
        print(f"   - 위험: {self.config.critical_distance}cm")
        time.sleep(1)

        # 2. 장애물 감지 테스트
        is_detected = self.is_obstacle_detected()
        print(f"2️⃣ 장애물 감지: {'예' if is_detected else '아니오'}")
        time.sleep(1)

        # 3. 제자리 좌회전 회피 테스트
        print("3️⃣ 제자리 좌회전 회피 테스트 (0.1초 정지 후 회전)")
        self.obstacle_avoid_left(forward_after=False)
        time.sleep(1)

        # 4. 제자리 우회전 회피 테스트
        print("4️⃣ 제자리 우회전 회피 테스트 (0.1초 정지 후 회전)")
        self.obstacle_avoid_right(forward_after=False)
        time.sleep(1)

        # 5. 자동 장애물 회피 테스트
        print("5️⃣ 자동 장애물 회피 테스트 (조기 감지 포함)")
        self.auto_obstacle_avoid("left")
        time.sleep(1)

        # 6. 안전 전진 테스트
        print("6️⃣ 안전 전진 테스트 (장애물 확인하며 전진)")
        success = self.safe_forward_with_obstacle_check(1.0)
        print(f"   결과: {'성공' if success else '장애물로 인한 중단'}")

        print("✅ 개선된 장애물 회피 기능 테스트 완료")
        print("   ✨ 주요 개선사항:")
        print("   - 더 먼 거리(40cm)에서 조기 감지")
        print("   - 후진 없이 바로 제자리 회전")
        print("   - 0.1초 정지 후 양방향 반대 회전으로 더 큰 각도")
        print("=" * 60)

    def test_turn_hold_adjustment(self) -> None:
        """회전 시간 조절 기능 테스트"""
        print("🧪 회전 시간 조절 기능 테스트")
        print("=" * 40)

        # 현재 설정 확인
        current_time = self.config.get_turn_hold_seconds()
        print(f"현재 회전 시간: {current_time:.2f}초")

        # +0.05초 조절 테스트
        new_time = self.config.adjust_turn_hold_time(1)  # +0.05초
        print(f"3키(+0.05초): {current_time:.2f}s → {new_time:.2f}s")

        # +0.05초 더 조절
        new_time = self.config.adjust_turn_hold_time(1)  # +0.05초
        print(f"3키(+0.05초): {new_time-0.05:.2f}s → {new_time:.2f}s")

        # -0.05초 조절 테스트
        new_time = self.config.adjust_turn_hold_time(-1)  # -0.05초
        print(f"4키(-0.05초): {new_time+0.05:.2f}s → {new_time:.2f}s")

        # 범위 테스트 (최대값)
        self.config.turn_hold_seconds = 0.45
        new_time = self.config.adjust_turn_hold_time(2)  # +0.10초 시도
        print(f"최대값 테스트: 0.45s + 0.10s → {new_time:.2f}s (최대 0.5s 제한)")

        # 범위 테스트 (최소값)
        self.config.turn_hold_seconds = 0.15
        new_time = self.config.adjust_turn_hold_time(-2)  # -0.10초 시도
        print(f"최소값 테스트: 0.15s - 0.10s → {new_time:.2f}s (최소 0.1s 제한)")

        # 기본값 복원
        self.config.reset_to_defaults()
        restored_time = self.config.get_turn_hold_seconds()
        print(f"기본값 복원: {restored_time:.2f}초")

        print("✅ 회전 시간 조절 기능 테스트 완료")
        print("  💡 사용법:")
        print("  - 3키: 회전 시간 +0.05초 (더 긴 회전)")
        print("  - 4키: 회전 시간 -0.05초 (더 짧은 회전)")
        print("  - 범위: 0.1초 ~ 0.5초")
        print("=" * 40)

    def analyze_line_position(self) -> tuple[str, str, float]:
        """라인 센서 데이터를 분석하여 위치 상태와 권장 동작 반환

        Returns:
            (위치상태, 권장동작, 회전시간) -
            위치상태: "center", "slight_left", "slight_right", "far_left", "far_right", "all_sensors", "lost"
            권장동작: "forward", "micro_left", "micro_right", "slight_left", "slight_right", "strong_left", "strong_right", "stop_backward_left", "search"
        """
        try:
            if not self.line or not getattr(self.line, "controller", None):
                return ("lost", "search", self.config.strong_turn_time)

            info = self.line.get_position_info()
            if not isinstance(info, dict):
                return ("lost", "search", self.config.strong_turn_time)

            sensors = info.get("sensors", {})
            left = int(sensors.get("left", 1))
            middle = int(sensors.get("middle", 1))
            right = int(sensors.get("right", 1))
            pattern = f"{left}{middle}{right}"

            # 패턴 분석 및 동작 결정
            if pattern == "010":  # 중앙에 라인
                return ("center", "forward", 0.0)

            elif pattern == "110":  # 중앙+좌측에 라인 (약간 우측으로 치우침)
                return ("slight_left", "micro_right", self.config.micro_turn_time)

            elif pattern == "011":  # 중앙+우측에 라인 (약간 좌측으로 치우침)
                return ("slight_right", "micro_left", self.config.micro_turn_time)

            elif pattern == "100":  # 좌측에만 라인 (우측으로 많이 치우침)
                return ("far_left", "slight_right", self.config.slight_turn_time)

            elif pattern == "001":  # 우측에만 라인 (좌측으로 많이 치우침)
                return ("far_right", "slight_left", self.config.slight_turn_time)

            elif pattern == "000":  # 라인 없음 (완전 이탈)
                return ("lost", "search", self.config.strong_turn_time)

            elif pattern == "111":  # 모든 센서에 라인 (교차점 또는 넓은 라인)
                return (
                    "all_sensors",
                    "stop_backward_left",
                    self.config.strong_turn_time,
                )

            else:  # 기타 패턴
                # 좌측 센서 활성화시 우측으로, 우측 센서 활성화시 좌측으로
                if left == 0:
                    return ("slight_left", "slight_right", self.config.normal_turn_time)
                elif right == 0:
                    return ("slight_right", "slight_left", self.config.normal_turn_time)
                else:
                    return ("lost", "search", self.config.strong_turn_time)

        except Exception as e:
            print(f"라인 위치 분석 오류: {e}")
            return ("lost", "search", self.config.strong_turn_time)

    def adaptive_line_follow_step(self) -> bool:
        """적응형 라인 팔로잉 한 스텝 실행

        Returns:
            True: 라인 따라가기 계속
            False: 라인 이탈 또는 정지 필요
        """
        try:
            # 먼저 장애물 확인 (설정에 따라 on/off 가능)
            if self.config.is_ultrasonic_enabled() and self.auto_obstacle_avoid():
                return True  # 장애물 회피 후 계속

            # 라인 위치 분석
            position, action, turn_time = self.analyze_line_position()

            # 센서 상태 로깅
            sensor_info = self.get_line_sensor_snapshot("적응형")
            print(
                f"{sensor_info} | 위치: {position} | 동작: {action} | 시간: {turn_time:.2f}s"
            )

            # 동작 실행
            if action == "forward":
                self.motor.set_speeds(
                    self.config.forward_speed, self.config.forward_speed
                )

            elif action == "micro_left":
                # 미세 좌회전 (속도 차이 작게)
                left_speed = self.config.forward_speed - 10
                right_speed = self.config.forward_speed
                self.motor.set_speeds(left_speed, right_speed)
                time.sleep(turn_time)

            elif action == "micro_right":
                # 미세 우회전 (속도 차이 작게)
                left_speed = self.config.forward_speed
                right_speed = self.config.forward_speed - 10
                self.motor.set_speeds(left_speed, right_speed)
                time.sleep(turn_time)

            elif action == "slight_left":
                # 약한 좌회전
                left_speed = self.config.low_turn_speed
                right_speed = self.config.forward_speed
                self.motor.set_speeds(left_speed, right_speed)
                time.sleep(turn_time)

            elif action == "slight_right":
                # 약한 우회전
                left_speed = self.config.forward_speed
                right_speed = self.config.low_turn_speed
                self.motor.set_speeds(left_speed, right_speed)
                time.sleep(turn_time)

            elif action == "strong_left":
                # 강한 좌회전 (제자리 회전)
                self.motor.set_speeds(0, 0)
                time.sleep(0.05)
                self.motor.set_speeds(
                    self.config.high_turn_speed, -self.config.high_turn_speed
                )
                time.sleep(turn_time)

            elif action == "strong_right":
                # 강한 우회전 (제자리 회전)
                self.motor.set_speeds(0, 0)
                time.sleep(0.05)
                self.motor.set_speeds(
                    -self.config.high_turn_speed, self.config.high_turn_speed
                )
                time.sleep(turn_time)

            elif action == "stop_backward_left":
                # 모든 센서 감지시 안정적 처리: 정지 → 후진 → 좌회전
                print("⚠️ 모든 센서 감지 - 안정적 처리 시작")

                # 1단계: 확실한 정지 (0.1초)
                print("1️⃣ 완전 정지 (0.1초)")
                self.motor.set_speeds(0, 0)
                time.sleep(0.1)
                print(self.get_line_sensor_snapshot("[정지후-센서확인]"))

                # 2단계: 후진 (0.1초)
                print("2️⃣ 후진 이동 (0.1초)")
                self.motor.set_speeds(
                    -self.config.forward_speed, -self.config.forward_speed
                )
                time.sleep(0.1)
                self.motor.set_speeds(0, 0)
                time.sleep(0.05)  # 안정화
                print(self.get_line_sensor_snapshot("[후진후-센서확인]"))

                # 3단계: 좌회전 (제자리 회전)
                print("3️⃣ 좌회전 시작")
                self.motor.set_speeds(
                    self.config.high_turn_speed, -self.config.high_turn_speed
                )
                time.sleep(turn_time)
                self.motor.set_speeds(0, 0)
                time.sleep(0.05)  # 안정화
                print("✅ 모든 센서 감지 처리 완료")
                print(self.get_line_sensor_snapshot("[처리완료-센서확인]"))

            elif action == "search":
                # 라인 탐색 (좌우 회전 시도)
                print("🔍 라인 탐색 중...")
                self.motor.set_speeds(0, 0)
                time.sleep(0.1)
                # 간단한 좌우 탐색
                self.motor.set_speeds(
                    self.config.high_turn_speed, -self.config.high_turn_speed
                )
                time.sleep(0.2)
                self.motor.set_speeds(
                    -self.config.high_turn_speed, self.config.high_turn_speed
                )
                time.sleep(0.4)
                self.motor.set_speeds(
                    self.config.high_turn_speed, -self.config.high_turn_speed
                )
                time.sleep(0.2)

            return position != "lost"

        except Exception as e:
            print(f"적응형 라인 팔로잉 오류: {e}")
            self.emergency_stop()
            return False

    def adaptive_line_follow_continuous(self, duration_seconds: float = None) -> None:
        """적응형 라인 팔로잉 연속 실행

        Args:
            duration_seconds: 실행 시간 (None이면 무제한)
        """
        print("🤖 적응형 라인 팔로잉 시작")
        print("=" * 50)

        start_time = time.time()
        step_count = 0

        try:
            while True:
                # 시간 제한 확인
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    print(f"⏰ 시간 제한 ({duration_seconds}초) 도달")
                    break

                # 한 스텝 실행
                if not self.adaptive_line_follow_step():
                    print("❌ 라인 이탈 또는 오류로 중단")
                    break

                step_count += 1
                time.sleep(0.05)  # 50ms 간격으로 업데이트

        except KeyboardInterrupt:
            print("🛑 사용자 중단")
        except Exception as e:
            print(f"적응형 라인 팔로잉 중단: {e}")
        finally:
            self.emergency_stop()
            print(f"✅ 적응형 라인 팔로잉 완료 (스텝: {step_count})")
            print("=" * 50)

    def test_adaptive_line_following(self) -> None:
        """적응형 라인 팔로잉 시스템 테스트"""
        print("🧪 적응형 라인 팔로잉 시스템 테스트")
        print("=" * 60)

        # 1. 설정값 확인
        print("1️⃣ 적응형 회전 시간 설정:")
        print(f"   - 미세조정: {self.config.micro_turn_time:.3f}초 (중앙 근처)")
        print(f"   - 약한회전: {self.config.slight_turn_time:.3f}초 (약간 벗어남)")
        print(f"   - 보통회전: {self.config.normal_turn_time:.3f}초 (많이 벗어남)")
        print(f"   - 강한회전: {self.config.strong_turn_time:.3f}초 (완전 이탈)")
        time.sleep(2)

        # 2. 라인 위치 분석 테스트
        print("\n2️⃣ 라인 위치 분석 테스트:")
        position, action, turn_time = self.analyze_line_position()
        sensor_info = self.get_line_sensor_snapshot("분석")
        print(f"   {sensor_info}")
        print(f"   위치: {position} | 권장동작: {action} | 회전시간: {turn_time:.3f}초")
        time.sleep(2)

        # 3. 시뮬레이션 패턴 테스트
        print("\n3️⃣ 다양한 센서 패턴 시뮬레이션:")
        test_patterns = [
            ("010", "중앙에 라인"),
            ("110", "중앙+좌측 라인"),
            ("011", "중앙+우측 라인"),
            ("100", "좌측만 라인"),
            ("001", "우측만 라인"),
            ("000", "라인 없음"),
            ("111", "모든 센서 라인 (교차점)"),
        ]

        for pattern, description in test_patterns:
            # 패턴별 분석 시뮬레이션
            mock_sensors = {
                "left": int(pattern[0]),
                "middle": int(pattern[1]),
                "right": int(pattern[2]),
            }

            # 간단한 분석 로직
            if pattern == "010":
                pos, act, tm = "center", "forward", 0.0
            elif pattern == "110":
                pos, act, tm = "slight_left", "micro_right", self.config.micro_turn_time
            elif pattern == "011":
                pos, act, tm = "slight_right", "micro_left", self.config.micro_turn_time
            elif pattern == "100":
                pos, act, tm = "far_left", "slight_right", self.config.slight_turn_time
            elif pattern == "001":
                pos, act, tm = "far_right", "slight_left", self.config.slight_turn_time
            elif pattern == "000":
                pos, act, tm = "lost", "search", self.config.strong_turn_time
            else:  # "111"
                pos, act, tm = (
                    "all_sensors",
                    "stop_backward_left",
                    self.config.strong_turn_time,
                )

            print(f"   패턴 {pattern} ({description}): {pos} → {act} ({tm:.3f}s)")

        time.sleep(2)

        # 4. 실제 적응형 주행 데모 (짧은 시간)
        print("\n4️⃣ 적응형 라인 팔로잉 데모 (5초간):")
        print("   (실제 센서로 적응형 주행 테스트)")
        self.adaptive_line_follow_continuous(5.0)

        print("\n✅ 적응형 라인 팔로잉 시스템 테스트 완료")
        print("   ✨ 주요 특징:")
        print("   - 라인 위치에 따른 4단계 회전 강도")
        print("   - 미세 조정부터 강한 회전까지 적응적 대응")
        print("   - 장애물 감지와 연동된 통합 자율주행")
        print("   - 실시간 센서 분석 및 동작 로깅")
        print("=" * 60)

    def test_all_sensors_handling(self) -> None:
        """모든 센서 감지(111 패턴) 처리 테스트"""
        print("🧪 모든 센서 감지 처리 테스트")
        print("=" * 50)

        print("📋 테스트 시나리오:")
        print("   - 111 패턴 감지 시뮬레이션")
        print("   - 정지(0.1초) → 후진(0.1초) → 좌회전 시퀀스")
        print("   - 각 단계별 센서 상태 모니터링")
        print("=" * 50)

        # 현재 센서 상태 확인
        print("1️⃣ 현재 센서 상태:")
        current_info = self.get_line_sensor_snapshot("현재")
        print(f"   {current_info}")
        time.sleep(1)

        # 111 패턴 처리 시뮬레이션
        print("\n2️⃣ 모든 센서 감지 처리 시뮬레이션:")

        # 실제 stop_backward_left 동작 실행
        print("⚠️ 모든 센서 감지 - 안정적 처리 시작")

        # 1단계: 확실한 정지 (0.1초)
        print("1️⃣ 완전 정지 (0.1초)")
        (
            self.motor.set_speeds(0, 0)
            if self.motor and getattr(self.motor, "controller", None)
            else None
        )
        time.sleep(0.1)
        stop_info = self.get_line_sensor_snapshot("[정지후-센서확인]")
        print(f"   {stop_info}")

        # 2단계: 후진 (0.1초)
        print("2️⃣ 후진 이동 (0.1초)")
        if self.motor and getattr(self.motor, "controller", None):
            self.motor.set_speeds(
                -self.config.forward_speed, -self.config.forward_speed
            )
            time.sleep(0.1)
            self.motor.set_speeds(0, 0)
        else:
            print("   Simulation: Backward movement")
            time.sleep(0.1)
        time.sleep(0.05)  # 안정화
        backward_info = self.get_line_sensor_snapshot("[후진후-센서확인]")
        print(f"   {backward_info}")

        # 3단계: 좌회전 (제자리 회전)
        print("3️⃣ 좌회전 시작")
        if self.motor and getattr(self.motor, "controller", None):
            self.motor.set_speeds(
                self.config.high_turn_speed, -self.config.high_turn_speed
            )
            time.sleep(self.config.strong_turn_time)
            self.motor.set_speeds(0, 0)
        else:
            print("   Simulation: Left turn rotation")
            time.sleep(self.config.strong_turn_time)
        time.sleep(0.05)  # 안정화

        turn_info = self.get_line_sensor_snapshot("[처리완료-센서확인]")
        print(f"   {turn_info}")
        print("✅ 모든 센서 감지 처리 완료")

        print("\n3️⃣ 테스트 결과 분석:")
        print("   ✨ 개선 사항:")
        print("   - 교차점이나 넓은 라인에서 안정적 처리")
        print("   - 정지 → 후진 → 좌회전으로 선 이탈 방지")
        print("   - 각 단계별 센서 상태 모니터링으로 디버깅 용이")
        print("   - autonomous_driver와 manual_controller 모두 적용")
        print("=" * 50)

    def test_turn_hold_adjustment_in_action(self) -> None:
        """실제 회전 동작에서 회전 지연 시간 조절 테스트"""
        print("🧪 회전 지연 시간 실제 동작 테스트")
        print("=" * 50)

        # 현재 설정 확인
        current_time = self.config.get_turn_hold_seconds()
        print(f"현재 회전 지연 시간: {current_time:.2f}초")

        # 기본 회전 테스트
        print("\n1️⃣ 기본 회전 지연 시간으로 좌회전 테스트")
        if self.motor and getattr(self.motor, "controller", None):
            self.motor.set_speeds(
                self.config.high_turn_speed, -self.config.high_turn_speed
            )
            time.sleep(self.config.get_turn_hold_seconds())
            self.motor.set_speeds(0, 0)
            print(f"   ✓ 좌회전 완료 ({current_time:.2f}초 지속)")
        else:
            print(f"   Simulation: Left turn for {current_time:.2f} seconds")
        time.sleep(1)

        # 시간 늘려서 테스트
        print("\n2️⃣ 회전 시간 늘리기 (+0.10초)")
        self.config.adjust_turn_hold_time(2)  # +0.10초
        new_time = self.config.get_turn_hold_seconds()
        print(f"   조정된 시간: {new_time:.2f}초")

        if self.motor and getattr(self.motor, "controller", None):
            self.motor.set_speeds(
                self.config.high_turn_speed, -self.config.high_turn_speed
            )
            time.sleep(self.config.get_turn_hold_seconds())
            self.motor.set_speeds(0, 0)
            print(f"   ✓ 좌회전 완료 ({new_time:.2f}초 지속) - 더 긴 회전")
        else:
            print(f"   Simulation: Left turn for {new_time:.2f} seconds (longer)")
        time.sleep(1)

        # 시간 줄여서 테스트
        print("\n3️⃣ 회전 시간 줄이기 (-0.15초)")
        self.config.adjust_turn_hold_time(-3)  # -0.15초
        short_time = self.config.get_turn_hold_seconds()
        print(f"   조정된 시간: {short_time:.2f}초")

        if self.motor and getattr(self.motor, "controller", None):
            self.motor.set_speeds(
                self.config.high_turn_speed, -self.config.high_turn_speed
            )
            time.sleep(self.config.get_turn_hold_seconds())
            self.motor.set_speeds(0, 0)
            print(f"   ✓ 좌회전 완료 ({short_time:.2f}초 지속) - 더 짧은 회전")
        else:
            print(f"   Simulation: Left turn for {short_time:.2f} seconds (shorter)")

        # 원래 시간으로 복원
        self.config.reset_to_defaults()
        restored_time = self.config.get_turn_hold_seconds()
        print(f"\n4️⃣ 기본값 복원: {restored_time:.2f}초")

        print("\n✅ 회전 지연 시간 실제 동작 테스트 완료")
        print("   💡 사용법:")
        print("   - 3키: 회전 시간 +0.05초 (더 큰 각도)")
        print("   - 4키: 회전 시간 -0.05초 (더 작은 각도)")
        print("   - 자율주행 중에도 실시간 조절 가능")
        print("   - 범위: 0.1초 ~ 0.5초")
        print("=" * 50)

    def test_ultrasonic_toggle(self) -> None:
        """초음파 센서 on/off 토글 기능 테스트"""
        print("🧪 초음파 센서 토글 기능 테스트")
        print("=" * 50)

        # 현재 상태 확인
        current_status = self.config.is_ultrasonic_enabled()
        status_text = "활성화" if current_status else "비활성화"
        print(f"1️⃣ 현재 초음파 센서 상태: {status_text}")

        # 거리 측정 테스트 (활성화 상태에서만)
        if current_status:
            distance = self.check_obstacle_distance()
            print(f"   현재 측정 거리: {distance:.1f}cm")
        else:
            print("   초음파 센서가 비활성화되어 거리 측정 불가")

        time.sleep(1)

        # 토글 테스트
        print("\n2️⃣ 초음파 센서 토글 테스트:")
        new_status = self.config.toggle_ultrasonic_sensor()
        new_status_text = "활성화" if new_status else "비활성화"
        print(f"   토글 후 상태: {new_status_text}")

        # 자율주행에서의 동작 테스트
        print("\n3️⃣ 자율주행 로직에서 초음파 센서 사용 여부:")
        if self.config.is_ultrasonic_enabled():
            print("   ✅ 자율주행 중 장애물 감지 활성화")
            print("   ✅ 적응형 라인 팔로잉에서 장애물 확인")
        else:
            print("   ❌ 자율주행 중 장애물 감지 비활성화")
            print("   ❌ 적응형 라인 팔로잉에서 장애물 확인 생략")

        # 다시 토글해서 원래 상태로
        print("\n4️⃣ 원래 상태로 복원:")
        restored_status = self.config.toggle_ultrasonic_sensor()
        restored_text = "활성화" if restored_status else "비활성화"
        print(f"   복원된 상태: {restored_text}")

        print("\n✅ 초음파 센서 토글 기능 테스트 완료")
        print("   💡 사용법:")
        print("   - u키: 초음파 센서 on/off 토글")
        print("   - 자율주행 중에도 실시간 토글 가능")
        print("   - 토글 상태는 메뉴에서 확인 가능")
        print("   - off시 장애물 감지 및 회피 기능 완전 비활성화")
        print("=" * 50)

    def obstacle_avoid_left(self, forward_after: bool = True) -> None:
        """장애물 회피용 제자리 큰 각도 좌회전

        Args:
            forward_after: 회전 후 전진할지 여부 (기본값: True)
        """
        try:
            if self.motor and getattr(self.motor, "controller", None):
                print("🔄 장애물 회피: 제자리 대각도 좌회전 시작")
                print(self.get_line_sensor_snapshot("[장애물회피-좌회전-이전]"))

                # 1단계: 완전 정지 확인 및 대기
                self.motor.set_speeds(0, 0)
                time.sleep(0.1)  # 0.1초 정지 상태 유지
                print("⏸️ 정지 상태에서 회전 준비")

                # 2단계: 제자리 큰 각도 좌회전 (양방향 반대 회전으로 더 큰 각도)
                self.motor.set_speeds(
                    self.config.obstacle_avoid_speed, -self.config.obstacle_avoid_speed
                )
                time.sleep(self.config.obstacle_avoid_time)
                self.motor.set_speeds(0, 0)

                print("✓ 제자리 좌회전 완료")
                print(self.get_line_sensor_snapshot("[장애물회피-좌회전-이후]"))

                # 회전 후 전진 (선택적)
                if forward_after:
                    time.sleep(0.3)  # 안정화 대기
                    print("🚗 장애물 회피 후 전진")
                    self.motor.set_speeds(
                        self.config.forward_speed, self.config.forward_speed
                    )
                    time.sleep(self.config.obstacle_forward_time)
                    self.motor.set_speeds(0, 0)
                    print("✓ 장애물 회피 전진 완료")
                    print(self.get_line_sensor_snapshot("[장애물회피-전진-이후]"))

            else:
                print(
                    f"Simulation: Stop for 0.1s then stationary left turn at ±{self.config.obstacle_avoid_speed}% for {self.config.obstacle_avoid_time}s"
                )
                time.sleep(0.1 + self.config.obstacle_avoid_time)
                if forward_after:
                    print(
                        f"Simulation: Forward at {self.config.forward_speed}% for {self.config.obstacle_forward_time}s"
                    )
                    time.sleep(self.config.obstacle_forward_time)
                print("Simulation: Stationary obstacle avoidance left completed")

        except Exception as e:
            print(f"장애물 회피 좌회전 오류: {e}")

    def obstacle_avoid_right(self, forward_after: bool = True) -> None:
        """장애물 회피용 제자리 큰 각도 우회전

        Args:
            forward_after: 회전 후 전진할지 여부 (기본값: True)
        """
        try:
            if self.motor and getattr(self.motor, "controller", None):
                print("🔄 장애물 회피: 제자리 대각도 우회전 시작")
                print(self.get_line_sensor_snapshot("[장애물회피-우회전-이전]"))

                # 1단계: 완전 정지 확인 및 대기
                self.motor.set_speeds(0, 0)
                time.sleep(0.1)  # 0.1초 정지 상태 유지
                print("⏸️ 정지 상태에서 회전 준비")

                # 2단계: 제자리 큰 각도 우회전 (양방향 반대 회전으로 더 큰 각도)
                self.motor.set_speeds(
                    -self.config.obstacle_avoid_speed, self.config.obstacle_avoid_speed
                )
                time.sleep(self.config.obstacle_avoid_time)
                self.motor.set_speeds(0, 0)

                print("✓ 제자리 우회전 완료")
                print(self.get_line_sensor_snapshot("[장애물회피-우회전-이후]"))

                # 회전 후 전진 (선택적)
                if forward_after:
                    time.sleep(0.3)  # 안정화 대기
                    print("🚗 장애물 회피 후 전진")
                    self.motor.set_speeds(
                        self.config.forward_speed, self.config.forward_speed
                    )
                    time.sleep(self.config.obstacle_forward_time)
                    self.motor.set_speeds(0, 0)
                    print("✓ 장애물 회피 전진 완료")
                    print(self.get_line_sensor_snapshot("[장애물회피-전진-이후]"))

            else:
                print(
                    f"Simulation: Stop for 0.1s then stationary right turn at ±{self.config.obstacle_avoid_speed}% for {self.config.obstacle_avoid_time}s"
                )
                time.sleep(0.1 + self.config.obstacle_avoid_time)
                if forward_after:
                    print(
                        f"Simulation: Forward at {self.config.forward_speed}% for {self.config.obstacle_forward_time}s"
                    )
                    time.sleep(self.config.obstacle_forward_time)
                print("Simulation: Stationary obstacle avoidance right completed")

        except Exception as e:
            print(f"장애물 회피 우회전 오류: {e}")

    def obstacle_avoid_sequence(self, direction: str = "left") -> None:
        """장애물 회피 시퀀스: 후진 → 대각도 회전 → 전진 → 복귀 회전

        Args:
            direction: 회피 방향 ("left" 또는 "right")
        """
        try:
            print(
                f"🚨 장애물 회피 시퀀스 시작 (방향: {'좌측' if direction == 'left' else '우측'})"
            )

            # 1단계: 약간 후진 (장애물과 거리 확보)
            print("1️⃣ 후진으로 거리 확보")
            self.drive_motion("backward", 0.3, label="회피준비")
            time.sleep(0.2)

            # 2단계: 대각도 회전 (전진 없이)
            print("2️⃣ 대각도 회전")
            if direction == "left":
                self.obstacle_avoid_left(forward_after=False)
            else:
                self.obstacle_avoid_right(forward_after=False)
            time.sleep(0.2)

            # 3단계: 장애물 우회 전진
            print("3️⃣ 장애물 우회 전진")
            self.drive_motion(
                "forward", self.config.obstacle_forward_time * 1.5, label="우회전진"
            )
            time.sleep(0.2)

            # 4단계: 반대 방향으로 복귀 회전
            print("4️⃣ 원래 경로로 복귀 회전")
            opposite_direction = "right" if direction == "left" else "left"
            if opposite_direction == "left":
                self.obstacle_avoid_left(forward_after=False)
            else:
                self.obstacle_avoid_right(forward_after=False)
            time.sleep(0.2)

            # 5단계: 전진하여 라인 재탐지
            print("5️⃣ 라인 재탐지를 위한 전진")
            self.drive_motion("forward", 0.5, label="라인탐지")

            print("✅ 장애물 회피 시퀀스 완료")

        except Exception as e:
            print(f"장애물 회피 시퀀스 오류: {e}")

    def check_obstacle_distance(self) -> float:
        """현재 장애물과의 거리를 측정하여 반환 (cm)

        Returns:
            측정된 거리 (cm), 측정 실패시 999.0 반환
        """
        try:
            if self.ultrasonic and getattr(self.ultrasonic, "sensor", None):
                distance = self.ultrasonic.read_distance_cm()
                if distance is not None:
                    return distance
                else:
                    return 999.0  # 측정 실패
            else:
                # 시뮬레이션 모드에서는 안전 거리보다 큰 값 반환
                return self.config.safe_distance + 10
        except Exception as e:
            print(f"초음파 센서 읽기 오류: {e}")
            return 999.0

    def get_obstacle_status(self) -> tuple[str, float]:
        """장애물 상태를 단계별로 분석

        Returns:
            (상태, 거리) - 상태: "safe", "early", "warning", "critical"
        """
        distance = self.check_obstacle_distance()

        if distance < self.config.critical_distance:
            return ("critical", distance)
        elif distance < self.config.warning_distance:
            return ("warning", distance)
        elif distance < self.config.early_detection_distance:
            return ("early", distance)
        else:
            return ("safe", distance)

    def is_obstacle_detected(self) -> bool:
        """장애물 감지 여부 확인 (기존 호환성 유지)

        Returns:
            True: 장애물 감지됨 (위험거리 이내)
            False: 안전함
        """
        status, distance = self.get_obstacle_status()
        is_detected = status in ["critical", "warning"]

        if is_detected:
            print(
                f"⚠️ 장애물 감지: {distance:.1f}cm (위험거리: {self.config.critical_distance}cm)"
            )

        return is_detected

    def auto_obstacle_avoid(self, preferred_direction: str = "left") -> bool:
        """자동 장애물 회피 (초음파 센서 기반) - 조기 감지 및 제자리 회전

        Args:
            preferred_direction: 우선 회피 방향 ("left" 또는 "right")

        Returns:
            True: 회피 동작 수행됨
            False: 장애물 없음 또는 회피 불필요
        """
        try:
            status, distance = self.get_obstacle_status()

            if status == "safe":
                return False
            elif status == "early":
                print(
                    f"🔍 조기 장애물 감지: {distance:.1f}cm (감지거리: {self.config.early_detection_distance}cm)"
                )
                print(
                    f"🚨 예방적 장애물 회피 시작 (방향: {'좌측' if preferred_direction == 'left' else '우측'})"
                )
            elif status in ["warning", "critical"]:
                print(
                    f"⚠️ 위험 장애물 감지: {distance:.1f}cm (위험거리: {self.config.critical_distance}cm)"
                )
                print(
                    f"🚨 긴급 장애물 회피 시작 (방향: {'좌측' if preferred_direction == 'left' else '우측'})"
                )

            # 즉시 정지 및 안정화
            self.emergency_stop()
            time.sleep(0.1)

            # 제자리 회전으로 회피 (후진 없이)
            if preferred_direction == "left":
                self.obstacle_avoid_left(forward_after=True)
            else:
                self.obstacle_avoid_right(forward_after=True)

            return True

        except Exception as e:
            print(f"자동 장애물 회피 오류: {e}")
            return False

    def safe_forward_with_obstacle_check(self, duration_seconds: float = None) -> bool:
        """장애물 확인하며 안전 전진

        Args:
            duration_seconds: 전진 시간 (None이면 무제한)

        Returns:
            True: 정상 전진 완료
            False: 장애물로 인한 중단
        """
        try:
            # 전진 시작 전 장애물 확인 (조기 감지 포함)
            status, distance = self.get_obstacle_status()
            if status in ["warning", "critical"]:
                print(f"⚠️ 전진 차단: 장애물 감지 ({distance:.1f}cm)")
                return False
            elif status == "early":
                print(f"🔍 조기 감지: {distance:.1f}cm - 저속 전진")
                # 조기 감지시 속도 감소
                forward_speed = self.config.forward_speed // 2
            else:
                forward_speed = self.config.forward_speed

            # 전진 시작
            self.motor.set_speeds(forward_speed, forward_speed)

            if duration_seconds is None:
                # 무제한 전진 (외부에서 정지 필요)
                return True
            else:
                # 제한 시간 전진 (중간에 장애물 확인)
                start_time = time.time()
                while time.time() - start_time < duration_seconds:
                    status, distance = self.get_obstacle_status()
                    if status in ["warning", "critical"]:
                        self.emergency_stop()
                        print(f"⚠️ 전진 중 장애물 감지로 정지 ({distance:.1f}cm)")
                        return False
                    elif (
                        status == "early" and forward_speed == self.config.forward_speed
                    ):
                        # 전진 중 조기 감지시 속도 감소
                        forward_speed = self.config.forward_speed // 2
                        self.motor.set_speeds(forward_speed, forward_speed)
                        print(f"🔍 전진 중 조기 감지: 속도 감소 ({distance:.1f}cm)")
                    time.sleep(0.1)  # 0.1초마다 확인

                # 정상 완료
                self.motor.set_speeds(0, 0)
                return True

        except Exception as e:
            print(f"안전 전진 오류: {e}")
            self.emergency_stop()
            return False

    def emergency_stop(self) -> None:
        """긴급 정지 - 모든 모터 즉시 정지"""
        try:
            if self.motor and getattr(self.motor, "controller", None):
                self.motor.stop()
                print("✓ 모터 긴급 정지")
        except Exception:
            pass
