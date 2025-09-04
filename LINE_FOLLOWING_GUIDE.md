# 🚗 라인 추적 자율 주행차 사용 가이드

라즈베리파이 기반 라인 센서를 이용한 자율 주행차 제어 프로그램들의 사용법을 설명합니다.

## 📋 프로그램 종류

### 1. **line_following_car.py** - 기본 버전
- **특징**: 전역 상수로 간단한 속도 조절
- **용도**: 기본적인 라인 추적 학습 및 테스트
- **설정**: 파일 상단의 전역 상수 직접 수정

### 2. **advanced_line_car.py** - 고급 버전  
- **특징**: 설정 파일 기반 고급 제어
- **용도**: 세밀한 튜닝 및 실전 주행
- **설정**: `car_config.py` 파일을 통한 설정 관리

### 3. **simple_main.py** - GUI 버전
- **특징**: tkinter GUI로 실시간 속도 조절
- **용도**: 시각적 인터페이스로 쉬운 조작
- **설정**: GUI trackbar로 실시간 조절

## 🚀 빠른 시작

### 기본 실행
```bash
# 기본 버전 (대화형 모드)
python3 line_following_car.py

# 고급 버전
python3 advanced_line_car.py

# GUI 버전
python3 simple_main.py

# 자동 실행 (5초 후 자동 시작)
python3 line_following_car.py --auto
```

### 설정 확인
```bash
# 현재 설정 보기
python3 car_config.py
```

## ⚙️ 속도 설정 방법

### 1. 기본 버전 설정 (line_following_car.py)

파일 상단의 전역 상수를 직접 수정:

```python
# 직진 속도 설정
FORWARD_SPEED = 50          # 직진 기본 속도 (0-100)

# 좌회전 속도 설정 (좌측으로 치우쳤을 때 우회전 필요)
LEFT_TURN_RIGHT_MOTOR = 60  # 우측 모터 속도 (직진)
LEFT_TURN_LEFT_MOTOR = 20   # 좌측 모터 속도 (감속 또는 후진)

# 우회전 속도 설정 (우측으로 치우쳤을 때 좌회전 필요)
RIGHT_TURN_LEFT_MOTOR = 60  # 좌측 모터 속도 (직진)
RIGHT_TURN_RIGHT_MOTOR = 20 # 우측 모터 속도 (감속 또는 후진)

# 라인 탐색 속도 (라인을 잃었을 때)
SEARCH_SPEED = 30           # 탐색 회전 속도
```

### 2. 고급 버전 설정 (car_config.py)

```python
# 직진 속도
FORWARD_SPEED = 50

# 좌회전 설정
LEFT_TURN_CONFIG = {
    "right_motor": 65,  # 우측 모터 속도 (빠르게)
    "left_motor": 25,   # 좌측 모터 속도 (느리게)
}

# 우회전 설정
RIGHT_TURN_CONFIG = {
    "left_motor": 65,   # 좌측 모터 속도 (빠르게)
    "right_motor": 25,  # 우측 모터 속도 (느리게)
}

# 급회전 설정
SHARP_TURN_CONFIG = {
    "speed_boost": 20,          # 추가 속도 증가
    "opposite_direction": True,  # 반대쪽 모터 후진 사용
}
```

## 🎮 조작 방법

### 대화형 모드 명령어

```
s - 자율 주행 시작
q - 정지 및 종료
h - 도움말
c - 현재 설정 보기
r - 설정 파일 다시 로드 (고급 버전만)
stat - 통계 보기 (고급 버전만)
```

### GUI 모드 (simple_main.py)
- **직진 속도 슬라이더**: 직진할 때의 기본 속도
- **코너링 강도 슬라이더**: 좌우 회전 시 속도 차이
- **시작/정지 버튼**: 자율 주행 제어

## 🔧 세부 설정 가이드

### 속도 설정 원리

1. **직진**: 양쪽 모터 동일 속도
2. **좌회전**: 우측 모터 빠르게, 좌측 모터 느리게
3. **우회전**: 좌측 모터 빠르게, 우측 모터 느리게
4. **라인 탐색**: 한쪽 전진, 한쪽 후진으로 제자리 회전

### 권장 설정값

#### 초보자 설정 (안정적)
```python
FORWARD_SPEED = 40
LEFT_TURN_RIGHT_MOTOR = 50
LEFT_TURN_LEFT_MOTOR = 20
RIGHT_TURN_LEFT_MOTOR = 50
RIGHT_TURN_RIGHT_MOTOR = 20
SEARCH_SPEED = 25
```

#### 중급자 설정 (균형)
```python
FORWARD_SPEED = 55
LEFT_TURN_RIGHT_MOTOR = 70
LEFT_TURN_LEFT_MOTOR = 25
RIGHT_TURN_LEFT_MOTOR = 70
RIGHT_TURN_RIGHT_MOTOR = 25
SEARCH_SPEED = 35
```

