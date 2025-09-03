#!/usr/bin/env python3
# 파일명: test_ultrasonic_noise_filtering.py
# 설명: 초음파 센서 노이즈 필터링 시스템 종합 테스트 프로그램
# 작성일: 2024

import time
import sys
from typing import List, Dict

# 노이즈 필터링 시스템 임포트
try:
    from autonomous_robot.sensors.ultrasonic_noise_filter import (
        get_ultra_reliable_distance_measurement,
        reset_all_filter_systems,
        print_detailed_filter_status,
        run_filter_performance_test,
        simulate_noisy_sensor_data_and_test_filtering,
        get_sensor_health_status,
    )
    from autonomous_robot.sensors.simple_ultrasonic_functions import (
        setup_ultrasonic_sensor_pins,
        get_complete_obstacle_status_and_recommendation,
        cleanup_ultrasonic_resources,
    )
except ImportError as e:
    print(f"❌ 모듈 임포트 실패: {e}")
    print("autonomous_robot 패키지가 제대로 설치되어 있는지 확인하세요.")
    sys.exit(1)

# =============================================================================
# 테스트 시나리오 함수들
# =============================================================================


def test_scenario_1_normal_operation():
    """
    테스트 시나리오 1: 정상 동작 상황
    노이즈가 적은 환경에서의 필터링 성능 확인
    """
    print("\n🧪 시나리오 1: 정상 동작 테스트")
    print("=" * 50)

    reset_all_filter_systems()

    print("15초 동안 정상 환경에서 거리 측정...")

    for i in range(15):
        # 노이즈 필터링된 측정
        result = get_ultra_reliable_distance_measurement()

        if result["distance_cm"] is not None:
            print(
                f"  측정 {i+1:2d}: {result['distance_cm']:6.1f}cm | "
                f"신뢰도: {result['confidence_level']:10s} | "
                f"센서점수: {result['reliability_score']:5.1f}%"
            )
        else:
            print(f"  측정 {i+1:2d}: 측정 실패")

        time.sleep(1)

    print_detailed_filter_status()


def test_scenario_2_noisy_environment():
    """
    테스트 시나리오 2: 노이즈가 많은 환경
    센서 오동작이 빈번한 상황에서의 필터링 효과 확인
    """
    print("\n🧪 시나리오 2: 노이즈 환경 테스트")
    print("=" * 50)

    print("시뮬레이션된 노이즈 데이터로 필터링 성능 확인...")
    simulate_noisy_sensor_data_and_test_filtering()


def test_scenario_3_performance_benchmark():
    """
    테스트 시나리오 3: 성능 벤치마크
    30초 동안 연속 측정하여 시스템 성능 평가
    """
    print("\n🧪 시나리오 3: 성능 벤치마크 테스트")
    print("=" * 50)

    performance_result = run_filter_performance_test(30)

    print(f"\n📊 벤치마크 결과 요약:")
    print(f"  총 시도: {performance_result['total_attempts']}회")
    print(f"  성공률: {performance_result['success_rate_percentage']:.1f}%")
    print(f"  평균 거리: {performance_result['average_distance']:.1f}cm")
    print(f"  측정 안정성: ±{performance_result['measurement_stability']:.1f}cm")
    print(f"  센서 점수: {performance_result['final_sensor_score']:.1f}%")
    print(f"  노이즈 감지율: {performance_result['noise_detection_rate']:.1f}%")


def test_scenario_4_real_robot_integration():
    """
    테스트 시나리오 4: 실제 로봇 통합 테스트
    실제 장애물 회피 시스템과 통합하여 테스트
    """
    print("\n🧪 시나리오 4: 실제 로봇 통합 테스트")
    print("=" * 50)

    # 초음파 센서 초기화 시도
    if setup_ultrasonic_sensor_pins():
        print("✅ 초음파 센서 초기화 성공")
    else:
        print("⚠️ 초음파 센서 초기화 실패 - 시뮬레이션 모드로 진행")

    print("실제 장애물 회피 시스템과 연동 테스트...")

    for i in range(10):
        # 통합 시스템에서 장애물 상태 확인
        obstacle_status = get_complete_obstacle_status_and_recommendation()

        print(f"\n--- 통합 테스트 {i+1} ---")
        print(
            f"거리: {obstacle_status['distance_cm']:.1f}cm"
            if obstacle_status["distance_cm"]
            else "거리: 측정 실패"
        )
        print(f"위험도: {obstacle_status['danger_level']}")
        print(f"추천 동작: {obstacle_status['recommended_action']}")
        print(f"측정 신뢰도: {obstacle_status['measurement_confidence']}")
        print(f"센서 상태: {'정상' if obstacle_status['sensor_health'] else '불량'}")
        print(
            f"노이즈 필터링: {'적용됨' if obstacle_status['noise_filtered'] else '미적용'}"
        )

        time.sleep(2)

    # 자원 정리
    cleanup_ultrasonic_resources()


