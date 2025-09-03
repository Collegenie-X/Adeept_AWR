#!/usr/bin/env python3
# 파일명: led_controller.py
# 설명: WS2812 LED 스트립 제어 모듈
# 작성일: 2024
"""
WS2812 LED 스트립을 이용한 상태 표시 및 시각적 피드백 모듈
- 로봇 상태별 LED 패턴 제어
- 색상별 의미 부여 (빨강: 위험, 노랑: 주의, 초록: 안전 등)
- 애니메이션 효과 지원
"""

import time
import threading
from typing import Tuple, Optional, List, Dict
from enum import Enum

try:
    from rpi_ws281x import Adafruit_NeoPixel, Color
    WS281X_AVAILABLE = True
except ImportError:
    print("경고: rpi_ws281x 라이브러리를 찾을 수 없습니다. LED 기능이 비활성화됩니다.")
    WS281X_AVAILABLE = False


class RobotState(Enum):
    """로봇 상태 열거형"""
    IDLE = "idle"              # 대기 상태
    MOVING = "moving"          # 이동 중
    OBSTACLE = "obstacle"      # 장애물 감지
    LINE_FOLLOWING = "line_following"  # 라인 추적 중
    LOST = "lost"              # 라인 분실
    ERROR = "error"            # 오류 상태
    SHUTDOWN = "shutdown"      # 종료 중


