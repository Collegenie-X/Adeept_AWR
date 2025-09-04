#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
단순한 라인 추적 모듈 (고등학생용)
Simple Line Following Module for High School Students

이 모듈은 검은 선을 따라가는 기능을 쉽게 만들 수 있게 해줍니다.
"""

import time
from simple_sensors import read_line, setup_sensors, cleanup_sensors
from simple_motors import go_forward, turn_left, turn_right, turn_left_gentle, turn_right_gentle, stop, setup_motors, cleanup_motors, SPEED_SLOW


def follow_line_simple():
    """
    간단한 라인 추적 (기본)
    검은 선을 보고 자동차가 따라갑니다
    """
    line_position = read_line()
    
    if line_position == "center":
        # 라인이 가운데 있으면 직진
        go_forward()
        
    elif line_position == "left":
        # 라인이 왼쪽에 있으면 오른쪽으로 가야 함
        turn_right()
        
    elif line_position == "right":
        # 라인이 오른쪽에 있으면 왼쪽으로 가야 함
        turn_left()
        
    else:  # line_position == "none"
        # 라인이 없으면 찾기 위해 천천히 돌기
        turn_left(SPEED_SLOW)


def follow_line_smooth():
    """
    부드러운 라인 추적 (개선된 버전)
    더 부드럽게 움직입니다
    """
    line_position = read_line()
    
    if line_position == "center":
        # 라인이 가운데 있으면 직진
        go_forward()
        
    elif line_position == "left":
        # 라인이 왼쪽에 있으면 부드럽게 오른쪽으로
        turn_right_gentle()
        
    elif line_position == "right":
        # 라인이 오른쪽에 있으면 부드럽게 왼쪽으로
        turn_left_gentle()
        
    else:  # line_position == "none"
        # 라인이 없으면 찾기 위해 천천히 돌기
        turn_left(SPEED_SLOW)


def start_line_following(smooth_mode=True, duration=10):
    """
    라인 추적을 시작합니다
    
    매개변수:
    - smooth_mode: True면 부드러운 모드, False면 기본 모드
    - duration: 몇 초 동안 실행할지 (0이면 무한히)
    """
    print(f"\n🚗 라인 추적 시작! ({'부드러운' if smooth_mode else '기본'} 모드)")
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
            
            # 라인 추적 실행
            if smooth_mode:
                follow_line_smooth()
            else:
                follow_line_simple()
            
            # 잠시 대기 (너무 빠르게 반응하지 않도록)
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n⌨️ Ctrl+C로 중단됨")
    
    finally:
        # 정리
        stop()
        cleanup_sensors()
        cleanup_motors()
        print("✓ 라인 추적 종료")


def test_line_following():
    """라인 추적 기능을 테스트합니다"""
    print("\n🧪 라인 추적 테스트")
    
    # 센서와 모터 준비
    if not setup_sensors():
        print("❌ 센서 준비 실패")
        return
        
    if not setup_motors():
        print("❌ 모터 준비 실패")
        return
    
    print("\n5초 동안 라인 상태에 따른 동작 테스트...")
    
    for i in range(25):  # 5초 = 25번 × 0.2초
        line_position = read_line()
        print(f"라인 위치: {line_position:6} → ", end="")
        
        # 동작 결정 (실제로는 움직이지 않고 출력만)
        if line_position == "center":
            print("직진")
        elif line_position == "left":
            print("오른쪽으로 회전")
        elif line_position == "right":
            print("왼쪽으로 회전")
        else:
            print("라인 찾기")
        
        time.sleep(0.2)
    
    cleanup_sensors()
    cleanup_motors()
    print("테스트 완료!")


def explain_line_following():
    """라인 추적 원리를 설명합니다"""
    print("\n📚 라인 추적 원리:")
    print("="*50)
    print("1. 센서가 검은 선의 위치를 확인합니다")
    print("   - 'center': 선이 가운데 → 직진")
    print("   - 'left':   선이 왼쪽   → 오른쪽으로 회전")
    print("   - 'right':  선이 오른쪽 → 왼쪽으로 회전")
    print("   - 'none':   선이 없음   → 찾기 위해 회전")
    print()
    print("2. 기본 모드 vs 부드러운 모드:")
    print("   - 기본: 빠르게 반응 (급회전)")
    print("   - 부드러운: 천천히 반응 (완만한 회전)")
    print()
    print("3. 사용법:")
    print("   start_line_following(smooth_mode=True)  # 부드러운 모드")
    print("   start_line_following(smooth_mode=False) # 기본 모드")


if __name__ == "__main__":
    explain_line_following()
    
    print("\n어떤 테스트를 하시겠습니까?")
    print("1. 라인 추적 원리 테스트 (안전)")
    print("2. 실제 라인 추적 (기본 모드, 10초)")
    print("3. 실제 라인 추적 (부드러운 모드, 10초)")
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == "1":
        test_line_following()
    elif choice == "2":
        start_line_following(smooth_mode=False, duration=10)
    elif choice == "3":
        start_line_following(smooth_mode=True, duration=10)
    else:
        print("잘못된 선택입니다")
