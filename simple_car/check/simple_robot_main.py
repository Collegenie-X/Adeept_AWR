#!/usr/bin/env python3
# 파일명: simple_robot_main.py
# 설명: 함수형으로 만든 간단한 자율주행 로봇 메인 프로그램 (고등학생 수준)
# 작성일: 2024

import time
import signal
import sys
from typing import Dict, Any

# 우리가 만든 함수들 가져오기
from autonomous_robot.utils.simple_rotary_functions import (
    get_smart_driving_command_for_rotary_and_normal_sections,
    print_current_status_for_debugging,
    reset_all_rotary_memory,
)
from autonomous_robot.actuators.simple_motor_functions import (
    setup_all_motor_pins_and_pwm_controllers,
    execute_driving_action_with_speed,
    stop_all_motors_immediately,
    cleanup_all_motor_resources_safely,
)
from autonomous_robot.sensors.simple_ultrasonic_functions import (
    setup_ultrasonic_sensor_pins,
    get_complete_obstacle_status_and_recommendation,
    cleanup_ultrasonic_resources,
)
from autonomous_robot.utils.obstacle_avoidance_strategies import (
    get_complete_obstacle_avoidance_command,
    reset_avoidance_state,
    print_avoidance_status_for_debugging,
)

# =============================================================================
# 전역 변수들 (로봇 상태 관리)
# =============================================================================

# 센서 핀 번호들 (라즈베리파이 물리 핀 번호)
LINE_SENSOR_LEFT_PIN = 35  # 왼쪽 라인 센서
LINE_SENSOR_CENTER_PIN = 36  # 가운데 라인 센서
LINE_SENSOR_RIGHT_PIN = 37  # 오른쪽 라인 센서

# 로봇 실행 상태
is_robot_running = False  # 자율주행 중인지 여부
should_stop_robot = False  # 정지 신호 받았는지 여부

# 성능 모니터링
total_control_loops = 0  # 총 제어 루프 실행 횟수
robot_start_time = 0.0  # 로봇 시작 시간

# 제어 설정
CONTROL_LOOP_INTERVAL = 0.1  # 제어 루프 주기 (100ms = 0.1초)


# =============================================================================
# 초기화 및 종료 함수들
# =============================================================================


def initialize_all_robot_hardware_systems() -> bool:
    """
    로봇의 모든 하드웨어 시스템을 초기화하는 함수
    모터, 센서 등을 모두 사용할 준비를 시킵니다.
    """
    print("🔧 로봇 하드웨어 초기화 시작...")

    # 각 시스템별로 초기화 시도
    initialization_results = {
        "모터 시스템": setup_all_motor_pins_and_pwm_controllers(),
        "초음파 센서": setup_ultrasonic_sensor_pins(),
        "라인 센서": True,  # 라인 센서는 별도 초기화 불필요 (GPIO 자동 설정)
    }

    # 초기화 결과 출력
    for system_name, success in initialization_results.items():
        status_text = "성공" if success else "실패"
        print(f"  {system_name}: {status_text}")

    # 모든 시스템이 성공했는지 확인
    all_systems_ready = all(initialization_results.values())

    if all_systems_ready:
        print("✅ 모든 하드웨어 시스템 초기화 완료!")

        # 로터리 시스템 메모리 초기화
        reset_all_rotary_memory()

        # 안전을 위해 모든 모터 정지 상태로 시작
        stop_all_motors_immediately()

    else:
        print("❌ 일부 하드웨어 시스템 초기화 실패")

    return all_systems_ready


def handle_emergency_stop_signal(signal_number, frame):
    """
    Ctrl+C 같은 비상 정지 신호를 처리하는 함수
    """
    global should_stop_robot
    print("\n🛑 비상 정지 신호 받음! 로봇을 안전하게 정지합니다...")
    should_stop_robot = True


def cleanup_all_robot_resources_before_exit():
    """
    프로그램 종료 전에 모든 로봇 자원을 안전하게 정리하는 함수
    """
    global is_robot_running

    print("\n🔌 로봇 시스템 종료 중...")

    # 자율주행 정지
    is_robot_running = False

    # 모든 모터 즉시 정지
    stop_all_motors_immediately()

    # 각 시스템별 자원 정리
    cleanup_all_motor_resources_safely()
    cleanup_ultrasonic_resources()

    # 성능 통계 출력
    print_final_performance_statistics()

    print("✅ 모든 시스템이 안전하게 종료되었습니다.")
    print("👋 프로그램을 종료합니다. 안전한 하루 되세요!")


