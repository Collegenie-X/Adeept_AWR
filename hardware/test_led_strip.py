#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WS2812 LED 스트립 테스트 모듈 (간결 버전)
- pip3 install rpi-ws281x 라이브러리 사용
- GPIO 12번 핀 연결, 16개 LED 제어
- 간단한 함수형 접근법으로 재작성
"""

import time

# 라이브러리 import 및 의존성 체크
try:
    from rpi_ws281x import Adafruit_NeoPixel, Color

    LIBRARY_AVAILABLE = True
except ImportError:
    print("Error: rpi_ws281x library is required.")
    print("Install command: pip3 install rpi-ws281x")
    print("Warning: sudo permission may be required.")
    LIBRARY_AVAILABLE = False


# LED 하드웨어 설정 (이미지 문서 기준)
LED_COUNT = 16  # 로봇 제품의 총 LED 개수
LED_PIN = 12  # GPIO 12번 핀 사용
LED_FREQ_HZ = 800000  # 800kHz 주파수
LED_DMA = 10  # DMA 채널
LED_BRIGHTNESS = 255  # 최대 밝기
LED_INVERT = False  # 신호 반전 없음
LED_CHANNEL = 0  # 채널 0 사용

# 전역 변수로 LED 스트립 객체 관리
strip = None


def setup():
    """LED 스트립 초기화 (이미지 문서 스타일)"""
    global strip

    if not LIBRARY_AVAILABLE:
        print("Running in simulation mode.")
        return False

    # 권한 확인
    import os

    if os.getuid() != 0:
        print("Warning: Root permission required for WS2812 control.")
        print("Run command: sudo python3 test_led_strip.py")
        print("Continuing in simulation mode...\n")
        return False

    try:
        # 이미지 문서와 동일한 설정으로 NeoPixel 객체 생성
        strip = Adafruit_NeoPixel(
            LED_COUNT,
            LED_PIN,
            LED_FREQ_HZ,
            LED_DMA,
            LED_INVERT,
            LED_BRIGHTNESS,
            LED_CHANNEL,
        )

        # 라이브러리 초기화
        strip.begin()

        print("LED strip initialization completed.")
        return True

    except Exception as e:
        print(f"LED initialization error: {e}")
        if "Permission denied" in str(e):
            print("Permission issue: Please run with sudo.")
        elif "mmap() failed" in str(e):
            print("Memory mapping failed: Check DMA channel.")
        print("Switching to simulation mode...\n")
        return False


def colorWipe(R, G, B):
    """
    모든 LED를 동일한 색상으로 변경 (이미지 문서 표준 함수)
    :param R: 빨강 밝기 (0-255)
    :param G: 초록 밝기 (0-255)
    :param B: 파랑 밝기 (0-255)
    """
    if not LIBRARY_AVAILABLE or not strip:
        print(f"Simulation: All LEDs = RGB({R}, {G}, {B})")
        return

    try:
        # 이미지 문서 방식: Color() 메서드로 RGB 값 패킹
        color = Color(R, G, B)
        # 한 번에 하나의 LED 색상만 설정 가능하므로 루프 필요
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, color)
        # show() 메서드 호출 후에만 색상 변경됨
        strip.show()
    except Exception as e:
        print(f"LED control error: {e}")


def set_single_led(led_num, R, G, B):
    """
    개별 LED 색상 설정 (이미지 문서 예제 방식)
    :param led_num: LED 번호 (0부터 시작)
    :param R: 빨강 밝기 (0-255)
    :param G: 초록 밝기 (0-255)
    :param B: 파랑 밝기 (0-255)
    """
    if not LIBRARY_AVAILABLE or not strip:
        print(f"Simulation: LED[{led_num}] = RGB({R}, {G}, {B})")
        return

    try:
        if 0 <= led_num < LED_COUNT:
            # 이미지 문서 예제와 동일한 방식
            strip.setPixelColor(led_num, Color(R, G, B))
            strip.show()
    except Exception as e:
        print(f"LED[{led_num}] control error: {e}")


def turn_off_all():
    """모든 LED 끄기 (이미지 문서 방식)"""
    colorWipe(0, 0, 0)


def basic_color_cycle():
    """이미지 문서 예제: 기본 3색 순환"""
    try:
        while True:
            colorWipe(255, 0, 0)  # 모든 LED 빨강
            time.sleep(1)
            colorWipe(0, 255, 0)  # 모든 LED 초록
            time.sleep(1)
            colorWipe(0, 0, 255)  # 모든 LED 파랑
            time.sleep(1)
    except KeyboardInterrupt:
        turn_off_all()  # CTRL+C 종료 시 모든 LED 끄기


def test_individual_leds():
    """개별 LED 테스트 (이미지 문서 방식)"""
    print("Individual LED test started.")

    # 각 LED를 차례로 빨강으로 점등
    for i in range(LED_COUNT):
        print(f"Testing LED {i}")
        set_single_led(i, 255, 0, 0)  # 빨강으로 점등
        time.sleep(0.3)

    turn_off_all()
    print("Individual LED test completed.")


def test_basic_sequence():
    """기본 테스트 시퀀스"""
    print("LED strip basic test started.")
    print("=" * 40)

    # 1. 기본 색상 테스트
    print("\n1. Basic color test")
    colors = [
        ("Red", 255, 0, 0),
        ("Green", 0, 255, 0),
        ("Blue", 0, 0, 255),
        ("White", 255, 255, 255),
        ("Yellow", 255, 255, 0),
        ("Cyan", 0, 255, 255),
        ("Magenta", 255, 0, 255),
    ]

    for name, r, g, b in colors:
        print(f"  > Displaying {name}")
        colorWipe(r, g, b)
        time.sleep(1.5)

    # 2. 개별 LED 테스트
    print("\n2. Individual LED control test")
    test_individual_leds()

    # 3. 문서 표준 3색 순환 (제한된 횟수)
    print("\n3. Standard 3-color cycle test (5 times)")
    for cycle in range(5):
        print(f"  Cycle {cycle + 1}/5")
        colorWipe(255, 0, 0)  # 빨강
        time.sleep(0.7)
        colorWipe(0, 255, 0)  # 초록
        time.sleep(0.7)
        colorWipe(0, 0, 255)  # 파랑
        time.sleep(0.7)

    turn_off_all()
    print("\nAll tests completed!")


def cleanup():
    """정리 작업"""
    turn_off_all()
    print("LED cleanup completed.")


if __name__ == "__main__":
    import sys

    # 권한 안내 표시
    import os

    if os.getuid() != 0 and LIBRARY_AVAILABLE:
        print("WS2812 LED Control Permission Notice")
        print("=" * 50)
        print("Root permission is required for actual LED control.")
        print("Run command: sudo python3 hardware/test_led_strip.py")
        print("Currently running in simulation mode.")
        print("=" * 50)
        print("")

    try:
        print("WS2812 LED Strip Test Program")
        print("=" * 50)
        setup()

        if len(sys.argv) > 1:
            mode = sys.argv[1]
            if mode == "--basic":
                # Document standard 3-color infinite cycle
                print("Mode: Basic 3-color infinite cycle")
                print("Press CTRL+C to exit.")
                basic_color_cycle()
            elif mode == "--individual":
                # Individual LED test
                print("Mode: Individual LED test")
                test_individual_leds()
            elif mode == "--help":
                print("WS2812 LED Strip Test Usage:")
                print("  Basic test:        python3 test_led_strip.py")
                print("  3-color infinite:  python3 test_led_strip.py --basic")
                print("  Individual LED:    python3 test_led_strip.py --individual")
                print("  Help:              python3 test_led_strip.py --help")
                print("")
                print("Important: Root permission required for actual LED control")
                print("  sudo python3 test_led_strip.py")
                print("")
                print("Connection:")
                print("  - Using GPIO pin 12")
                print("  - 16 LED support")
                print("  - Motor HAT WS2812 interface connection")
                print("")
                print("Troubleshooting:")
                print("  Permission denied: Run with sudo")
                print("  mmap() failed: Check DMA channel or reboot")
            else:
                print(f"Unknown mode: {mode}")
                print("Use --help option to check usage.")
        else:
            # 기본 종합 테스트
            test_basic_sequence()

    except KeyboardInterrupt:
        print("\nUser interrupted the program.")
    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        cleanup()
 