#!/usr/bin/python3
# 파일명      : LED.py
# 설명        : WS2812(NeoPixel) 제어
# 참고        : https://github.com/rpi-ws281x/rpi-ws281x-python
# 작성        : original code by Tony DiCola (tony@tonydicola.com)
# 개정        : 안전 초기화/권한 검사/정리 로직 보강
import os
import sys
import time
from rpi_ws281x import *

# LED 스트립 기본 설정:
LED_COUNT = 16  # LED 픽셀 수
LED_PIN = 12  # GPIO 핀 (PWM 모드: 12/18/40/52 on ch 0, 13/19/41/45/53 on ch 1)
# LED_PIN       = 10      # SPI 사용 시: /dev/spidev0.0 (라이브러리/배선 변경 필요)
LED_FREQ_HZ = 800000  # 신호 주파수(Hz)
LED_DMA = 10  # DMA 채널(권장: 10)
LED_BRIGHTNESS = 255  # 0(최저광) ~ 255(최고광)
LED_INVERT = False  # NPN 레벨시프터 사용 시 True
LED_CHANNEL = 0  # 채널 0: 12/18/40/52, 채널 1: 13/19/41/45/53

BREATH = 1
color = "yellow"
FRE_TIME = 50
DELY = 0.1


def require_root_or_exit():
    """루트 권한 필수 검사. 부족 시 안내 후 종료."""
    if os.geteuid() != 0:
        print("[오류] WS281x(PWM/PCM) 구동에는 루트 권한이 필요합니다.")
        print("- 해결 1: sudo로 실행 (권장): sudo python3 hardware/LED.py")
        print("- 해결 2: SPI 모드 사용으로 전환 (하드웨어/라이브러리 설정 변경 필요)")
        sys.exit(1)


class LED:
    def __init__(self):
        """WS2812 LED 초기화. 루트 권한 확인 후 스트립 시작."""
        require_root_or_exit()

        self.LED_COUNT = LED_COUNT
        self.LED_PIN = LED_PIN
        self.LED_FREQ_HZ = LED_FREQ_HZ
        self.LED_DMA = LED_DMA
        self.LED_BRIGHTNESS = LED_BRIGHTNESS
        self.LED_INVERT = LED_INVERT
        self.LED_CHANNEL = LED_CHANNEL

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

        # 라이브러리 초기화 (예외 핸들링)
        try:
            self.strip.begin()
        except Exception as exc:
            print("[오류] WS281x 초기화 실패: {}".format(exc))
            print(
                "- 'Can't open /dev/mem: Permission denied' 발생 시 sudo로 실행하세요."
            )
            print("- 하드웨어 연결/핀 설정(LED_PIN, LED_CHANNEL)도 확인하세요.")
            raise

    # LED 연출 함수들
    def colorWipe(self, color, wait_ms=0):
        """좌->우로 지정 색을 채우는 기본 효과."""
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
            self.strip.show()
            if wait_ms and wait_ms > 0:
                time.sleep(wait_ms / 1000.0)

    def breath_status_set(self, status):
        global BREATH
        BREATH = status

    def breath_color_set(self, invar):
        global color
        color = invar

    def breath_frequency_set(self, frequency_input):
        global FRE_TIME
        FRE_TIME = frequency_input

    def breath(self, brightness):
        """호흡(밝기 상하) 애니메이션. 무한 루프."""
        while 1:
            if BREATH:
                if color == "red":
                    for a in range(0, brightness, FRE_TIME):
                        if not BREATH:
                            break
                        else:
                            self.colorWipe(Color(a, 0, 0))
                            time.sleep(DELY)
                    for b in range(0, brightness, FRE_TIME):
                        if not BREATH:
                            break
                        else:
                            self.colorWipe(Color(((brightness - 1) - b), 0, 0))
                            time.sleep(DELY)
                elif color == "green":
                    for a in range(0, brightness, FRE_TIME):
                        if not BREATH:
                            break
                        else:
                            self.colorWipe(Color(0, a, 0))
                            time.sleep(DELY)
                    for b in range(0, brightness, FRE_TIME):
                        if not BREATH:
                            break
                        else:
                            self.colorWipe(Color(0, ((brightness - 1) - b), 0))
                            time.sleep(DELY)
                elif color == "yellow":
                    for a in range(0, brightness, FRE_TIME):
                        if not BREATH:
                            break
                        else:
                            self.colorWipe(Color(a, a, 0))
                            time.sleep(DELY)
                    for b in range(0, brightness, FRE_TIME):
                        if not BREATH:
                            break
                        else:
                            self.colorWipe(
                                Color(((brightness - 1) - b), ((brightness - 1) - b), 0)
                            )
                            time.sleep(DELY)
                elif color == "blue":
                    for a in range(0, brightness, FRE_TIME):
                        if not BREATH:
                            break
                        else:
                            self.colorWipe(Color(0, a, a))
                            time.sleep(DELY)
                    for b in range(0, brightness, FRE_TIME):
                        if not BREATH:
                            break
                        else:
                            self.colorWipe(
                                Color(0, ((brightness - 1) - b), ((brightness - 1) - b))
                            )
                            time.sleep(DELY)
            else:
                time.sleep(0.2)

    def turnOff(self):
        """모든 LED 끄기(검정)."""
        self.colorWipe(Color(0, 0, 0))


# led=LED()
# led.breath(255)
# led.colorWipe(Color(0,0,0))

if __name__ == "__main__":
    # 메인 테스트 루프: 루트 권한 필요
    led = LED()
    try:
        while True:
            led.colorWipe(Color(255, 0, 0))  # red
            time.sleep(1)
            led.colorWipe(Color(0, 255, 0))  # green
            time.sleep(1)
            led.colorWipe(Color(0, 0, 255))  # blue
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print("[예외] LED 실행 중 오류: {}".format(exc))
    finally:
        led.turnOff()  # Lights out
