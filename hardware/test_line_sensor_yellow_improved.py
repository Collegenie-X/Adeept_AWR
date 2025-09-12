#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
개선된 노란색 라인 센서 모듈
- 검정 배경 + 노란선 최적화
- 다중 샘플링 및 노이즈 필터링
- 동적 감도 조정
- 실시간 캘리브레이션
"""

import RPi.GPIO as GPIO
import time
import statistics


class ImprovedYellowLineSensor:
    def __init__(self):
        # 라인 센서 GPIO 핀 정의
        self.LINE_PIN_RIGHT = 19
        self.LINE_PIN_MIDDLE = 16
        self.LINE_PIN_LEFT = 20

        # 샘플링 설정
        self.SAMPLE_COUNT = 5  # 노이즈 필터링을 위한 샘플 수
        self.SAMPLE_DELAY = 0.001  # 샘플 간 지연 (1ms)

        # 캘리브레이션 데이터
        self.black_baseline = [0, 0, 0]  # 검정 배경 기준값
        self.yellow_baseline = [1, 1, 1]  # 노란선 기준값
        self.is_calibrated = False

        # 이력 데이터 (안정성 향상)
        self.sensor_history = []
        self.HISTORY_SIZE = 3

        self.setup()

    def setup(self):
        """GPIO 초기화 및 최적화"""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # 센서 핀을 입력으로 설정
        # 풀업 저항 사용 (노란선에서 더 안정적)
        GPIO.setup(self.LINE_PIN_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.LINE_PIN_MIDDLE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.LINE_PIN_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        print("✓ GPIO 초기화 완료 (풀업 저항 활성화)")

        # 초기 안정화 시간
        time.sleep(0.1)

    def read_sensors_multi_sample(self):
        """다중 샘플링으로 노이즈 제거"""
        left_samples = []
        middle_samples = []
        right_samples = []

        # 다중 샘플 수집
        for _ in range(self.SAMPLE_COUNT):
            left = GPIO.input(self.LINE_PIN_LEFT)
            middle = GPIO.input(self.LINE_PIN_MIDDLE)
            right = GPIO.input(self.LINE_PIN_RIGHT)

            left_samples.append(left)
            middle_samples.append(middle)
            right_samples.append(right)

            if self.SAMPLE_COUNT > 1:
                time.sleep(self.SAMPLE_DELAY)

        # 다수결 방식으로 안정적인 값 결정
        left_final = 1 if sum(left_samples) > self.SAMPLE_COUNT // 2 else 0
        middle_final = 1 if sum(middle_samples) > self.SAMPLE_COUNT // 2 else 0
        right_final = 1 if sum(right_samples) > self.SAMPLE_COUNT // 2 else 0

        return (left_final, middle_final, right_final)

    def read_sensors(self):
        """기본 센서 읽기 (호환성)"""
        return self.read_sensors_multi_sample()

    def add_to_history(self, sensor_data):
        """센서 데이터 이력 관리"""
        self.sensor_history.append(sensor_data)
        if len(self.sensor_history) > self.HISTORY_SIZE:
            self.sensor_history.pop(0)

    def get_stable_reading(self):
        """안정적인 센서 읽기 (이력 기반)"""
        current = self.read_sensors_multi_sample()
        self.add_to_history(current)

        if len(self.sensor_history) < self.HISTORY_SIZE:
            return current

        # 이력 데이터에서 가장 일관된 값 찾기
        left_votes = [data[0] for data in self.sensor_history]
        middle_votes = [data[1] for data in self.sensor_history]
        right_votes = [data[2] for data in self.sensor_history]

        # 다수결
        left_stable = 1 if sum(left_votes) > len(left_votes) // 2 else 0
        middle_stable = 1 if sum(middle_votes) > len(middle_votes) // 2 else 0
        right_stable = 1 if sum(right_votes) > len(right_votes) // 2 else 0

        return (left_stable, middle_stable, right_stable)

    def auto_calibrate(self):
        """자동 캘리브레이션"""
        print("\n🎯 자동 캘리브레이션 시작")
        print("=" * 50)

        # 1단계: 검정 배경 캘리브레이션
        print("1단계: 검정 배경에 로봇을 놓고 3초 기다리세요...")
        input("준비되면 Enter를 누르세요...")

        black_samples = []
        for i in range(30):
            sample = self.read_sensors_multi_sample()
            black_samples.append(sample)
            print(f"\r검정 배경 측정 중... {i+1}/30", end="", flush=True)
            time.sleep(0.1)

        # 검정 배경 기준값 계산
        self.black_baseline = [
            (
                1
                if sum(sample[i] for sample in black_samples) > len(black_samples) // 2
                else 0
            )
            for i in range(3)
        ]

        print(f"\n✓ 검정 배경 기준값: {self.black_baseline}")

        # 2단계: 노란선 캘리브레이션
        print("\n2단계: 노란선 위에 로봇을 놓고 3초 기다리세요...")
        input("준비되면 Enter를 누르세요...")

        yellow_samples = []
        for i in range(30):
            sample = self.read_sensors_multi_sample()
            yellow_samples.append(sample)
            print(f"\r노란선 측정 중... {i+1}/30", end="", flush=True)
            time.sleep(0.1)

        # 노란선 기준값 계산
        self.yellow_baseline = [
            (
                1
                if sum(sample[i] for sample in yellow_samples)
                > len(yellow_samples) // 2
                else 0
            )
            for i in range(3)
        ]

        print(f"\n✓ 노란선 기준값: {self.yellow_baseline}")

        # 캘리브레이션 결과 분석
        self.analyze_calibration()
        self.is_calibrated = True

    def analyze_calibration(self):
        """캘리브레이션 결과 분석"""
        print("\n📊 캘리브레이션 분석:")
        print("=" * 40)

        sensor_names = ["LEFT", "MIDDLE", "RIGHT"]
        all_good = True

        for i, name in enumerate(sensor_names):
            black_val = self.black_baseline[i]
            yellow_val = self.yellow_baseline[i]

            print(f"{name:6s}: 검정={black_val}, 노란={yellow_val}", end="")

            if black_val != yellow_val:
                print(" ✅ 좋음")
            else:
                print(" ❌ 차이 없음")
                all_good = False

        if all_good:
            print("\n✅ 캘리브레이션 성공! 노란선 감지 가능")
        else:
            print("\n⚠️ 캘리브레이션 문제 발견")
            print("해결 방법:")
            print("  - 센서 높이 조정 (2-3mm)")
            print("  - 조명 개선")
            print("  - 센서 청소")
            print("  - 노란선 교체 (더 밝은 색)")

    def get_line_position(self):
        """개선된 라인 위치 판단"""
        if self.is_calibrated:
            left, middle, right = self.get_stable_reading()
        else:
            left, middle, right = self.read_sensors_multi_sample()

        # 센서 상태를 이진 패턴으로 변환 (LMR)
        pattern = (left << 2) | (middle << 1) | right

        # 노란선 감지 최적화된 패턴 매핑
        position_map = {
            0b000: (None, "검정 배경 (라인 없음)"),
            0b001: (1, "우측 노란선"),
            0b010: (0, "중앙 노란선 (이상적)"),
            0b011: (0.5, "중앙-우측 노란선"),
            0b100: (-1, "좌측 노란선"),
            0b101: (None, "양쪽 노란선 (교차점)"),
            0b110: (-0.5, "중앙-좌측 노란선"),
            0b111: (0, "넓은 노란선"),
        }

        position, description = position_map.get(pattern, (0, "알 수 없음"))

        return {
            "position": position,
            "description": description,
            "pattern": f"{left}{middle}{right}",
            "binary": f"0b{pattern:03b}",
            "sensors": {"left": left, "middle": middle, "right": right},
            "calibrated": self.is_calibrated,
        }

    def get_simple_position(self):
        """간단한 위치 판단"""
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

    def test_yellow_line_detection(self):
        """노란선 감지 테스트"""
        print("\n🧪 노란선 감지 성능 테스트")
        print("=" * 60)

        if not self.is_calibrated:
            print("⚠️ 캘리브레이션이 필요합니다.")
            return

        print("실시간 노란선 감지 테스트 중...")
        print("로봇을 노란선 위에서 움직여보세요")
        print("=" * 80)
        print("시간   | 센서상태 | 위치 | 설명")
        print("=" * 80)

        try:
            start_time = time.time()
            while True:
                line_info = self.get_line_position()
                current_time = time.time() - start_time

                pos_str = (
                    f"{line_info['position']:+5.1f}"
                    if line_info["position"] is not None
                    else " None"
                )

                sensors = line_info["sensors"]
                sensor_str = f"L[{'●' if sensors['left'] else '○'}] M[{'●' if sensors['middle'] else '○'}] R[{'●' if sensors['right'] else '○'}]"

                print(
                    f"\r{current_time:5.1f}s | {sensor_str} | {pos_str} | {line_info['description']}",
                    end="",
                    flush=True,
                )

                time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n테스트 종료")

    def cleanup(self):
        """GPIO 정리"""
        GPIO.cleanup()


def main():
    """메인 테스트 함수"""
    sensor = ImprovedYellowLineSensor()

    try:
        print("🟡 개선된 노란색 라인 센서 테스트")
        print("=" * 50)

        while True:
            print("\n메뉴:")
            print("1. 자동 캘리브레이션")
            print("2. 노란선 감지 테스트")
            print("3. 원시 센서 값 모니터링")
            print("q. 종료")

            choice = input("\n선택: ").strip()

            if choice == "1":
                sensor.auto_calibrate()
            elif choice == "2":
                sensor.test_yellow_line_detection()
            elif choice == "3":
                print("원시 센서 값 모니터링 (Ctrl+C로 중단)")
                try:
                    while True:
                        left, middle, right = sensor.read_sensors_multi_sample()
                        print(
                            f"\rLEFT: {left}, MIDDLE: {middle}, RIGHT: {right}",
                            end="",
                            flush=True,
                        )
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    print("\n모니터링 중단")
            elif choice == "q":
                break
            else:
                print("잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n프로그램 중단")
    finally:
        sensor.cleanup()
        print("✅ 프로그램 종료")


if __name__ == "__main__":
    main()

