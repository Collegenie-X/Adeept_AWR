#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
노란색 라인 센서 디버깅 및 문제 해결 모듈
- 검정 배경 + 노란선 감지 문제 분석
- 센서 민감도 및 전압 레벨 확인
- 실시간 센서 값 모니터링 및 조정
"""

import RPi.GPIO as GPIO
import time


class YellowLineSensorDebugger:
    def __init__(self):
        # 라인 센서 GPIO 핀 정의
        self.LINE_PIN_RIGHT = 19
        self.LINE_PIN_MIDDLE = 16
        self.LINE_PIN_LEFT = 20

        # 센서 감도 관련 설정
        self.sensor_names = {
            self.LINE_PIN_LEFT: "LEFT",
            self.LINE_PIN_MIDDLE: "MIDDLE",
            self.LINE_PIN_RIGHT: "RIGHT",
        }

        self.setup()

    def setup(self):
        """GPIO 초기화"""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        # 센서 핀을 입력으로 설정 (풀업 저항 활성화)
        GPIO.setup(self.LINE_PIN_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.LINE_PIN_MIDDLE, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.LINE_PIN_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        print("✓ GPIO 초기화 완료 (풀업 저항 활성화)")

    def read_raw_sensors(self):
        """원시 센서 값 읽기"""
        left = GPIO.input(self.LINE_PIN_LEFT)
        middle = GPIO.input(self.LINE_PIN_MIDDLE)
        right = GPIO.input(self.LINE_PIN_RIGHT)
        return left, middle, right

    def analyze_sensor_behavior(self):
        """센서 동작 분석"""
        print("\n" + "=" * 80)
        print("🔍 노란색 라인 센서 문제 분석")
        print("=" * 80)
        print("📋 분석 목적:")
        print("  - 검정 배경에서 노란선 인식 문제 해결")
        print("  - 센서 민감도 및 신호 레벨 확인")
        print("  - 최적 감지 조건 찾기")
        print()
        print("💡 예상 동작:")
        print("  - 검정 배경: LOW(0) - 어두운 표면")
        print("  - 노란선: HIGH(1) - 밝은 표면")
        print()
        print("🔧 가능한 문제들:")
        print("  1. 센서 높이가 너무 높음/낮음")
        print("  2. 조명 부족으로 노란선이 충분히 밝지 않음")
        print("  3. 센서 민감도 조정 필요")
        print("  4. 노란색 반사율이 적외선에서 낮음")
        print("  5. 센서 오염 또는 렌즈 문제")
        print()

    def continuous_monitoring(self):
        """연속적인 센서 모니터링"""
        print("🔄 실시간 센서 모니터링 시작")
        print("검정 배경과 노란선 위에 센서를 놓고 차이를 확인하세요")
        print("=" * 90)
        print("시간     | LEFT | MID | RIGHT | 패턴 | 상태 분석")
        print("=" * 90)

        start_time = time.time()
        sample_count = 0

        try:
            while True:
                left, middle, right = self.read_raw_sensors()
                current_time = time.time() - start_time
                sample_count += 1

                # 패턴 분석
                pattern = f"{left}{middle}{right}"
                total_sensors = left + middle + right

                # 상태 분석
                if total_sensors == 0:
                    status = "완전히 검정 배경 (정상)"
                elif total_sensors == 3:
                    status = "모든 센서 노란선 감지"
                elif total_sensors == 1:
                    if left:
                        status = "좌측만 노란선"
                    elif middle:
                        status = "중앙만 노란선 (이상적)"
                    else:
                        status = "우측만 노란선"
                elif total_sensors == 2:
                    status = "두 센서 노란선 (경계)"
                else:
                    status = "알 수 없음"

                # 실시간 출력
                print(
                    f"\r{current_time:6.1f}s | {left:4d} | {middle:3d} | {right:5d} | {pattern:4s} | {status:25s}",
                    end="",
                    flush=True,
                )

                # 주기적으로 새 줄 추가 (가독성)
                if sample_count % 50 == 0:
                    print()

                time.sleep(0.1)

        except KeyboardInterrupt:
            print(f"\n\n📊 모니터링 종료 (총 {sample_count}개 샘플)")

    def calibration_test(self):
        """센서 보정 테스트"""
        print("\n🎯 센서 보정 테스트")
        print("=" * 60)
        print("단계별 테스트를 진행합니다:")
        print()

        # 1단계: 검정 배경 테스트
        input("1단계: 모든 센서를 검정 배경에 놓고 Enter를 누르세요...")
        black_samples = []
        print("검정 배경 측정 중 (3초)...")

        for i in range(30):
            left, middle, right = self.read_raw_sensors()
            black_samples.append((left, middle, right))
            time.sleep(0.1)

        # 검정 배경 분석
        black_avg = [
            sum(sample[i] for sample in black_samples) / len(black_samples)
            for i in range(3)
        ]

        print(
            f"검정 배경 평균값: L={black_avg[0]:.2f}, M={black_avg[1]:.2f}, R={black_avg[2]:.2f}"
        )

        # 2단계: 노란선 테스트
        input("\n2단계: 모든 센서를 노란선에 놓고 Enter를 누르세요...")
        yellow_samples = []
        print("노란선 측정 중 (3초)...")

        for i in range(30):
            left, middle, right = self.read_raw_sensors()
            yellow_samples.append((left, middle, right))
            time.sleep(0.1)

        # 노란선 분석
        yellow_avg = [
            sum(sample[i] for sample in yellow_samples) / len(yellow_samples)
            for i in range(3)
        ]

        print(
            f"노란선 평균값: L={yellow_avg[0]:.2f}, M={yellow_avg[1]:.2f}, R={yellow_avg[2]:.2f}"
        )

        # 결과 분석
        print("\n📊 보정 결과 분석:")
        print("=" * 60)

        for i, name in enumerate(["LEFT", "MIDDLE", "RIGHT"]):
            diff = yellow_avg[i] - black_avg[i]
            print(
                f"{name:6s} 센서: 검정={black_avg[i]:.2f}, 노란={yellow_avg[i]:.2f}, 차이={diff:+.2f}"
            )

            if abs(diff) < 0.1:
                print(f"  ⚠️  {name} 센서: 거의 차이 없음 - 조정 필요!")
            elif diff > 0.8:
                print(f"  ✅ {name} 센서: 좋은 대비")
            elif diff > 0.5:
                print(f"  🔶 {name} 센서: 보통 대비")
            else:
                print(f"  ❌ {name} 센서: 불충분한 대비")

    def hardware_check(self):
        """하드웨어 점검"""
        print("\n🔧 하드웨어 점검")
        print("=" * 50)
        print("점검 항목:")
        print("1. 센서와 도로 거리: 2-5mm 권장")
        print("2. 센서 청결도: 렌즈에 먼지나 오염 확인")
        print("3. 조명 조건: 충분한 조명 필요")
        print("4. 노란선 색상: 형광 노란색이 가장 효과적")
        print("5. 배경 색상: 무광 검정색이 가장 효과적")
        print()

        # 연결 상태 확인
        print("📡 GPIO 연결 상태 확인:")
        pins = [self.LINE_PIN_LEFT, self.LINE_PIN_MIDDLE, self.LINE_PIN_RIGHT]
        names = ["LEFT", "MIDDLE", "RIGHT"]

        for pin, name in zip(pins, names):
            try:
                value = GPIO.input(pin)
                print(
                    f"  {name:6s} (GPIO {pin:2d}): {'연결됨' if value in [0, 1] else '오류'}"
                )
            except Exception as e:
                print(f"  {name:6s} (GPIO {pin:2d}): 오류 - {e}")

    def solution_recommendations(self):
        """해결책 제안"""
        print("\n💡 노란선 인식 개선 방법")
        print("=" * 60)
        print("🔧 하드웨어 조정:")
        print("  1. 센서 높이 조정: 2-3mm가 최적")
        print("  2. 센서 청소: 알코올로 렌즈 청소")
        print("  3. 조명 추가: LED 조명으로 균일한 조명 제공")
        print("  4. 센서 각도: 수직으로 정확히 정렬")
        print()
        print("🎨 도로 개선:")
        print("  1. 노란선 교체: 형광 노란색 테이프 사용")
        print("  2. 배경 개선: 무광 검정 테이프/페인트")
        print("  3. 선 폭 조정: 15-20mm 폭이 적당")
        print("  4. 표면 평활화: 울퉁불퉁한 표면 제거")
        print()
        print("⚙️ 소프트웨어 조정:")
        print("  1. 풀업/풀다운 저항 설정 변경")
        print("  2. 샘플링 속도 조정")
        print("  3. 노이즈 필터링 추가")
        print("  4. 다중 샘플 평균화")

    def cleanup(self):
        """GPIO 정리"""
        GPIO.cleanup()


def main():
    """메인 테스트 함수"""
    debugger = YellowLineSensorDebugger()

    try:
        debugger.analyze_sensor_behavior()
        debugger.hardware_check()

        while True:
            print("\n" + "=" * 60)
            print("🛠️  노란색 라인 센서 디버깅 메뉴")
            print("=" * 60)
            print("1. 실시간 센서 모니터링")
            print("2. 센서 보정 테스트")
            print("3. 해결책 제안")
            print("4. 하드웨어 점검")
            print("q. 종료")
            print()

            choice = input("선택 (1-4, q): ").strip().lower()

            if choice == "1":
                debugger.continuous_monitoring()
            elif choice == "2":
                debugger.calibration_test()
            elif choice == "3":
                debugger.solution_recommendations()
            elif choice == "4":
                debugger.hardware_check()
            elif choice == "q":
                break
            else:
                print("❌ 잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n프로그램 중단됨")
    finally:
        debugger.cleanup()
        print("✅ GPIO 정리 완료")


if __name__ == "__main__":
    main()

