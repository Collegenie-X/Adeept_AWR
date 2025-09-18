#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
메뉴 출력 서비스 모듈
- 키보드 제어 메뉴 출력
- 설정값 상태 표시
- 종료 시 요약 정보 출력
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config_service import ConfigurationService


class MenuService:
    """메뉴 출력 담당 서비스 클래스"""

    def __init__(self, config_service: "ConfigurationService"):
        self.config = config_service

    def print_control_menu(self) -> None:
        """키보드 제어 메뉴 출력"""
        print("\n" + "=" * 70)
        print("🎮 키보드 제어 메뉴 및 현재 설정")
        print("=" * 70)

        # 현재 설정값 상세 정보
        print("📊 현재 속도 및 설정 정보:")
        print(
            f"  🚗 전진 속도:     {self.config.forward_speed:3d}% "
            f"(범위: {self.config.SPEED_MIN}-{self.config.SPEED_MAX}%, "
            f"기본값: {self.config.DEFAULT_FORWARD_SPEED}%)"
        )
        print(
            f"  🔄 약한 회전:     {self.config.low_turn_speed:3d}% "
            f"(범위: {self.config.SPEED_MIN}-{self.config.SPEED_MAX}%, "
            f"기본값: {self.config.DEFAULT_LOW_TURN_SPEED}%)"
        )
        print(
            f"  ⚡ 강한 회전:     {self.config.high_turn_speed:3d}% "
            f"(범위: {self.config.SPEED_MIN}-{self.config.SPEED_MAX}%, "
            f"기본값: {self.config.DEFAULT_HIGH_TURN_SPEED}%)"
        )
        print(
            f"  🛡️ 안전 거리:     {self.config.safe_distance:3d}cm "
            f"(범위: {self.config.DISTANCE_MIN}-{self.config.DISTANCE_MAX}cm, "
            f"기본값: {self.config.DEFAULT_SAFE_DISTANCE}cm)"
        )
        print(
            f"  ⏱️ 회피 시간:     {self.config.get_avoid_time_seconds():4.1f}s "
            f"(범위: {self.config.TIME_MIN/10:.1f}-{self.config.TIME_MAX/10:.1f}s, "
            f"기본값: {self.config.DEFAULT_AVOID_TIME:.1f}s)"
        )

        print("\n🎯 속도 설정 용도:")
        print("  • 전진 속도: 직선 주행 시 사용")
        print("  • 약한 회전: 라인 센서 center_left/center_right 감지 시 미세 조정")
        print("  • 강한 회전: 라인 센서 left/right 감지 시 빠른 회전")
        print("  • 안전 거리: 장애물 감지 최소 거리")
        print("  • 회피 시간: 장애물 회피 동작 지속 시간")

        print("\n🚦 주행 제어:")
        print("  Enter: 자동 주행 시작")
        print("  스페이스(또는 p): 즉시 정지 (모든 동작 중단, 수동 모드로 전환)")
        print("  q: 프로그램 종료")

        print(
            f"\n🎮 수동 조작 (정지 상태에서만, {self.config.get_manual_pulse_seconds():.1f}초 동작 후 자동 정지):"
        )
        print("  ↑ 또는 w: 전진 (현재 전진 속도로)")
        print("  ↓ 또는 s: 후진 (현재 전진 속도로)")
        print("  ← 또는 a: 좌회전 (현재 강한 회전 속도로)")
        print("  → 또는 d: 우회전 (현재 강한 회전 속도로)")

        print("\n⚙️ 속도 조절 (실시간, Enter 키 불필요):")
        print("  1,2: 전진 속도 -10%/+10%")
        print("  3,4: 약한 회전 속도 -10%/+10%")
        print("  5,6: 강한 회전 속도 -10%/+10%")
        print("  7,8: 안전 거리 -5cm/+5cm")
        print("  9,0: 회피 시간 -0.1s/+0.1s")
        print("  [,]: 수동 펄스 시간 -0.1s/+0.1s")
        print("  m: 모터 캘리브레이션 (직진 보정)")

        print("\n🔍 디버깅 기능:")
        print("  x: 라인 센서 상태 실시간 확인")
        print("  z: 거리 센서 상태 확인")
        print("  t: 조향 테스트 시퀀스 실행")

        print("\n💡 팁:")
        print("  • 대부분의 키는 Enter 없이 즉시 반응, 자동 시작은 Enter 키")
        print("  • 자동 주행 중에도 속도 실시간 조절 가능")
        print(
            f"  • 수동 조작은 {self.config.get_manual_pulse_seconds():.1f}초 동작 후 자동 정지 (속도/각도 테스트용)"
        )
        print("  • 스페이스(또는 p) 키로 언제든 모든 동작 즉시 중단")
        print("  • q 키 또는 Ctrl+C로 설정값 표시 후 안전 종료")
        print("  • x, z 키로 센서 상태 실시간 확인 가능")
        print("  h: 이 메뉴 다시 보기")
        print("=" * 70)

    def print_status_line(
        self, autonomous_mode: bool, manual_control_active: bool
    ) -> None:
        """현재 상태를 한 줄로 출력"""
        if autonomous_mode:
            status = "🚗 자동"
        elif manual_control_active:
            status = "🎮 수동"
        else:
            status = "⏸️ 대기"

        print(
            f"\r상태:{status} | Enter=자동 | Space=정지 | q=종료",
            end="",
            flush=True,
        )

    def print_final_settings(self) -> None:
        """종료 시 현재 설정값 표시"""
        print("\n" + "=" * 50)
        print("📊 종료 시점 설정값 요약")
        print("=" * 50)

        settings = self.config.get_current_settings()
        print(
            f"🚗 전진 속도:     {settings['forward_speed']:3d}% "
            f"(기본값: {self.config.DEFAULT_FORWARD_SPEED}%)"
        )
        print(
            f"🔄 약한 회전:     {settings['low_turn_speed']:3d}% "
            f"(기본값: {self.config.DEFAULT_LOW_TURN_SPEED}%)"
        )
        print(
            f"⚡ 강한 회전:     {settings['high_turn_speed']:3d}% "
            f"(기본값: {self.config.DEFAULT_HIGH_TURN_SPEED}%)"
        )
        print(
            f"🛡️ 안전 거리:     {settings['safe_distance']:3d}cm "
            f"(기본값: {self.config.DEFAULT_SAFE_DISTANCE}cm)"
        )
        print(
            f"⏱️ 회피 시간:     {settings['avoid_time']:4.1f}s "
            f"(기본값: {self.config.DEFAULT_AVOID_TIME:.1f}s)"
        )
        print(f"🕐 수동 동작시간: {settings['motor_sleep_time']:4.1f}s")

        # 변경된 설정값 표시
        changed_settings = self.config.get_changed_settings()
        if changed_settings:
            print("\n🔄 기본값에서 변경된 설정:")
            for change in changed_settings:
                print(f"  • {change}")
        else:
            print("\n✅ 모든 설정이 기본값과 동일")

        print("=" * 50)

    def print_runtime_status(self, context: str, distance: float = None) -> None:
        """수동/자동 동작 시점의 런타임 상태 요약 출력"""
        print("-" * 60)
        settings = self.config.get_current_settings()
        print(
            f"[{context}] 속도 설정: "
            f"FWD={settings['forward_speed']}% | "
            f"TURN_LOW={settings['low_turn_speed']}% | "
            f"TURN_HIGH={settings['high_turn_speed']}%"
        )
        print(
            f"안전거리={settings['safe_distance']}cm | "
            f"회피시간={settings['avoid_time']:.1f}s"
        )

        if distance is not None:
            print(
                f"현재 거리={distance:.1f}cm (안전기준 {settings['safe_distance']}cm)"
            )
        else:
            print("현재 거리=알수없음")
        print("-" * 60)