#### 고급자 설정 (고속)
```python
FORWARD_SPEED = 70
LEFT_TURN_RIGHT_MOTOR = 85
LEFT_TURN_LEFT_MOTOR = 30
RIGHT_TURN_LEFT_MOTOR = 85
RIGHT_TURN_RIGHT_MOTOR = 30
SEARCH_SPEED = 45
```

### 튜닝 팁

1. **직진이 불안정할 때**: `FORWARD_SPEED` 낮추기
2. **회전이 느릴 때**: 회전 속도 차이 늘리기
3. **급회전에서 벗어날 때**: `SHARP_TURN_CONFIG` 활용
4. **라인을 자주 놓칠 때**: `SEARCH_SPEED` 낮추기

## 🐛 문제 해결

### 일반적인 문제들

#### 1. 직진하지 않고 한쪽으로 치우침
```python
# 모터 보정 (한쪽이 더 빠른 경우)
FORWARD_SPEED_LEFT = 48   # 좌측 모터 약간 감속
FORWARD_SPEED_RIGHT = 52  # 우측 모터 약간 증속
```

#### 2. 코너에서 라인을 놓침
```python
# 회전 속도 차이 증가
LEFT_TURN_RIGHT_MOTOR = 70  # 더 빠르게
LEFT_TURN_LEFT_MOTOR = 15   # 더 느리게 (또는 후진)
```

#### 3. 라인 추적이 불안정함
```python
# 제어 주기 조정
CONTROL_FREQUENCY = 15  # 더 느린 제어 (더 안정적)

# 또는 센서 민감도 조정
SENSOR_CONFIG = {
    "position_threshold": 0.5,  # 더 낮은 값 (덜 민감)
    "stable_count": 3,          # 더 많은 연속 감지
}
```

#### 4. 시작 시 하드웨어 오류
```bash
# 권한 확인
sudo usermod -a -G gpio pi
sudo usermod -a -G i2c pi

# I2C 활성화 확인
sudo raspi-config
# Interface Options → I2C → Enable

# 재부팅
sudo reboot
```

## 📊 성능 모니터링

### 디버그 정보 활성화 (고급 버전)

```python
DEBUG_CONFIG = {
    "show_sensor_raw": True,    # 센서 원시값 표시
    "show_motor_speed": True,   # 모터 속도 표시  
    "show_position": True,      # 위치 정보 표시
    "update_interval": 0.1,     # 업데이트 주기
}
```

### 통계 정보
- 총 주행 시간
- 좌/우회전 횟수
- 라인 분실 횟수
- 회전 빈도

## 🔄 실시간 설정 변경

### 고급 버전에서 설정 변경
1. `car_config.py` 파일 수정
2. 프로그램에서 `r` 명령 입력
3. 즉시 새 설정 적용

### GUI 버전에서 설정 변경
- 슬라이더를 움직이면 즉시 적용
- 실시간으로 속도 조절 가능

## 🎯 고급 기능

### PID 제어 (향후 구현)
```python
PID_CONFIG = {
    "kp": 1.0,  # 비례 게인
    "ki": 0.0,  # 적분 게인
    "kd": 0.1,  # 미분 게인
}
```

### 안전 기능
```python
SAFETY_CONFIG = {
    "max_speed": 100,           # 최대 속도 제한
    "min_speed": -100,          # 최소 속도 제한
    "emergency_stop_time": 5.0, # 비상정지 대기 시간
}
```

## 📝 개발 참고사항

### 센서 패턴별 제어 로직

| 센서 패턴 | 위치값 | 동작 | 설명 |
|-----------|--------|------|------|
| `000` | None | 탐색 | 라인 없음 |
| `001` | +1.0 | 좌회전 | 우측 가장자리 |
| `010` | 0.0 | 직진 | 중앙 정확 |
| `011` | +0.5 | 약간 좌회전 | 중앙-우측 |
| `100` | -1.0 | 우회전 | 좌측 가장자리 |
| `101` | None | 탐색 | 교차점 또는 분실 |
| `110` | -0.5 | 약간 우회전 | 중앙-좌측 |
| `111` | 0.0 | 직진 | 넓은 라인 |

### 모터 제어 공식
```python
# 기본 제어
if position < 0:  # 우회전 필요
    right_motor = base_speed + turn_adjustment
    left_motor = base_speed - turn_adjustment
elif position > 0:  # 좌회전 필요  
    right_motor = base_speed - turn_adjustment
    left_motor = base_speed + turn_adjustment
else:  # 직진
    right_motor = left_motor = base_speed
```

---

💡 **팁**: 처음에는 낮은 속도로 시작해서 점진적으로 올려가며 최적값을 찾으세요!
