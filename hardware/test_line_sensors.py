#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
라인 센서 테스트 모듈
- 3개의 적외선 라인 센서를 사용한 라인 감지
- 디지털 출력 (HIGH: 라인 감지, LOW: 바닥 감지)
"""

import RPi.GPIO as GPIO
import time


class LineSensorController:
    def __init__(self):
        # 라인 센서 GPIO 핀 정의
        self.LINE_PIN_RIGHT = 19
        self.LINE_PIN_MIDDLE = 16
        self.LINE_PIN_LEFT = 20

        self.setup()

    def setup(self):
        """GPIO 초기화"""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # 센서 핀을 입력으로 설정
        GPIO.setup(self.LINE_PIN_RIGHT, GPIO.IN)
        GPIO.setup(self.LINE_PIN_MIDDLE, GPIO.IN)
        GPIO.setup(self.LINE_PIN_LEFT, GPIO.IN)

    def read_sensors(self):
        """
        모든 센서의 상태를 읽어서 반환
        :return: (좌측, 중앙, 우측) 센서 값의 튜플
        """
        left = GPIO.input(self.LINE_PIN_LEFT)
        middle = GPIO.input(self.LINE_PIN_MIDDLE)
        right = GPIO.input(self.LINE_PIN_RIGHT)
        return (left, middle, right)

    def get_line_position(self):
        """
        라인의 위치를 판단 (개선된 로직)
        :return: 라인의 상대적 위치와 상세 정보
        """
        left, middle, right = self.read_sensors()

        # 센서 상태를 이진 패턴으로 변환 (LMR)
        pattern = (left << 2) | (middle << 1) | right

        # 패턴별 위치 및 설명 매핑
        position_map = {
            0b000: (None, "라인 없음"),  # 000: 모든 센서 OFF
            0b001: (1, "우측 가장자리"),  # 001: 우측만 ON
            0b010: (0, "중앙 정확"),  # 010: 중앙만 ON
            0b011: (0.5, "중앙-우측"),  # 011: 중앙+우측 ON
            0b100: (-1, "좌측 가장자리"),  # 100: 좌측만 ON
            0b101: (None, "라인 분실 또는 교차점"),  # 101: 좌측+우측 ON (중앙 OFF)
            0b110: (-0.5, "중앙-좌측"),  # 110: 좌측+중앙 ON
            0b111: (0, "넓은 라인 또는 교차점"),  # 111: 모든 센서 ON
        }

        position, description = position_map.get(pattern, (0, "알 수 없음"))

        return {
            "position": position,
            "description": description,
            "pattern": f"{left}{middle}{right}",
            "binary": f"0b{pattern:03b}",
            "sensors": {"left": left, "middle": middle, "right": right},
        }

    def get_simple_position(self):
        """
        간단한 위치 판단 (기존 호환성)
        :return: -1(좌측), 0(중앙), 1(우측), None(감지안됨)
        """
        result = self.get_line_position()
        position = result["position"]

        if position is None:
            return None
        elif position < -0.25:
            return -1  # 좌측
        elif position > 0.25:
            return 1  # 우측
        else:
            return 0  # 중앙

    def cleanup(self):
        """GPIO 설정 초기화"""
        GPIO.cleanup()


def test_line_sensors():
    """라인 센서 테스트 함수"""
    controller = LineSensorController()

    try:
        print("라인 센서 테스트를 시작합니다...")
        print("센서 패턴별 위치 판단을 확인하세요.")
        print("=" * 70)
        print("센서 패턴: 좌[●/○] 중[●/○] 우[●/○] | 위치값 | 설명")
        print("=" * 70)
        print("Ctrl+C를 눌러 종료하세요.\n")

        while True:
            # 센서 값 읽기 (개선된 로직 사용)
            left, middle, right = controller.read_sensors()
            line_info = controller.get_line_position()
            simple_pos = controller.get_simple_position()

            # 위치값을 문자열로 변환
            pos_str = (
                f"{line_info['position']:+5.1f}"
                if line_info["position"] is not None
                else " None"
            )

            # 간단한 위치 표시
            simple_str = {-1: "←좌측", 0: "↑중앙", 1: "우측→", None: "없음"}[simple_pos]

            # 상태 출력 (더 상세한 정보)
            print(
                f"\r센서: 좌[{'●' if left else '○'}] 중[{'●' if middle else '○'}] 우[{'●' if right else '○'}] "
                f"| {pos_str} | {line_info['description']:12s} | {simple_str:6s} | "
                f"패턴:{line_info['pattern']} ({line_info['binary']})",
                end="",
            )

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    finally:
        controller.cleanup()


def test_line_patterns():
    """라인 센서 패턴별 상세 테스트"""
    controller = LineSensorController()

    print("라인 센서 패턴 분석 테스트")
    print("=" * 50)

    # 모든 가능한 패턴 시뮬레이션
    patterns = [
        (0, 0, 0, "라인 없음 - 후진 또는 탐색 필요"),
        (0, 0, 1, "우측 가장자리 - 좌회전 필요"),
        (0, 1, 0, "중앙 정확 - 직진"),
        (0, 1, 1, "중앙-우측 - 약간 좌회전"),
        (1, 0, 0, "좌측 가장자리 - 우회전 필요"),
        (1, 0, 1, "좌측+우측 - 교차점 또는 라인 분실"),
        (1, 1, 0, "중앙-좌측 - 약간 우회전"),
        (1, 1, 1, "넓은 라인 - 직진 또는 교차점"),
    ]

    for left, middle, right, description in patterns:
        # 패턴 생성
        pattern = (left << 2) | (middle << 1) | right

        # 가상 테스트
        print(f"패턴 {left}{middle}{right} (0b{pattern:03b}): {description}")

    print("\n실제 센서로 테스트를 시작합니다...")
    test_line_sensors()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--patterns":
        # 패턴 분석 모드
        test_line_patterns()
    else:
        # 일반 테스트 모드
        test_line_sensors()
