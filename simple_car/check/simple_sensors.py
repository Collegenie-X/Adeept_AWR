#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
단순한 센서 읽기 모듈 (고등학생용)
Simple Sensor Reading Module for High School Students

이 모듈은 라인 센서와 초음파 센서를 쉽게 읽을 수 있게 해줍니다.
"""

import time
import random

# 하드웨어 모듈 가져오기
try:
    from hardware.test_line_sensors import LineSensorController
    from hardware.test_ultrasonic_sensor import UltrasonicSensor
    HARDWARE_AVAILABLE = True
    print("✓ 실제 센서 사용")
except ImportError:
    HARDWARE_AVAILABLE = False
    print("⚠️ 시뮬레이션 모드")

# 전역 변수 - 센서 객체들
line_sensor = None
ultrasonic_sensor = None


def setup_sensors():
    """센서들을 준비합니다"""
    global line_sensor, ultrasonic_sensor
    
    if HARDWARE_AVAILABLE:
        try:
            line_sensor = LineSensorController()
            ultrasonic_sensor = UltrasonicSensor()
            print("✓ 센서 준비 완료!")
            return True
        except Exception as e:
            print(f"❌ 센서 준비 실패: {e}")
            return False
    else:
        print("✓ 시뮬레이션 센서 준비 완료!")
        return True


def read_line():
    """
    라인 센서를 읽습니다
    
    반환값:
    - "left": 라인이 왼쪽에 있음 (오른쪽으로 가야 함)
    - "center": 라인이 가운데 있음 (직진)  
    - "right": 라인이 오른쪽에 있음 (왼쪽으로 가야 함)
    - "none": 라인이 없음 (찾아야 함)
    """
    if line_sensor:
        # 실제 센서 사용
        line_info = line_sensor.get_line_position()
        position = line_info["position"]
        
        if position is None:
            return "none"
        elif position < -0.3:
            return "left"
        elif position > 0.3:
            return "right"
        else:
            return "center"
    else:
        # 시뮬레이션 - 랜덤하게 반환
        options = ["left", "center", "right", "none"]
        weights = [20, 50, 20, 10]  # center가 가장 높은 확률
        return random.choices(options, weights=weights)[0]


def read_distance():
    """
    초음파 센서로 앞의 거리를 측정합니다
    
    반환값:
    - 거리 (cm 단위)
    """
    if ultrasonic_sensor:
        # 실제 센서 사용
        distance = ultrasonic_sensor.measure_distance()
        return distance if distance is not None else 999
    else:
        # 시뮬레이션 - 대부분 안전한 거리
        if random.random() < 0.1:  # 10% 확률로 장애물
            return random.randint(10, 30)
        else:
            return random.randint(50, 200)


def is_obstacle_close():
    """
    장애물이 가까이 있는지 확인합니다
    
    반환값:
    - True: 장애물이 가까이 있음 (20cm 이내)
    - False: 안전함
    """
    distance = read_distance()
    return distance < 20


def cleanup_sensors():
    """센서들을 정리합니다"""
    global line_sensor, ultrasonic_sensor
    
    try:
        if line_sensor:
            line_sensor.cleanup()
        if ultrasonic_sensor:
            ultrasonic_sensor.cleanup()
        print("✓ 센서 정리 완료")
    except Exception as e:
        print(f"센서 정리 중 오류: {e}")


# 테스트 함수
def test_sensors():
    """센서들을 테스트합니다"""
    print("\n🧪 센서 테스트")
    
    if not setup_sensors():
        print("❌ 센서 준비 실패")
        return
    
    print("\n5초 동안 센서 읽기...")
    for i in range(10):
        line_result = read_line()
        distance = read_distance()
        obstacle = is_obstacle_close()
        
        print(f"{i+1}. 라인: {line_result:6} | 거리: {distance:3.0f}cm | 장애물: {'예' if obstacle else '아니오'}")
        time.sleep(0.5)
    
    cleanup_sensors()
    print("테스트 완료!")


if __name__ == "__main__":
    test_sensors()
