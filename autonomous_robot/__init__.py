#!/usr/bin/env python3
# 파일명: __init__.py
# 설명: 자율주행 로봇 패키지 초기화 파일
# 작성일: 2024
"""
라즈베리파이 기반 자율주행 로봇 패키지

이 패키지는 다음 기능들을 제공합니다:
- 4개 기어모터를 이용한 이동 제어
- 3개 라인 센서를 이용한 라인 추적
- 초음파 센서를 이용한 장애물 회피
- LED를 이용한 상태 표시
- 통합 자율주행 제어
"""

__version__ = "1.0.0"
__author__ = "라즈베리파이 자율주행 프로젝트"
__description__ = "모듈형 자율주행 로봇 제어 시스템"

# 패키지 메타데이터
PACKAGE_INFO = {
    "name": "autonomous_robot",
    "version": __version__,
    "author": __author__,
    "description": __description__,
    "python_requires": ">=3.7",
    "required_libraries": ["RPi.GPIO", "rpi_ws281x", "adafruit-circuitpython-pca9685"],
    "hardware_requirements": [
        "라즈베리파이 4B 이상",
        "L298N 모터 드라이버",
        "HC-SR04 초음파 센서",
        "적외선 라인 센서 3개",
        "WS2812 LED 스트립",
        "기어모터 4개",
        "12V 배터리",
    ],
}

# 모듈 임포트 (선택적)
try:
    from .controllers.autonomous_controller import AutonomousController
    from .actuators.motor_controller import MotorController
    from .actuators.led_controller import LEDController
    from .sensors.line_sensor import LineSensor
    from .sensors.ultrasonic_sensor import UltrasonicSensor

    __all__ = [
        "AutonomousController",
        "MotorController",
        "LEDController",
        "LineSensor",
        "UltrasonicSensor",
    ]

except ImportError as e:
    # 라즈베리파이가 아닌 환경에서는 모듈을 임포트하지 않음
    print(f"모듈 임포트 실패 (라즈베리파이 환경이 아닐 수 있음): {e}")
    __all__ = []


def get_package_info():
    """패키지 정보 반환"""
    return PACKAGE_INFO


def print_package_info():
    """패키지 정보 출력"""
    print(f"=== {PACKAGE_INFO['name']} v{PACKAGE_INFO['version']} ===")
    print(f"설명: {PACKAGE_INFO['description']}")
    print(f"작성자: {PACKAGE_INFO['author']}")
    print(f"Python 요구사항: {PACKAGE_INFO['python_requires']}")
    print("\n필수 라이브러리:")
    for lib in PACKAGE_INFO["required_libraries"]:
        print(f"  - {lib}")
    print("\n하드웨어 요구사항:")
    for hw in PACKAGE_INFO["hardware_requirements"]:
        print(f"  - {hw}")
