#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
간단한 자율 주행차 메인 프로그램 (고등학생용)
Simple Autonomous Car Main Program for High School Students

이 프로그램은 라인을 따라가면서 장애물도 피하는 똑똑한 자동차입니다.
"""

import time
import sys

# 우리가 만든 모듈들 가져오기
from simple_sensors import read_line, read_distance, setup_sensors, cleanup_sensors
from simple_motors import go_forward, turn_left, turn_right, stop, setup_motors, cleanup_motors, SPEED_NORMAL
from simple_line_follow import follow_line_smooth
from simple_obstacle_avoid import check_obstacle, avoid_obstacle_simple


def smart_car_drive():
    """
    똑똑한 자동차 주행
    라인을 따라가면서 장애물도 피합니다
    """
    # 1단계: 장애물 확인
    obstacle_status = check_obstacle()
    
    if obstacle_status == "danger":
        # 장애물이 위험하게 가까우면 즉시 피하기
        print("🚨 장애물 회피!")
        avoid_obstacle_simple()
        return "avoiding"
    
    elif obstacle_status == "warning":
        # 장애물이 좀 있으면 천천히 가기
        print("⚠️ 장애물 주의 - 천천히 직진")
        go_forward(speed=SPEED_NORMAL // 2)
        return "slow"
    
    else:  # obstacle_status == "safe"
        # 장애물이 없으면 라인 추적
        follow_line_smooth()
        return "following"


def start_smart_car(duration=30):
    """
    똑똑한 자동차를 시작합니다
    
    매개변수:
    - duration: 몇 초 동안 실행할지 (0이면 무한히)
    """
    print("\n🚗 똑똑한 자율 주행차 시작!")
    print("라인을 따라가면서 장애물도 피합니다")
    print("Ctrl+C를 누르면 멈춥니다")
    
    # 센서와 모터 준비
    print("센서와 모터 준비 중...")
    if not setup_sensors():
        print("❌ 센서 준비 실패")
        return
        
    if not setup_motors():
        print("❌ 모터 준비 실패")
        return
    
    print("✓ 준비 완료!")
    start_time = time.time()
    
    # 통계
    stats = {
        "following": 0,    # 라인 추적 횟수
        "slow": 0,         # 천천히 주행 횟수
        "avoiding": 0      # 장애물 회피 횟수
    }
    
    try:
        while True:
            # 시간 체크 (duration이 0이 아닌 경우)
            if duration > 0 and (time.time() - start_time) > duration:
                print(f"\n⏰ {duration}초 완료!")
                break
            
            # 똑똑한 주행 실행
            action = smart_car_drive()
            stats[action] += 1
            
            # 잠시 대기
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\n⌨️ Ctrl+C로 중단됨")
    
    finally:
        # 정리
        stop()
        cleanup_sensors()
        cleanup_motors()
        
        # 통계 출력
        total_actions = sum(stats.values())
        if total_actions > 0:
            print("\n📊 주행 통계:")
            print(f"  라인 추적: {stats['following']}회 ({stats['following']/total_actions*100:.1f}%)")
            print(f"  천천히 주행: {stats['slow']}회 ({stats['slow']/total_actions*100:.1f}%)")
            print(f"  장애물 회피: {stats['avoiding']}회 ({stats['avoiding']/total_actions*100:.1f}%)")
        
        print("✓ 똑똑한 자동차 종료")


def test_all_functions():
    """모든 기능을 간단히 테스트합니다"""
    print("\n🧪 전체 기능 테스트")
    
    # 센서와 모터 준비
    if not setup_sensors():
        print("❌ 센서 준비 실패")
        return
        
    if not setup_motors():
        print("❌ 모터 준비 실패")
        return
    
    print("\n5초 동안 전체 기능 테스트...")
    
    for i in range(25):  # 5초 = 25번 × 0.2초
        # 센서 읽기
        line_pos = read_line()
        distance = read_distance()
        obstacle = check_obstacle()
        
        # 상태 출력
        print(f"{i+1:2d}. 라인:{line_pos:6} | 거리:{distance:3.0f}cm | 장애물:{obstacle:7} → ", end="")
        
        # 어떤 동작을 할지 결정 (실제로는 움직이지 않음)
        if obstacle == "danger":
            print("장애물 회피")
        elif obstacle == "warning":
            print("천천히 직진")
        else:
            if line_pos == "center":
                print("직진")
            elif line_pos == "left":
                print("오른쪽 회전")
            elif line_pos == "right":
                print("왼쪽 회전")
            else:
                print("라인 찾기")
        
        time.sleep(0.2)
    
    cleanup_sensors()
    cleanup_motors()
    print("테스트 완료!")


def manual_control():
    """수동으로 자동차를 조종합니다"""
    print("\n🎮 수동 조종 모드")
    print("키보드로 자동차를 조종할 수 있습니다")
    
    if not setup_motors():
        print("❌ 모터 준비 실패")
        return
    
    print("\n조종법:")
    print("  w: 앞으로")
    print("  s: 뒤로")
    print("  a: 왼쪽")
    print("  d: 오른쪽")
    print("  x: 멈춤")
    print("  q: 종료")
    
    try:
        while True:
            command = input("\n명령 입력: ").lower().strip()
            
            if command == 'w':
                go_forward()
            elif command == 's':
                go_backward()
            elif command == 'a':
                turn_left()
            elif command == 'd':
                turn_right()
            elif command == 'x':
                stop()
            elif command == 'q':
                break
            else:
                print("잘못된 명령입니다")
    
    except KeyboardInterrupt:
        print("\n⌨️ Ctrl+C로 중단됨")
    
    finally:
        stop()
        cleanup_motors()
        print("✓ 수동 조종 종료")


def show_menu():
    """메뉴를 보여줍니다"""
    print("\n" + "="*50)
    print("🚗 간단한 자율 주행차 (고등학생용)")
    print("="*50)
    print("1. 똑똑한 자율 주행 (30초)")
    print("2. 전체 기능 테스트 (5초)")
    print("3. 수동 조종")
    print("4. 라인 추적만")
    print("5. 장애물 회피만")
    print("6. 도움말")
    print("0. 종료")
    print("="*50)


def show_help():
    """도움말을 보여줍니다"""
    print("\n📚 도움말:")
    print("="*50)
    print("이 프로그램은 다음 모듈들로 구성되어 있습니다:")
    print()
    print("📁 simple_sensors.py")
    print("   - 라인 센서와 초음파 센서를 읽습니다")
    print("   - read_line(): 라인 위치 확인")
    print("   - read_distance(): 앞의 거리 측정")
    print()
    print("📁 simple_motors.py")
    print("   - 자동차의 바퀴를 움직입니다")
    print("   - go_forward(): 직진")
    print("   - turn_left(), turn_right(): 회전")
    print()
    print("📁 simple_line_follow.py")
    print("   - 검은 선을 따라갑니다")
    print("   - follow_line_smooth(): 부드러운 라인 추적")
    print()
    print("📁 simple_obstacle_avoid.py")
    print("   - 장애물을 피합니다")
    print("   - avoid_obstacle_simple(): 간단한 회피")
    print()
    print("💡 속도나 거리 설정을 바꾸려면:")
    print("   각 모듈 파일의 상단 설정값을 수정하세요!")


def main():
    """메인 함수"""
    while True:
        show_menu()
        
        try:
            choice = input("선택하세요 (0-6): ").strip()
            
            if choice == "1":
                start_smart_car(duration=30)
                
            elif choice == "2":
                test_all_functions()
                
            elif choice == "3":
                manual_control()
                
            elif choice == "4":
                from simple_line_follow import start_line_following
                start_line_following(smooth_mode=True, duration=20)
                
            elif choice == "5":
                from simple_obstacle_avoid import start_obstacle_avoidance
                start_obstacle_avoidance(duration=20)
                
            elif choice == "6":
                show_help()
                
            elif choice == "0":
                print("👋 프로그램을 종료합니다")
                break
                
            else:
                print("❌ 잘못된 선택입니다")
                
        except KeyboardInterrupt:
            print("\n\n⌨️ Ctrl+C로 종료됨")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