class LEDController:
    """LED 스트립 컨트롤러 클래스"""
    
    def __init__(self, led_count: int = 16, led_pin: int = 12):
        """LED 컨트롤러 초기화"""
        # LED 스트립 설정
        self.led_count = led_count           # LED 개수
        self.led_pin = led_pin              # GPIO 핀 번호
        self.led_freq_hz = 800000           # 신호 주파수 (800kHz)
        self.led_dma = 10                   # DMA 채널
        self.led_brightness = 255           # 밝기 (0-255)
        self.led_invert = False             # 신호 반전 여부
        self.led_channel = 0                # LED 채널
        
        # NeoPixel 객체
        self.strip: Optional[Adafruit_NeoPixel] = None
        
        # 애니메이션 제어
        self.animation_thread: Optional[threading.Thread] = None
        self.animation_running = False
        self.current_state = RobotState.IDLE
        
        # 초기화 상태
        self.is_initialized = False
        
        # 상태별 색상 정의 (RGB)
        self.state_colors = {
            RobotState.IDLE: (0, 0, 50),           # 어두운 파랑
            RobotState.MOVING: (0, 255, 0),        # 초록
            RobotState.OBSTACLE: (255, 255, 0),    # 노랑
            RobotState.LINE_FOLLOWING: (0, 255, 255),  # 시안
            RobotState.LOST: (255, 100, 0),        # 주황
            RobotState.ERROR: (255, 0, 0),         # 빨강
            RobotState.SHUTDOWN: (100, 0, 100)     # 보라
        }
    
    def initialize_led(self) -> bool:
        """LED 스트립 초기화"""
        if not WS281X_AVAILABLE:
            print("LED 라이브러리가 없어 LED 기능을 비활성화합니다.")
            return False
        
        try:
            # NeoPixel 객체 생성
            self.strip = Adafruit_NeoPixel(
                self.led_count,
                self.led_pin,
                self.led_freq_hz,
                self.led_dma,
                self.led_invert,
                self.led_brightness,
                self.led_channel
            )
            
            # 라이브러리 초기화
            self.strip.begin()
            
            # 모든 LED 끄기
            self.clear_all()
            
            self.is_initialized = True
            print("LED 컨트롤러 초기화 완료")
            return True
            
        except Exception as e:
            print(f"LED 초기화 오류: {e}")
            return False
    
    def _check_initialization(self) -> bool:
        """초기화 상태 확인"""
        if not self.is_initialized or not WS281X_AVAILABLE:
            return False
        return True
    
    def set_pixel_color(self, pixel: int, r: int, g: int, b: int) -> None:
        """개별 픽셀 색상 설정"""
        if not self._check_initialization():
            return
        
        if 0 <= pixel < self.led_count:
            color = Color(r, g, b)
            self.strip.setPixelColor(pixel, color)
    
    def set_all_pixels(self, r: int, g: int, b: int) -> None:
        """모든 픽셀 동일 색상 설정"""
        if not self._check_initialization():
            return
        
        for i in range(self.led_count):
            self.set_pixel_color(i, r, g, b)
    
    def clear_all(self) -> None:
        """모든 LED 끄기"""
        if not self._check_initialization():
            return
        
        self.set_all_pixels(0, 0, 0)
        self.strip.show()
    
    def show(self) -> None:
        """LED 변경사항 적용"""
        if not self._check_initialization():
            return
        
        self.strip.show()
    
    def set_robot_state(self, state: RobotState) -> None:
        """로봇 상태에 따른 LED 표시"""
        self.current_state = state
        
        if not self._check_initialization():
            print(f"로봇 상태 변경: {state.value}")
            return
        
        # 애니메이션 중단
        self.stop_animation()
        
        # 상태별 색상 설정
        if state in self.state_colors:
            r, g, b = self.state_colors[state]
            self.set_all_pixels(r, g, b)
            self.show()
            print(f"LED 상태 변경: {state.value} - RGB({r}, {g}, {b})")
    
    def start_breathing_animation(self, r: int, g: int, b: int, speed: float = 0.05) -> None:
        """호흡 효과 애니메이션 시작"""
        if not self._check_initialization():
            return
        
        self.stop_animation()
        self.animation_running = True
        
        def breathing_loop():
            direction = 1
            brightness = 0
            
            while self.animation_running:
                # 밝기 조절
                brightness += direction * 5
                if brightness >= 255:
                    brightness = 255
                    direction = -1
                elif brightness <= 0:
                    brightness = 0
                    direction = 1
                
                # 색상 적용
                scaled_r = int((r * brightness) / 255)
                scaled_g = int((g * brightness) / 255)
                scaled_b = int((b * brightness) / 255)
                
                self.set_all_pixels(scaled_r, scaled_g, scaled_b)
                self.show()
                
                time.sleep(speed)
        
        self.animation_thread = threading.Thread(target=breathing_loop, daemon=True)
        self.animation_thread.start()
    
    def start_rainbow_animation(self, speed: float = 0.1) -> None:
        """무지개 효과 애니메이션 시작"""
        if not self._check_initialization():
            return
        
        self.stop_animation()
        self.animation_running = True
        
        def rainbow_loop():
            hue = 0
            
            while self.animation_running:
                for i in range(self.led_count):
                    # HSV to RGB 변환 (간단한 버전)
                    h = (hue + (i * 360 // self.led_count)) % 360
                    r, g, b = self._hsv_to_rgb(h, 100, 100)
                    self.set_pixel_color(i, r, g, b)
                
                self.show()
                hue = (hue + 5) % 360
                time.sleep(speed)
        
        self.animation_thread = threading.Thread(target=rainbow_loop, daemon=True)
        self.animation_thread.start()
    
    def start_blink_animation(self, r: int, g: int, b: int, interval: float = 0.5) -> None:
        """깜빡임 애니메이션 시작"""
        if not self._check_initialization():
            return
        
        self.stop_animation()
        self.animation_running = True
        
        def blink_loop():
            state = False
            
            while self.animation_running:
                if state:
                    self.set_all_pixels(r, g, b)
                else:
                    self.clear_all()
                
                self.show()
                state = not state
                time.sleep(interval)
        
        self.animation_thread = threading.Thread(target=blink_loop, daemon=True)
        self.animation_thread.start()
    
    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[int, int, int]:
        """HSV를 RGB로 변환 (간단한 구현)"""
        h = h / 60.0
        s = s / 100.0
        v = v / 100.0
        
        c = v * s
        x = c * (1 - abs((h % 2) - 1))
        m = v - c
        
        if 0 <= h < 1:
            r, g, b = c, x, 0
        elif 1 <= h < 2:
            r, g, b = x, c, 0
        elif 2 <= h < 3:
            r, g, b = 0, c, x
        elif 3 <= h < 4:
            r, g, b = 0, x, c
        elif 4 <= h < 5:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return (
            int((r + m) * 255),
            int((g + m) * 255),
            int((b + m) * 255)
        )
    
    def stop_animation(self) -> None:
        """애니메이션 중단"""
        if self.animation_running:
            self.animation_running = False
            if self.animation_thread:
                self.animation_thread.join(timeout=1)
    
    def show_obstacle_warning(self, distance: float) -> None:
        """거리에 따른 장애물 경고 표시"""
        if not self._check_initialization():
            return
        
        if distance < 10:
            # 매우 가까움 - 빨간색 깜빡임
            self.start_blink_animation(255, 0, 0, 0.2)
        elif distance < 20:
            # 가까움 - 주황색 호흡
            self.start_breathing_animation(255, 100, 0, 0.03)
        elif distance < 40:
            # 조금 가까움 - 노란색
            self.set_all_pixels(255, 255, 0)
            self.show()
        else:
            # 안전 - 초록색
            self.set_all_pixels(0, 255, 0)
            self.show()
    
    def show_startup_sequence(self) -> None:
        """시작 시퀀스 LED 효과"""
        if not self._check_initialization():
            return
        
        print("LED 시작 시퀀스 실행")
        
        # 1. 모든 LED 켜기 (흰색)
        self.set_all_pixels(255, 255, 255)
        self.show()
        time.sleep(0.5)
        
        # 2. 색상별로 순차 켜기
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        for r, g, b in colors:
            self.set_all_pixels(r, g, b)
            self.show()
            time.sleep(0.3)
        
        # 3. 모든 LED 끄기
        self.clear_all()
        time.sleep(0.2)
        
        # 4. 대기 상태로 설정
        self.set_robot_state(RobotState.IDLE)
    
    def cleanup(self) -> None:
        """리소스 정리"""
        if self.is_initialized:
            self.stop_animation()
            self.clear_all()
            self.is_initialized = False
            print("LED 컨트롤러 정리 완료")


def main():
    """LED 컨트롤러 테스트 함수"""
    led = LEDController()
    
    if not led.initialize_led():
        print("LED 초기화 실패 또는 라이브러리 없음")
        return
    
    try:
        print("LED 컨트롤러 테스트 시작... (Ctrl+C로 종료)")
        
        # 시작 시퀀스
        led.show_startup_sequence()
        time.sleep(1)
        
        # 상태별 테스트
        states = [
            RobotState.IDLE,
            RobotState.MOVING,
            RobotState.LINE_FOLLOWING,
            RobotState.OBSTACLE,
            RobotState.LOST,
            RobotState.ERROR
        ]
        
        for state in states:
            print(f"상태 테스트: {state.value}")
            led.set_robot_state(state)
            time.sleep(2)
        
        # 애니메이션 테스트
        print("호흡 애니메이션 테스트")
        led.start_breathing_animation(0, 255, 0)
        time.sleep(3)
        
        print("무지개 애니메이션 테스트")
        led.start_rainbow_animation()
        time.sleep(3)
        
        print("깜빡임 애니메이션 테스트")
        led.start_blink_animation(255, 0, 255)
        time.sleep(3)
        
        print("테스트 완료")
        
    except KeyboardInterrupt:
        print("\n사용자에 의해 테스트 중단")
    finally:
        led.cleanup()


if __name__ == '__main__':
    main()
