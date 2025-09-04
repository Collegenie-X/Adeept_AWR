#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
초간단 자율 주행차 v3 (고등학생용)
Ultra Simple Autonomous Car v3 for High School Students

개선 사항:
1. 옵션 없이 바로 실행
2. 빈도수 기반 로터리 감지 (5번 중 몇 번)
3. 넓은 라인에도 대응하는 스마트 감지
"""

import time

# 하드웨어 가져오기
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from hardware.test_line_sensors import LineSensorController
    from hardware.test_gear_motors import GearMotorController
    from hardware.test_ultrasonic_sensor import UltrasonicSensor

    print("✓ 실제 하드웨어 사용")
    SIMULATION = False
except ImportError:
    print("⚠️ 시뮬레이션 모드")
    SIMULATION = True

# ==================== 설정값 ====================
# 기본 주행 속도
FORWARD_SPEED = 80  # 직진 속도

# 좌회전 세부 설정
LEFT_TURN_RIGHT_MOTOR = 100  # 좌회전시 우측 모터 (높은 속도)
LEFT_TURN_LEFT_MOTOR = 30  # 좌회전시 좌측 모터 (낮은 속도)

# 우회전 세부 설정
RIGHT_TURN_LEFT_MOTOR = 100  # 우회전시 좌측 모터 (높은 속도)
RIGHT_TURN_RIGHT_MOTOR = 30  # 우회전시 우측 모터 (낮은 속도)

# 장애물 회피 설정
SAFE_DISTANCE = 15  # 장애물 안전 거리 (cm)
AVOID_TIME = 0.8  # 회피 동작 시간 (초)

# 로터리 감지 설정 (빈도수 기반) - 새로운 알고리즘!
ROTARY_CHECK_SAMPLES = 5  # 체크할 샘플 수 (5번 측정)
ROTARY_DETECTION_RATIO = 0.6  # 감지 비율 (5번 중 3번 이상, 60%)
ROTARY_SAFE_SPEED = 40  # 로터리에서 안전 속도
ROTARY_DURATION = 3.0  # 로터리 모드 지속 시간 (초)

# 하드웨어 객체들
line_sensor = None
motor = None
ultrasonic = None

# 로터리 감지용 변수들 (빈도수 기반)
line_samples = []  # 최근 5번의 라인 상태 저장
rotary_mode = False
rotary_start_time = 0


def setup():
    """하드웨어 준비"""
    global line_sensor, motor, ultrasonic

    if not SIMULATION:
        try:
            line_sensor = LineSensorController()
            motor = GearMotorController()
            ultrasonic = UltrasonicSensor()
            print("✓ 하드웨어 준비 완료")
            return True
        except Exception as e:
            print(f"❌ 하드웨어 오류: {e}")
            return False
    else:
        print("✓ 시뮬레이션 준비 완료")
        return True


def read_line():
    """라인 위치 읽기"""
    if line_sensor:
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
        # 시뮬레이션 (로터리 시뮬레이션 포함)
        import random

        # 로터리 시뮬레이션: 주기적으로 복잡한 패턴 생성
        if random.random() < 0.08:  # 8% 확률로 로터리 시뮬레이션
            # 로터리에서는 라인이 자주 변함
            return random.choice(["left", "right", "none", "center"])
        else:
            # 일반 도로: 안정적인 패턴
            weights = [15, 60, 15, 10]  # center가 가장 높은 확률
            return random.choices(["left", "center", "right", "none"], weights=weights)[
                0
            ]


def read_distance():
    """앞의 거리 읽기"""
    if ultrasonic:
        distance = ultrasonic.measure_distance()
        return distance if distance else 999
    else:
        # 시뮬레이션
        import random

        if random.random() < 0.06:  # 6% 확률로 장애물
            distance = random.randint(5, SAFE_DISTANCE - 1)
            return distance
        else:
            return random.randint(SAFE_DISTANCE + 10, 100)


def check_rotary_frequency(current_line):
    """
    로터리 감지 알고리즘 (빈도수 기반)

    원리:
    1. 최근 5번의 라인 상태를 저장
    2. 5번 중 몇 번이 라인 변화인지 계산
    3. 설정 비율(60%) 이상이면 로터리로 판단
    """
    global line_samples, rotary_mode, rotary_start_time

    # 최근 5번의 샘플 유지
    line_samples.append(current_line)
    if len(line_samples) > ROTARY_CHECK_SAMPLES:
        line_samples.pop(0)  # 가장 오래된 것 제거

    # 충분한 샘플이 없으면 일반 모드
    if len(line_samples) < ROTARY_CHECK_SAMPLES:
        return False

    # 라인 변화 횟수 계산
    changes = 0
    for i in range(1, len(line_samples)):
        if line_samples[i] != line_samples[i - 1]:
            changes += 1

    # 변화 비율 계산
    change_ratio = changes / (ROTARY_CHECK_SAMPLES - 1)

    print(
        f"  📊 라인 변화: {changes}/{ROTARY_CHECK_SAMPLES-1} = {change_ratio:.2f} ({'로터리' if change_ratio >= ROTARY_DETECTION_RATIO else '일반'})"
    )

    # 로터리 감지 조건
    if change_ratio >= ROTARY_DETECTION_RATIO and not rotary_mode:
        rotary_mode = True
        rotary_start_time = time.time()
        line_samples.clear()  # 샘플 리셋
        print(f"🌀 로터리 감지! (변화율: {change_ratio:.2f}) 안전 모드 시작")
        return True

    # 로터리 모드 해제 조건
    if rotary_mode and (time.time() - rotary_start_time) > ROTARY_DURATION:
        rotary_mode = False
        line_samples.clear()  # 샘플 리셋
        print("✅ 로터리 통과 완료! 정상 모드 복귀")
        return False

    return rotary_mode


def stop():
    """정지"""
    if motor:
        motor.motor_stop()
        print("⏹️ 정지")
    else:
        print("시뮬레이션: 정지")


def go_forward(speed=None):
    """직진"""
    speed = speed or FORWARD_SPEED
    if motor:
        motor.set_motor_speed("A", speed)  # 오른쪽
        motor.set_motor_speed("B", speed)  # 왼쪽
        print(f"⬆️ 직진 (속도: {speed})")
    else:
        print(f"시뮬레이션: 직진 (속도: {speed})")


def turn_left():
    """좌회전 (개별 속도 설정)"""
    if motor:
        motor.set_motor_speed("A", LEFT_TURN_RIGHT_MOTOR)  # 오른쪽: 높은 속도
        motor.set_motor_speed("B", -LEFT_TURN_LEFT_MOTOR)  # 왼쪽: 낮은 속도 후진
        print(f"⬅️ 좌회전 (우측:{LEFT_TURN_RIGHT_MOTOR}, 좌측:-{LEFT_TURN_LEFT_MOTOR})")
    else:
        print(
            f"시뮬레이션: 좌회전 (우측:{LEFT_TURN_RIGHT_MOTOR}, 좌측:-{LEFT_TURN_LEFT_MOTOR})"
        )


def turn_right():
    """우회전 (개별 속도 설정)"""
    if motor:
        motor.set_motor_speed("A", -RIGHT_TURN_RIGHT_MOTOR)  # 오른쪽: 낮은 속도 후진
        motor.set_motor_speed("B", RIGHT_TURN_LEFT_MOTOR)  # 왼쪽: 높은 속도
        print(
            f"➡️ 우회전 (우측:-{RIGHT_TURN_RIGHT_MOTOR}, 좌측:{RIGHT_TURN_LEFT_MOTOR})"
        )
    else:
        print(
            f"시뮬레이션: 우회전 (우측:-{RIGHT_TURN_RIGHT_MOTOR}, 좌측:{RIGHT_TURN_LEFT_MOTOR})"
        )


def avoid_obstacle():
    """장애물 피하기 (좌회전 → 직진 → 우회전)"""
    print("🚨 장애물 회피 시작!")

    # 1단계: 좌회전
    print("  1. 좌회전으로 피하기")
    turn_left()
    time.sleep(AVOID_TIME)

    # 2단계: 직진으로 지나가기
    print("  2. 직진으로 지나가기")
    go_forward()
    time.sleep(AVOID_TIME)

    # 3단계: 우회전으로 원래 방향
    print("  3. 우회전으로 복귀")
    turn_right()
    time.sleep(AVOID_TIME)

    print("✅ 장애물 회피 완료!")


def smart_drive():
    """스마트 주행 (모든 기능 통합)"""
    # 1단계: 장애물 확인 (최우선)
    distance = read_distance()
    if distance < SAFE_DISTANCE:
        print(f"🚨 장애물 감지: {distance}cm")
        avoid_obstacle()
        return

    # 2단계: 라인 읽기
    line_position = read_line()

    # 3단계: 로터리 감지 (빈도수 기반)
    is_rotary = check_rotary_frequency(line_position)

    # 4단계: 주행 모드 결정
    if is_rotary:
        # 로터리 모드: 안전하게 천천히
        print(f"🌀 로터리 안전 주행: {line_position}")
        if line_position == "center":
            go_forward(ROTARY_SAFE_SPEED)
        elif line_position == "left":
            # 로터리에서는 부드럽게 회전
            go_forward(ROTARY_SAFE_SPEED // 2)
        elif line_position == "right":
            # 로터리에서는 부드럽게 회전
            go_forward(ROTARY_SAFE_SPEED // 2)
        else:  # none
            # 라인이 없어도 천천히 직진 (로터리 특성)
            go_forward(ROTARY_SAFE_SPEED // 3)
    else:
        # 일반 모드: 정상 속도로 라인 추적
        if line_position == "center":
            go_forward()
        elif line_position == "left":
            turn_right()
        elif line_position == "right":
            turn_left()
        else:  # none
            turn_left()  # 라인 찾기


def show_algorithm_info():
    """로터리 감지 알고리즘 설명"""
    print("\n" + "=" * 60)
    print("🧠 로터리 감지 알고리즘 (빈도수 기반)")
    print("=" * 60)
    print("📋 원리:")
    print("1. 최근 5번의 라인 센서 값을 저장")
    print("2. 연속된 값들 사이의 변화 횟수 계산")
    print("3. 변화율 = 변화횟수 / (샘플수-1)")
    print("4. 변화율이 60% 이상이면 로터리로 판단")
    print()
    print("📊 현재 설정:")
    print(f"   체크 샘플 수: {ROTARY_CHECK_SAMPLES}번")
    print(
        f"   감지 임계값: {ROTARY_DETECTION_RATIO*100}% (5번 중 {int(ROTARY_DETECTION_RATIO*4)}번 이상 변화)"
    )
    print(f"   로터리 지속시간: {ROTARY_DURATION}초")
    print(f"   로터리 안전속도: {ROTARY_SAFE_SPEED}")
    print()
    print("🔄 예시:")
    print("   일반 도로: [center, center, center, left, center] → 변화율 25% → 일반")
    print("   로터리:   [left, none, right, center, left] → 변화율 100% → 로터리")
    print("=" * 60)


def show_settings():
    """현재 설정 표시"""
    print("\n" + "=" * 50)
    print("🚗 초간단 자율 주행차 v3 설정")
    print("=" * 50)
    print("📈 기본 속도:")
    print(f"  직진 속도: {FORWARD_SPEED}")
    print()
    print("🔄 회전 속도 (개별 설정):")
    print(
        f"  좌회전 - 우측모터: {LEFT_TURN_RIGHT_MOTOR}, 좌측모터: {LEFT_TURN_LEFT_MOTOR}"
    )
    print(
        f"  우회전 - 우측모터: {RIGHT_TURN_RIGHT_MOTOR}, 좌측모터: {RIGHT_TURN_LEFT_MOTOR}"
    )
    print()
    print("🛡️ 장애물 회피:")
    print(f"  안전 거리: {SAFE_DISTANCE}cm")
    print(f"  회피 시간: {AVOID_TIME}초")
    print()
    print("🌀 로터리 감지 (빈도수 기반):")
    print(f"  체크 샘플 수: {ROTARY_CHECK_SAMPLES}번")
    print(f"  감지 임계값: {ROTARY_DETECTION_RATIO*100}%")
    print(f"  안전 속도: {ROTARY_SAFE_SPEED}")
    print(f"  지속 시간: {ROTARY_DURATION}초")
    print("=" * 50)


def cleanup():
    """정리"""
    try:
        stop()
        if line_sensor:
            line_sensor.cleanup()
        if motor:
            motor.cleanup()
        if ultrasonic:
            ultrasonic.cleanup()
        print("✓ 정리 완료")
    except:
        pass


def main():
    """메인 함수 - 바로 실행!"""
    print("🚗 초간단 자율 주행차 v3")
    print("=" * 40)
    print("새로운 기능:")
    print("✅ 빈도수 기반 로터리 감지")
    print("✅ LEFT/RIGHT 개별 모터 제어")
    print("✅ 넓은 라인 대응")
    print("=" * 40)

    # 설정과 알고리즘 정보 표시
    show_settings()
    show_algorithm_info()

    if not setup():
        print("❌ 하드웨어 준비 실패")
        return

    print("\n🚀 스마트 자율 주행 시작!")
    print("Ctrl+C로 언제든지 중단할 수 있습니다")
    print("=" * 50)

    try:
        while True:
            smart_drive()
            time.sleep(0.2)  # 0.2초마다 센서 체크

    except KeyboardInterrupt:
        print("\n\n⌨️ 사용자가 중단했습니다")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
    finally:
        cleanup()
        print("👋 프로그램 종료")


if __name__ == "__main__":
    main()