# =============================================================================
# 메인 제어 루프 함수들
# =============================================================================


def collect_all_sensor_data_and_analyze() -> Dict[str, Any]:
    """
    모든 센서의 데이터를 수집하고 분석하는 함수

    이 함수는:
    1. 라인 센서 데이터를 읽고 로터리 상태를 분석
    2. 초음파 센서로 장애물을 감지
    3. 두 정보를 합쳐서 반환
    """

    # 1단계: 라인 센서 + 로터리 분석
    line_analysis = get_smart_driving_command_for_rotary_and_normal_sections(
        LINE_SENSOR_LEFT_PIN, LINE_SENSOR_CENTER_PIN, LINE_SENSOR_RIGHT_PIN
    )

    # 2단계: 초음파 센서 장애물 분석
    obstacle_analysis = get_complete_obstacle_status_and_recommendation()

    # 3단계: 두 정보를 합쳐서 반환
    combined_sensor_data = {
        "line_tracking": line_analysis,
        "obstacle_detection": obstacle_analysis,
        "timestamp": time.time(),
    }

    return combined_sensor_data


def decide_final_robot_action_using_sensor_fusion(
    sensor_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    여러 센서의 정보를 종합해서 최종 로봇 행동을 결정하는 함수

    우선순위 규칙:
    1. 초음파 센서 비상 상황 (10cm 이하) → 즉시 정지
    2. 초음파 센서 위험 상황 (20cm 이하) → 장애물 회피
    3. 일반 상황 → 라인 추적 (로터리 포함)
    """

    line_data = sensor_data["line_tracking"]
    obstacle_data = sensor_data["obstacle_detection"]

    # 1순위: 매우 위험한 장애물 (즉시 정지)
    if obstacle_data["danger_level"] == "very_dangerous":
        return {
            "final_action": "stop_all_motors",
            "final_speed": 0,
            "decision_reason": f"비상 정지! 장애물이 {obstacle_data['distance_cm']:.1f}cm 거리에 있음",
            "priority_level": "emergency",
            "controlling_system": "obstacle_avoidance",
        }

    # 2순위: 위험한 장애물 (고급 회피 전략 사용)
    elif obstacle_data["danger_level"] in ["dangerous", "very_dangerous"]:
        # 고급 장애물 회피 시스템 사용
        advanced_avoidance = get_complete_obstacle_avoidance_command(
            obstacle_data["distance_cm"],
            obstacle_data["danger_level"],
            line_data["position"],
        )

        return {
            "final_action": advanced_avoidance["action"],
            "final_speed": advanced_avoidance["speed"],
            "decision_reason": f"고급 회피: {advanced_avoidance['reason']}",
            "priority_level": advanced_avoidance.get("priority_level", "high"),
            "controlling_system": "advanced_obstacle_avoidance",
            "avoidance_strategy": advanced_avoidance.get(
                "avoidance_strategy", "unknown"
            ),
            "noise_filtered": obstacle_data.get("noise_filtered", False),
        }

    # 3순위: 라인 추적 (로터리 포함) + 장애물 거리 고려 속도 조정
    else:
        base_action = line_data["action"]
        base_speed = line_data["speed"]

        # 장애물 거리에 따른 속도 조정
        if obstacle_data["danger_level"] == "caution":
            adjusted_speed = int(base_speed * 0.7)  # 30% 속도 감소
            speed_reason = (
                f", 장애물 주의로 속도 감소 ({obstacle_data['distance_cm']:.1f}cm)"
            )
        else:
            adjusted_speed = base_speed
            speed_reason = ""

        return {
            "final_action": base_action,
            "final_speed": adjusted_speed,
            "decision_reason": f"라인 추적: {line_data['reason']}{speed_reason}",
            "priority_level": "normal",
            "controlling_system": "line_tracking",
        }


def execute_robot_control_command(control_command: Dict[str, Any]) -> None:
    """
    결정된 제어 명령을 실제로 실행하는 함수
    """
    action = control_command["final_action"]
    speed = control_command["final_speed"]

    # 모터 명령 실행
    execute_driving_action_with_speed(action, speed)


def run_one_complete_control_cycle() -> Dict[str, Any]:
    """
    하나의 완전한 제어 사이클을 실행하는 함수

    1. 센서 데이터 수집
    2. 행동 결정
    3. 명령 실행
    4. 결과 반환
    """
    global total_control_loops

    cycle_start_time = time.time()

    # 1단계: 센서 데이터 수집 및 분석
    sensor_data = collect_all_sensor_data_and_analyze()

    # 2단계: 최종 행동 결정
    control_decision = decide_final_robot_action_using_sensor_fusion(sensor_data)

    # 3단계: 명령 실행
    execute_robot_control_command(control_decision)

    # 4단계: 통계 업데이트
    total_control_loops += 1
    cycle_duration = time.time() - cycle_start_time

    # 결과 정보 구성
    cycle_result = {
        "cycle_number": total_control_loops,
        "cycle_duration_ms": cycle_duration * 1000,
        "sensor_data": sensor_data,
        "control_decision": control_decision,
    }

    return cycle_result


def main_autonomous_driving_loop():
    """
    메인 자율주행 루프 함수

    이 함수가 로봇의 "뇌" 역할을 합니다:
    - 100ms마다 센서를 읽고
    - 상황을 판단하고
    - 모터를 제어합니다
    """
    global is_robot_running, should_stop_robot, robot_start_time

    print("🚗 자율주행 시작!")
    print("🛑 정지하려면 Ctrl+C를 누르세요\n")

    robot_start_time = time.time()
    is_robot_running = True

    try:
        while is_robot_running and not should_stop_robot:
            loop_start_time = time.time()

            # 한 번의 완전한 제어 사이클 실행
            cycle_result = run_one_complete_control_cycle()

            # 주기적으로 상태 출력 (10번마다)
            if cycle_result["cycle_number"] % 10 == 0:
                print_current_driving_status(cycle_result)

            # 정확한 제어 주기 유지
            loop_duration = time.time() - loop_start_time
            sleep_time = max(0, CONTROL_LOOP_INTERVAL - loop_duration)
            time.sleep(sleep_time)

    except Exception as error:
        print(f"❌ 자율주행 중 오류 발생: {error}")
        stop_all_motors_immediately()

    finally:
        is_robot_running = False
        stop_all_motors_immediately()
        print("\n✅ 자율주행 루프 종료")


# =============================================================================
# 모니터링 및 디버깅 함수들
# =============================================================================


def print_current_driving_status(cycle_result: Dict[str, Any]) -> None:
    """
    현재 주행 상태를 화면에 출력하는 함수
    """
    cycle_num = cycle_result["cycle_number"]
    duration_ms = cycle_result["cycle_duration_ms"]
    decision = cycle_result["control_decision"]
    sensor_data = cycle_result["sensor_data"]

    print(f"\n--- 사이클 {cycle_num} (소요시간: {duration_ms:.1f}ms) ---")
    print(f"행동: {decision['final_action']} | 속도: {decision['final_speed']}%")
    print(
        f"제어: {decision['controlling_system']} | 우선순위: {decision['priority_level']}"
    )
    print(f"이유: {decision['decision_reason']}")

    # 센서 상세 정보
    line_info = sensor_data["line_tracking"]
    obstacle_info = sensor_data["obstacle_detection"]

    print(f"라인: {line_info['current_sensor']} | 로터리: {line_info['rotary_status']}")

    if obstacle_info["distance_cm"]:
        print(
            f"장애물: {obstacle_info['distance_cm']:.1f}cm ({obstacle_info['danger_level']})"
        )
    else:
        print("장애물: 측정 실패")


def print_final_performance_statistics() -> None:
    """
    프로그램 종료 시 최종 성능 통계를 출력하는 함수
    """
    if robot_start_time > 0:
        total_runtime = time.time() - robot_start_time
        average_frequency = (
            total_control_loops / total_runtime if total_runtime > 0 else 0
        )

        print(f"\n📊 성능 통계")
        print(f"총 실행 시간: {total_runtime:.1f}초")
        print(f"총 제어 루프: {total_control_loops}회")
        print(f"평균 주파수: {average_frequency:.1f}Hz")
        print(f"목표 주파수: {1/CONTROL_LOOP_INTERVAL:.1f}Hz")


def show_help_menu() -> None:
    """
    사용자 도움말을 출력하는 함수
    """
    print("\n📋 명령어 도움말:")
    print("  's' - 자율주행 시작")
    print("  'q' - 프로그램 종료")
    print("  'h' - 이 도움말 보기")
    print("  't' - 센서 테스트")
    print("  'r' - 시스템 재시작")


def test_all_sensors_step_by_step() -> None:
    """
    모든 센서를 단계별로 테스트하는 함수
    """
    print("🧪 센서 테스트 시작...")

    for i in range(5):
        print(f"\n--- 테스트 {i+1}/5 ---")

        # 센서 데이터 수집
        sensor_data = collect_all_sensor_data_and_analyze()

        # 라인 센서 정보
        line_info = sensor_data["line_tracking"]
        print(
            f"라인 센서: {line_info['current_sensor']} | 로터리: {line_info['rotary_status']}"
        )
        print(
            f"라인 빈도: 왼쪽={line_info['frequency_counts']['left']}, 가운데={line_info['frequency_counts']['center']}, 오른쪽={line_info['frequency_counts']['right']}"
        )

        # 초음파 센서 정보
        obstacle_info = sensor_data["obstacle_detection"]
        if obstacle_info["distance_cm"]:
            print(
                f"초음파 센서: {obstacle_info['distance_cm']:.1f}cm ({obstacle_info['danger_level']})"
            )
        else:
            print("초음파 센서: 측정 실패")

        time.sleep(1)

    print("✅ 센서 테스트 완료!")


# =============================================================================
# 사용자 인터페이스 함수들
# =============================================================================


def get_user_command_and_process() -> str:
    """
    사용자로부터 명령을 받아서 처리하는 함수
    """
    try:
        command = input("\n🎮 명령 입력 (h:도움말): ").strip().lower()

        if command == "s":
            return "start_driving"
        elif command == "q":
            return "quit_program"
        elif command == "h":
            show_help_menu()
            return "continue"
        elif command == "t":
            test_all_sensors_step_by_step()
            return "continue"
        elif command == "r":
            return "restart_system"
        else:
            print("❓ 알 수 없는 명령입니다. 'h'를 입력하여 도움말을 확인하세요.")
            return "continue"

    except (EOFError, KeyboardInterrupt):
        return "quit_program"


def start_autonomous_driving_with_countdown() -> None:
    """
    3초 카운트다운 후 자율주행을 시작하는 함수
    """
    print("\n🚗 자율주행을 시작합니다!")
    print("⚠️ 안전을 위해 로봇 주변을 확인하세요!")
    print("🛑 비상 정지: Ctrl+C")

    # 3초 카운트다운
    for i in range(3, 0, -1):
        print(f"⏰ {i}초 후 시작...")
        time.sleep(1)

    # 자율주행 시작
    main_autonomous_driving_loop()


def restart_robot_system() -> bool:
    """
    로봇 시스템을 재시작하는 함수
    """
    print("\n🔄 로봇 시스템 재시작 중...")

    # 기존 자원 정리
    stop_all_motors_immediately()
    cleanup_all_motor_resources_safely()
    cleanup_ultrasonic_resources()

    # 메모리 초기화
    reset_all_rotary_memory()

    # 시스템 재초기화
    success = initialize_all_robot_hardware_systems()

    if success:
        print("✅ 시스템 재시작 완료!")
    else:
        print("❌ 시스템 재시작 실패")

    return success


# =============================================================================
# 메인 함수
# =============================================================================


def main():
    """
    프로그램의 메인 함수

    이 함수에서:
    1. 시스템을 초기화하고
    2. 사용자 명령을 받고
    3. 자율주행을 실행합니다
    """
    print("🤖 간단한 자율주행 로봇 시스템")
    print("=" * 50)

    # 비상 정지 신호 처리 설정
    signal.signal(signal.SIGINT, handle_emergency_stop_signal)

    # 라즈베리파이 환경 확인
    try:
        import RPi.GPIO as GPIO

        print("✅ 라즈베리파이 환경 감지")
    except ImportError:
        print("⚠️ 라즈베리파이가 아닌 환경에서 실행 중")
        print("   일부 기능이 제한될 수 있습니다.")

    # 하드웨어 초기화
    if not initialize_all_robot_hardware_systems():
        print("❌ 하드웨어 초기화 실패로 프로그램을 종료합니다.")
        return

    print("\n🎉 로봇이 준비되었습니다!")
    show_help_menu()

    # 메인 사용자 인터페이스 루프
    try:
        while True:
            command_result = get_user_command_and_process()

            if command_result == "start_driving":
                start_autonomous_driving_with_countdown()

            elif command_result == "restart_system":
                if not restart_robot_system():
                    print("시스템 재시작 실패. 프로그램을 종료합니다.")
                    break

            elif command_result == "quit_program":
                break

            # 'continue'인 경우 계속 루프

    except KeyboardInterrupt:
        print("\n⚠️ Ctrl+C 감지 - 비상 정지")

    finally:
        cleanup_all_robot_resources_before_exit()


if __name__ == "__main__":
    main()
