#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WS2812 LED 스트립 테스트 모듈
- Motor HAT의 WS2812 인터페이스 연결 (GPIO 12)
- 체인 연결: IN → OUT 방향으로 신호선 연결
- 16개 LED 개별 제어 및 색상 패턴 테스트
- 로봇 상태별 시각적 피드백 제공

연결 방법:
- WS2812 모듈을 Motor HAT의 WS2812 인터페이스에 3핀 케이블로 연결
- 다중 모듈 연결 시: 이전 모듈 OUT → 다음 모듈 IN
- 신호선 방향 주의: 라즈베리파이 → 첫 번째 모듈 IN
"""

import time
import threading
from typing import Tuple, Optional
from enum import Enum

try:
    from rpi_ws281x import Adafruit_NeoPixel, Color

    WS281X_AVAILABLE = True
except ImportError:
    print("경고: rpi_ws281x 라이브러리를 찾을 수 없습니다.")
    print("설치 명령어: pip3 install rpi-ws281x")
    print("또는: sudo pip3 install rpi-ws281x")
    print("주의: root 권한이 필요할 수 있습니다.")
    WS281X_AVAILABLE = False


class RobotState(Enum):
    """로봇 상태 열거형"""

    IDLE = "idle"
    MOVING = "moving"
    OBSTACLE = "obstacle"
    LINE_FOLLOWING = "line_following"
    LOST = "lost"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class LEDStripController:
    def __init__(self):
        # WS2812 LED 하드웨어 설정 (Motor HAT 기준)
        self.LED_COUNT = 16  # 로봇 제품의 총 LED 개수
        self.LED_PIN = 12  # Motor HAT WS2812 인터페이스 (GPIO 12)
        self.LED_FREQ_HZ = 800000  # LED 신호 주파수 (일반적으로 800kHz)
        self.LED_DMA = 10  # 신호 생성용 DMA 채널 (10 사용)
        self.LED_BRIGHTNESS = 255  # 밝기 설정 (0=가장 어두움, 255=가장 밝음)
        self.LED_INVERT = False  # 신호 반전 (NPN 트랜지스터 레벨 시프트 시 True)
        self.LED_CHANNEL = 0  # GPIO 13,19,41,45,53 사용 시 '1'로 설정

        # 제어 변수
        self.strip = None
        self.animation_running = False
        self.animation_thread = None

        # 상태별 색상 정의 (R, G, B)
        self.state_colors = {
            RobotState.IDLE: (0, 0, 50),  # 어두운 파랑
            RobotState.MOVING: (0, 255, 0),  # 초록
            RobotState.OBSTACLE: (255, 255, 0),  # 노랑
            RobotState.LINE_FOLLOWING: (0, 255, 255),  # 시안
            RobotState.LOST: (255, 100, 0),  # 주황
            RobotState.ERROR: (255, 0, 0),  # 빨강
            RobotState.SHUTDOWN: (100, 0, 100),  # 보라
        }

        self.setup()

    def setup(self):
        """LED 스트립 초기화"""
        if not WS281X_AVAILABLE:
            print("LED 라이브러리가 없어 시뮬레이션 모드로 실행됩니다.")
            return False

        # 권한 확인
        import os

        if os.getuid() != 0:
            print("경고: WS2812 제어를 위해 root 권한이 필요합니다.")
            print("다음 명령어로 실행하세요: sudo python3 test_led_strip.py")
            print("시뮬레이션 모드로 계속 실행합니다...\n")
            return False

        try:
            # NeoPixel 객체 생성
            self.strip = Adafruit_NeoPixel(
                self.LED_COUNT,
                self.LED_PIN,
                self.LED_FREQ_HZ,
                self.LED_DMA,
                self.LED_INVERT,
                self.LED_BRIGHTNESS,
                self.LED_CHANNEL,
            )

            # 라이브러리 초기화
            self.strip.begin()

            # 모든 LED 끄기
            self.clear_all()
            print("LED 스트립 초기화 완료")
            return True

        except Exception as e:
            print(f"LED 초기화 오류: {e}")
            if "Permission denied" in str(e):
                print("권한 문제입니다. sudo로 실행하세요.")
            elif "mmap() failed" in str(e):
                print(
                    "메모리 매핑 실패. DMA 채널을 확인하거나 다른 채널을 시도해보세요."
                )
            print("시뮬레이션 모드로 계속 실행합니다...\n")
            return False

    def set_pixel_color(self, pixel: int, r: int, g: int, b: int):
        """
        개별 LED 색상 설정
        :param pixel: LED 번호 (0부터 시작, 첫 번째 LED=0, 두 번째 LED=1...)
        :param r: 빨강 밝기 (0-255)
        :param g: 초록 밝기 (0-255)
        :param b: 파랑 밝기 (0-255)
        주의: Color() 메서드로 RGB 값을 패킹한 후 setPixelColor에 전달해야 함
        """
        if not WS281X_AVAILABLE or not self.strip:
            print(f"시뮬레이션: LED[{pixel}] = RGB({r}, {g}, {b})")
            return

        if 0 <= pixel < self.LED_COUNT:
            # Color() 메서드로 RGB 값 패킹 (문서 요구사항)
            color = Color(r, g, b)
            self.strip.setPixelColor(pixel, color)

    def set_all_pixels(self, r: int, g: int, b: int):
        """모든 픽셀 동일 색상 설정"""
        for i in range(self.LED_COUNT):
            self.set_pixel_color(i, r, g, b)

    def clear_all(self):
        """모든 LED 끄기"""
        if not WS281X_AVAILABLE or not self.strip:
            print("시뮬레이션: 모든 LED 끄기")
            return

        try:
            for i in range(self.LED_COUNT):
                self.set_pixel_color(i, 0, 0, 0)
            self.show()
        except Exception as e:
            print(f"LED 끄기 오류: {e}")

    def show(self):
        """
        LED 변경사항 적용
        주의: show() 메서드 호출 후에만 색상 변경이 적용됨
        """
        if WS281X_AVAILABLE and self.strip:
            self.strip.show()

    def colorWipe(self, r: int, g: int, b: int):
        """
        모든 LED를 동일한 색상으로 변경 (문서 표준 메서드)
        :param r: 빨강 밝기 (0-255)
        :param g: 초록 밝기 (0-255)
        :param b: 파랑 밝기 (0-255)

        사용 예:
        LED.colorWipe(255, 0, 0)  # 모든 LED를 빨강으로
        LED.colorWipe(0, 255, 0)  # 모든 LED를 초록으로
        LED.colorWipe(0, 0, 255)  # 모든 LED를 파랑으로
        """
        if not WS281X_AVAILABLE or not self.strip:
            print(f"시뮬레이션: 모든 LED = RGB({r}, {g}, {b})")
            return

        try:
            color = Color(r, g, b)
            # 한 번에 하나의 LED 색상만 설정 가능하므로 루프 필요
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, color)
            # show() 메서드 호출 후에만 색상 변경됨
            self.strip.show()
        except Exception as e:
            print(f"LED 제어 오류: {e}")
            print("시뮬레이션 모드로 전환합니다.")

    def set_state_color(self, state: RobotState):
        """로봇 상태에 따른 색상 설정"""
        r, g, b = self.state_colors[state]
        self.colorWipe(r, g, b)  # 표준 colorWipe 메서드 사용
        print(f"상태: {state.value} -> 색상: RGB({r}, {g}, {b})")

    def color_wipe_animation(self, r: int, g: int, b: int, wait_ms: int = 50):
        """색상을 순차적으로 채우는 애니메이션 효과"""
        for i in range(self.LED_COUNT):
            self.set_pixel_color(i, r, g, b)
            self.show()
            time.sleep(wait_ms / 1000.0)

    def rainbow_cycle(self, iterations: int = 1, wait_ms: int = 20):
        """무지개 색상 순환"""
        for j in range(256 * iterations):
            for i in range(self.LED_COUNT):
                color = self._wheel(((i * 256 // self.LED_COUNT) + j) & 255)
                (
                    self.strip.setPixelColor(i, color)
                    if WS281X_AVAILABLE and self.strip
                    else None
                )
            self.show()
            time.sleep(wait_ms / 1000.0)

    def _wheel(self, pos: int):
        """색상 휠 (0-255 범위의 색상 생성)"""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)

    def blink_pattern(
        self, r: int, g: int, b: int, times: int = 3, interval: float = 0.5
    ):
        """깜빡임 패턴"""
        for _ in range(times):
            self.set_all_pixels(r, g, b)
            self.show()
            time.sleep(interval)

            self.clear_all()
            time.sleep(interval)

    def breathing_effect(self, r: int, g: int, b: int, duration: float = 3.0):
        """숨쉬기 효과 (밝기 조절)"""
        if not WS281X_AVAILABLE or not self.strip:
            print(f"시뮬레이션: 숨쉬기 효과 RGB({r}, {g}, {b})")
            return

        steps = 50
        for cycle in range(2):  # 2번 숨쉬기
            # 밝아지기
            for i in range(steps):
                brightness = int((i / steps) * 255)
                self.strip.setBrightness(brightness)
                self.set_all_pixels(r, g, b)
                self.show()
                time.sleep(duration / (steps * 4))

            # 어두워지기
            for i in range(steps):
                brightness = int(((steps - i) / steps) * 255)
                self.strip.setBrightness(brightness)
                self.set_all_pixels(r, g, b)
                self.show()
                time.sleep(duration / (steps * 4))

        # 밝기 원래대로
        self.strip.setBrightness(self.LED_BRIGHTNESS)
        self.clear_all()

    def turn_off_all(self):
        """모든 LED 끄기 (문서 표준 방법)"""
        self.colorWipe(0, 0, 0)

    def demonstrate_basic_cycle(self):
        """문서 예제: 기본 3색 순환"""
        try:
            while True:
                self.colorWipe(255, 0, 0)  # 모든 LED 빨강
                time.sleep(1)
                self.colorWipe(0, 255, 0)  # 모든 LED 초록
                time.sleep(1)
                self.colorWipe(0, 0, 255)  # 모든 LED 파랑
                time.sleep(1)
        except KeyboardInterrupt:
            # CTRL+C로 프로그램 종료 시 모든 LED 끄기
            self.turn_off_all()

    def cleanup(self):
        """정리 및 종료"""
        self.animation_running = False
        if self.animation_thread:
            self.animation_thread.join()
        self.turn_off_all()  # 표준 끄기 방법 사용
        print("LED 스트립 정리 완료")


def test_led_strip():
    """LED 스트립 테스트 함수"""
    # 권한 확인 안내
    import os

    if os.getuid() != 0 and WS281X_AVAILABLE:
        print("🚨 WS2812 LED 제어 권한 안내 🚨")
        print("=" * 50)
        print("실제 LED 제어를 위해서는 root 권한이 필요합니다.")
        print("다음 명령어로 실행하세요:")
        print("  sudo python3 hardware/test_led_strip.py")
        print("")
        print("현재는 시뮬레이션 모드로 실행됩니다.")
        print("=" * 50)
        print("")

    controller = LEDStripController()

    try:
        print("LED 스트립 테스트를 시작합니다...")
        print("=" * 50)

        # 기본 색상 테스트
        print("\n1. 기본 색상 테스트")
        colors = [
            ("빨강", 255, 0, 0),
            ("초록", 0, 255, 0),
            ("파랑", 0, 0, 255),
            ("흰색", 255, 255, 255),
        ]

        for name, r, g, b in colors:
            print(f"  - {name} 색상 표시")
            controller.colorWipe(r, g, b)  # 표준 메서드 사용
            time.sleep(2)

        controller.clear_all()
        time.sleep(1)

        # 로봇 상태별 색상 테스트
        print("\n2. 로봇 상태별 색상 테스트")
        for state in RobotState:
            print(f"  - {state.value} 상태 색상")
            controller.set_state_color(state)
            time.sleep(2)

        controller.clear_all()
        time.sleep(1)

        # 색상 와이프 애니메이션 테스트
        print("\n3. 색상 와이프 애니메이션 효과")
        controller.color_wipe_animation(255, 0, 0, 50)  # 빨강 순차 점등
        controller.color_wipe_animation(0, 255, 0, 50)  # 초록 순차 점등
        controller.color_wipe_animation(0, 0, 255, 50)  # 파랑 순차 점등

        controller.clear_all()
        time.sleep(1)

        # 깜빡임 테스트
        print("\n4. 깜빡임 패턴 테스트")
        controller.blink_pattern(255, 255, 0, times=5, interval=0.3)  # 노랑 깜빡임

        # 숨쉬기 효과 테스트
        print("\n5. 숨쉬기 효과 테스트")
        controller.breathing_effect(0, 255, 255, duration=4.0)  # 시안 숨쉬기

        # 개별 LED 제어 테스트
        print("\n6. 개별 LED 제어 테스트")
        controller.turn_off_all()
        for i in range(min(5, controller.LED_COUNT)):  # 처음 5개 LED 테스트
            print(f"  - LED {i} 빨강 점등")
            if WS281X_AVAILABLE and controller.strip:
                try:
                    controller.strip.setPixelColor(i, Color(255, 0, 0))
                    controller.strip.show()
                except Exception as e:
                    print(f"LED {i} 제어 오류: {e}")
            else:
                print(f"시뮬레이션: LED[{i}] = 빨강")
            time.sleep(0.5)

        controller.turn_off_all()
        time.sleep(1)

        # 무지개 효과 테스트 (실제 하드웨어에서만)
        if WS281X_AVAILABLE and controller.strip:
            print("\n7. 무지개 효과 테스트")
            controller.rainbow_cycle(iterations=2, wait_ms=20)

        # 문서 표준 예제 테스트
        print("\n8. 문서 표준 3색 순환 테스트 (3회)")
        for cycle in range(3):
            print(f"  순환 {cycle + 1}/3")
            controller.colorWipe(255, 0, 0)  # 빨강
            time.sleep(0.8)
            controller.colorWipe(0, 255, 0)  # 초록
            time.sleep(0.8)
            controller.colorWipe(0, 0, 255)  # 파랑
            time.sleep(0.8)

        print("\nLED 테스트 완료!")

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    finally:
        controller.cleanup()


def test_basic_cycle():
    """문서 표준 3색 무한 순환 테스트"""
    print("문서 표준 3색 순환 테스트")
    print("CTRL+C를 눌러 종료하세요.")

    controller = LEDStripController()
    controller.demonstrate_basic_cycle()


def test_individual_leds():
    """개별 LED 제어 테스트"""
    print("개별 LED 제어 테스트")
    controller = LEDStripController()

    try:
        print(f"총 {controller.LED_COUNT}개 LED를 순차적으로 테스트합니다.")

        for i in range(controller.LED_COUNT):
            print(f"LED {i} 테스트 중...")

            # 개별 LED를 다양한 색상으로 테스트
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
            color_names = ["빨강", "초록", "파랑"]

            for (r, g, b), name in zip(colors, color_names):
                if WS281X_AVAILABLE and controller.strip:
                    controller.strip.setPixelColor(i, Color(r, g, b))
                    controller.strip.show()
                else:
                    print(f"시뮬레이션: LED[{i}] = {name}")
                time.sleep(0.3)

            # LED 끄기
            if WS281X_AVAILABLE and controller.strip:
                controller.strip.setPixelColor(i, Color(0, 0, 0))
                controller.strip.show()

        print("개별 LED 테스트 완료!")

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다.")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "--basic":
            # 문서 표준 3색 무한 순환
            test_basic_cycle()
        elif mode == "--individual":
            # 개별 LED 테스트
            test_individual_leds()
        elif mode == "--help":
            print("WS2812 LED 스트립 테스트 모드:")
            print("  기본 모드:     python3 test_led_strip.py")
            print("  3색 순환:     python3 test_led_strip.py --basic")
            print("  개별 LED:     python3 test_led_strip.py --individual")
            print("  도움말:       python3 test_led_strip.py --help")
            print("")
            print("🚨 중요: 실제 LED 제어를 위해서는 root 권한 필요")
            print("  sudo python3 test_led_strip.py")
            print("")
            print("연결 방법:")
            print("  - Motor HAT의 WS2812 인터페이스에 3핀 케이블로 연결")
            print("  - GPIO 12번 핀 사용")
            print("  - 체인 연결: IN → OUT 방향")
            print("")
            print("문제 해결:")
            print("  Permission denied: sudo로 실행")
            print("  mmap() failed: DMA 채널 확인 또는 재부팅")
            print("  Segmentation fault: 하드웨어 연결 확인")
        else:
            print(f"알 수 없는 모드: {mode}")
            print("--help 옵션으로 사용법을 확인하세요.")
    else:
        # 기본 종합 테스트
        test_led_strip()