# =============================================================================
# 메인 테스트 함수들
# =============================================================================


def show_test_menu():
    """테스트 메뉴 출력"""
    print("\n📋 초음파 센서 노이즈 필터링 테스트 메뉴:")
    print("  1 - 정상 동작 테스트")
    print("  2 - 노이즈 환경 테스트")
    print("  3 - 성능 벤치마크 테스트")
    print("  4 - 실제 로봇 통합 테스트")
    print("  5 - 전체 테스트 실행")
    print("  s - 시스템 상태 확인")
    print("  r - 필터 시스템 초기화")
    print("  q - 종료")


def run_all_tests():
    """모든 테스트를 순서대로 실행"""
    print("\n🚀 전체 테스트 시퀀스 시작")
    print("=" * 60)

    try:
        test_scenario_1_normal_operation()
        time.sleep(2)

        test_scenario_2_noisy_environment()
        time.sleep(2)

        test_scenario_3_performance_benchmark()
        time.sleep(2)

        test_scenario_4_real_robot_integration()

        print("\n🎉 모든 테스트 완료!")

    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 테스트 중단")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")


def check_system_status():
    """현재 시스템 상태 확인"""
    print("\n📊 현재 시스템 상태:")

    # 센서 상태 확인
    sensor_status = get_sensor_health_status()

    print(f"센서 신뢰도: {sensor_status['reliability_score']:.1f}%")
    print(f"센서 상태: {sensor_status['health_status']}")
    print(f"정상 작동: {'예' if sensor_status['is_working_properly'] else '아니오'}")
    print(f"연속 불량: {sensor_status['consecutive_bad_readings']}회")
    print(f"총 측정: {sensor_status['total_measurements']}회")
    print(f"노이즈율: {sensor_status['noise_detection_rate']:.1f}%")

    # 상세 상태 출력
    print_detailed_filter_status()


def main():
    """메인 함수"""
    print("🤖 초음파 센서 노이즈 필터링 시스템 테스트 프로그램")
    print("=" * 60)

    # 라즈베리파이 환경 확인
    try:
        import RPi.GPIO as GPIO

        print("✅ 라즈베리파이 환경 감지")
        is_raspberry_pi = True
    except ImportError:
        print("⚠️ 라즈베리파이가 아닌 환경 - 시뮬레이션 모드로 실행")
        is_raspberry_pi = False

    # 필터링 시스템 초기화
    reset_all_filter_systems()
    print("✅ 필터링 시스템 초기화 완료")

    # 메인 루프
    try:
        while True:
            show_test_menu()
            choice = input("\n선택: ").strip().lower()

            if choice == "1":
                test_scenario_1_normal_operation()
            elif choice == "2":
                test_scenario_2_noisy_environment()
            elif choice == "3":
                test_scenario_3_performance_benchmark()
            elif choice == "4":
                test_scenario_4_real_robot_integration()
            elif choice == "5":
                run_all_tests()
            elif choice == "s":
                check_system_status()
            elif choice == "r":
                reset_all_filter_systems()
                print("✅ 필터 시스템 초기화 완료")
            elif choice == "q":
                break
            else:
                print("❓ 알 수 없는 명령입니다.")

    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C로 프로그램 종료")
    except Exception as e:
        print(f"\n❌ 프로그램 오류: {e}")
    finally:
        # 자원 정리
        try:
            cleanup_ultrasonic_resources()
        except:
            pass
        print("👋 프로그램을 종료합니다.")


if __name__ == "__main__":
    main()
