#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
단순한 장애물 회피 모듈 (고등학생용)
Simple Obstacle Avoidance Module for High School Students

이 모듈은 앞의 장애물을 피하는 기능을 쉽게 만들 수 있게 해줍니다.
"""

import time
from simple_sensors import read_distance, is_obstacle_close, setup_sensors, cleanup_sensors
from simple_motors import go_forward, turn_left, turn_right, stop, setup_motors, cleanup_motors, SPEED_NORMAL

# 회피 설정 (고등학생이 쉽게 바꿀 수 있음)
SAFE_DISTANCE = 30      # 안전한 거리 (cm)
DANGER_DISTANCE = 15    # 위험한 거리 (cm)
AVOID_TIME = 0.8        # 회피 동작 시간 (초)


def check_obstacle():
    """
    장애물이 있는지 확인합니다
    
    반환값:
    - "safe": 안전함 (30cm 이상)
    - "warning": 주의 (15-30cm)
    - "danger": 위험함 (15cm 이하)
    """
    distance = read_distance()
    
    if distance >= SAFE_DISTANCE:
        return "safe"
    elif distance >= DANGER_DISTANCE:
        return "warning"
    else:
        return "danger"


def avoid_obstacle_simple():
    """
    간단한 장애물 회피 (방법 1)
    왼쪽으로 돌아서 피합니다
    """
    print("🚨 장애물 발견! 왼쪽으로 피합니다")
    
    # 1단계: 왼쪽으로 돌기
    print("  1단계: 왼쪽으로 돌기")
    turn_left()
    time.sleep(AVOID_TIME)
    
    # 2단계: 앞으로 가기
    print("  2단계: 앞으로 가기")
    go_forward()
    time.sleep(AVOID_TIME)
    
    # 3단계: 오른쪽으로 돌아서 원래 방향으로
    print("  3단계: 오른쪽으로 돌기")
    turn_right()
    time.sleep(AVOID_TIME)
    
    print("✓ 장애물 회피 완료!")


def avoid_obstacle_smart():
    """
    똑똑한 장애물 회피 (방법 2)
    거리에 따라 다르게 반응합니다
    """
    obstacle_status = check_obstacle()
    
    if obstacle_status == "safe":
        # 안전하면 직진
        go_forward()
        return "safe"
        
    elif obstacle_status == "warning":
        # 주의하면 천천히 직진
        print("⚠️ 장애물 주의! 천천히 직진")
        go_forward(speed=SPEED_NORMAL // 2)  # 속도 절반으로
        return "warning"
        
    else:  # obstacle_status == "danger"
        # 위험하면 즉시 회피
        print("🚨 장애물 위험! 즉시 회피")
        avoid_obstacle_simple()
        return "danger"


def start_obstacle_avoidance(duration=10):
    """
    장애물 회피를 시작합니다
    
    매개변수:
    - duration: 몇 초 동안 실행할지 (0이면 무한히)
    """
    print(f"\n🛡️ 장애물 회피 시작!")
    print("앞으로 가다가 장애물이 있으면 피합니다")
    print("Ctrl+C를 누르면 멈춥니다")
    
    # 센서와 모터 준비
    if not setup_sensors():
        print("❌ 센서 준비 실패")
        return
        
    if not setup_motors():
        print("❌ 모터 준비 실패")
        return
    
    start_time = time.time()
    
    try:
        while True:
            # 시간 체크 (duration이 0이 아닌 경우)
            if duration > 0 and (time.time() - start_time) > duration:
                print(f"\n⏰ {duration}초 완료!")
                break
            
            # 똑똑한 장애물 회피 실행
            avoid_obstacle_smart()
            
            # 잠시 대기
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("\n\n⌨️ Ctrl+C로 중단됨")
    
    finally:
        # 정리
        stop()
        cleanup_sensors()
        cleanup_motors()
        print("✓ 장애물 회피 종료")


def test_obstacle_detection():
    """장애물 감지 기능을 테스트합니다"""
    print("\n🧪 장애물 감지 테스트")
    
    if not setup_sensors():
        print("❌ 센서 준비 실패")
        return
    
    print("\n5초 동안 장애물 감지 테스트...")
    
    for i in range(25):  # 5초 = 25번 × 0.2초
        distance = read_distance()
        status = check_obstacle()
        
        if status == "safe":
            icon = "✅"
        elif status == "warning":
            icon = "⚠️"
        else:
            icon = "🚨"
        
        print(f"{icon} 거리: {distance:3.0f}cm - {status}")
        time.sleep(0.2)
    
    cleanup_sensors()
    print("테스트 완료!")


def test_avoidance_movement():
    """장애물 회피 동작을 테스트합니다 (실제로 움직이지 않음)"""
    print("\n🧪 장애물 회피 동작 테스트")
    
    if not setup_motors():
        print("❌ 모터 준비 실패")
        return
    
    print("\n장애물 회피 동작 시뮬레이션...")
    print("(실제로는 움직이지 않고 출력만 합니다)")
    
    # 회피 동작 시뮬레이션
    print("\n🚨 가상 장애물 발견!")
    print("  1단계: 왼쪽으로 돌기")
    print("  2단계: 앞으로 가기")
    print("  3단계: 오른쪽으로 돌기")
    print("✓ 회피 완료!")
    
    cleanup_motors()
    print("테스트 완료!")


def explain_obstacle_avoidance():
    """장애물 회피 원리를 설명합니다"""
    print("\n📚 장애물 회피 원리:")
    print("="*50)
    print("1. 초음파 센서로 앞의 거리를 측정합니다")
    print(f"   - {SAFE_DISTANCE}cm 이상: 안전 (직진)")
    print(f"   - {DANGER_DISTANCE}-{SAFE_DISTANCE}cm: 주의 (천천히)")
    print(f"   - {DANGER_DISTANCE}cm 이하: 위험 (회피)")
    print()
    print("2. 회피 방법:")
    print("   ① 왼쪽으로 돌기")
    print("   ② 앞으로 가서 장애물 지나가기")
    print("   ③ 오른쪽으로 돌아서 원래 방향으로")
    print()
    print("3. 설정 변경:")
    print("   파일 상단의 SAFE_DISTANCE, DANGER_DISTANCE,")
    print("   AVOID_TIME 값을 바꿔서 조정할 수 있습니다")


def show_current_settings():
    """현재 설정을 보여줍니다"""
    print("\n⚙️ 현재 장애물 회피 설정:")
    print(f"  안전 거리: {SAFE_DISTANCE}cm")
    print(f"  위험 거리: {DANGER_DISTANCE}cm")
    print(f"  회피 시간: {AVOID_TIME}초")


if __name__ == "__main__":
    explain_obstacle_avoidance()
    show_current_settings()
    
    print("\n어떤 테스트를 하시겠습니까?")
    print("1. 장애물 감지 테스트 (안전)")
    print("2. 회피 동작 테스트 (안전)")
    print("3. 실제 장애물 회피 (10초)")
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == "1":
        test_obstacle_detection()
    elif choice == "2":
        test_avoidance_movement()
    elif choice == "3":
        start_obstacle_avoidance(duration=10)
    else:
        print("잘못된 선택입니다")
