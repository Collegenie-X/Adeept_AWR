#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
자율 주행차 설정 파일
Car Configuration File

이 파일의 값들을 수정하여 자동차의 동작을 조절할 수 있습니다.
"""

# ==================== 속도 설정 ====================

# 직진 속도 (0-100)
FORWARD_SPEED = 50

# 좌회전 시 속도 (라인이 좌측으로 치우쳤을 때 우회전 필요)
LEFT_TURN_CONFIG = {
    "right_motor": 65,  # 우측 모터 속도 (빠르게)
    "left_motor": 25,  # 좌측 모터 속도 (느리게)
}

# 우회전 시 속도 (라인이 우측으로 치우쳤을 때 좌회전 필요)
RIGHT_TURN_CONFIG = {
    "left_motor": 65,  # 좌측 모터 속도 (빠르게)
    "right_motor": 25,  # 우측 모터 속도 (느리게)
}

# 급회전 설정 (라인이 많이 치우쳤을 때)
SHARP_TURN_CONFIG = {
    "speed_boost": 20,  # 추가 속도 증가
    "opposite_direction": True,  # 반대쪽 모터 후진 사용
}

# 라인 탐색 속도 (라인을 잃었을 때)
SEARCH_SPEED = 35

# ==================== 제어 설정 ====================

# 제어 주기 (Hz)
CONTROL_FREQUENCY = 20

# 라인 분실 허용 시간 (초)
LINE_LOST_TIMEOUT = 0.3

# 센서 민감도 설정
SENSOR_CONFIG = {
    "position_threshold": 0.7,  # 급회전 판단 기준
    "stable_count": 2,  # 안정 판단을 위한 연속 감지 횟수
}

# ==================== 디버그 설정 ====================

# 출력 설정
DEBUG_CONFIG = {
    "show_sensor_raw": True,  # 원시 센서 값 표시
    "show_motor_speed": True,  # 모터 속도 표시
    "show_position": True,  # 위치 정보 표시
    "update_interval": 0.1,  # 화면 업데이트 간격
}

# 시뮬레이션 설정
SIMULATION_CONFIG = {
    "random_scenarios": True,  # 랜덤 시나리오 사용
    "scenario_change_rate": 2,  # 시나리오 변경 빈도 (초)
}

# ==================== 고급 설정 ====================

# PID 제어 설정 (향후 구현용)
PID_CONFIG = {
    "kp": 1.0,  # 비례 게인
    "ki": 0.0,  # 적분 게인
    "kd": 0.1,  # 미분 게인
}

# 안전 설정
SAFETY_CONFIG = {
    "max_speed": 100,  # 최대 속도 제한
    "min_speed": -100,  # 최소 속도 제한 (후진)
    "emergency_stop_time": 5.0,  # 비상정지 대기 시간
}


# ==================== 설정 검증 함수 ====================


def validate_config():
    """설정값 유효성 검사"""
    errors = []

    # 속도 범위 검사
    if not (0 <= FORWARD_SPEED <= 100):
        errors.append(f"FORWARD_SPEED ({FORWARD_SPEED})는 0-100 범위여야 합니다.")

    if not (0 <= SEARCH_SPEED <= 100):
        errors.append(f"SEARCH_SPEED ({SEARCH_SPEED})는 0-100 범위여야 합니다.")

    # 회전 속도 검사
    for motor_speed in [
        LEFT_TURN_CONFIG["right_motor"],
        LEFT_TURN_CONFIG["left_motor"],
        RIGHT_TURN_CONFIG["left_motor"],
        RIGHT_TURN_CONFIG["right_motor"],
    ]:
        if not (-100 <= motor_speed <= 100):
            errors.append(f"모터 속도 ({motor_speed})는 -100~100 범위여야 합니다.")

    # 주파수 검사
    if not (1 <= CONTROL_FREQUENCY <= 100):
        errors.append(
            f"CONTROL_FREQUENCY ({CONTROL_FREQUENCY})는 1-100 범위여야 합니다."
        )

    return errors


def print_config():
    """현재 설정 출력"""
    print("\n" + "=" * 60)
    print("🚗 자율 주행차 설정")
    print("=" * 60)
    print(f"직진 속도: {FORWARD_SPEED}%")
    print(
        f"좌회전 시: 우측모터 {LEFT_TURN_CONFIG['right_motor']}%, 좌측모터 {LEFT_TURN_CONFIG['left_motor']}%"
    )
    print(
        f"우회전 시: 좌측모터 {RIGHT_TURN_CONFIG['left_motor']}%, 우측모터 {RIGHT_TURN_CONFIG['right_motor']}%"
    )
    print(f"라인 탐색 속도: {SEARCH_SPEED}%")
    print(f"제어 주파수: {CONTROL_FREQUENCY}Hz")
    print(f"라인 분실 허용시간: {LINE_LOST_TIMEOUT}초")

    if SHARP_TURN_CONFIG["opposite_direction"]:
        print("급회전 모드: 반대방향 모터 사용")
    else:
        print("급회전 모드: 속도 차이만 사용")

    print("=" * 60)

    # 설정 검증
    errors = validate_config()
    if errors:
        print("⚠️ 설정 오류:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ 모든 설정이 유효합니다.")
    print()


if __name__ == "__main__":
    print_config()
