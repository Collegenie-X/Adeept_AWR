# 🤖 라즈베리파이 자율주행 로봇

라즈베리파이 기반의 지능형 자율주행 로봇 시스템입니다. 라인 추적과 장애물 회피 기능을 갖춘 모듈형 설계로 구현되었습니다.

## ✨ 주요 기능

- 🛤️ **라인 추적**: 3개 적외선 센서를 이용한 정확한 라인 추적
- 🚧 **장애물 회피**: 초음파 센서를 이용한 안전한 장애물 회피  
- 💡 **상태 표시**: WS2812 LED를 통한 직관적인 상태 표시
- 🔧 **모듈형 설계**: 유지보수가 용이한 컴포넌트 기반 아키텍처
- 🛡️ **안전 기능**: 비상 정지 및 예외 처리

## 🎯 프로젝트 구조

```
autonomous_robot/
├── controllers/              # 제어 로직
│   ├── autonomous_controller.py  # 메인 자율주행 컨트롤러
│   └── __init__.py
├── actuators/               # 액추에이터 제어
│   ├── motor_controller.py      # 4개 기어모터 제어
│   ├── led_controller.py        # LED 스트립 제어
│   └── __init__.py
├── sensors/                 # 센서 모듈
│   ├── line_sensor.py           # 라인 센서 (3개)
│   ├── ultrasonic_sensor.py     # 초음파 센서
│   └── __init__.py
├── utils/                   # 유틸리티 (확장용)
├── config/                  # 설정 파일 (확장용)
└── __init__.py
main.py                      # 메인 실행 파일
pinout.md                    # 하드웨어 핀아웃 가이드
prod.md                      # 제품 요구사항 문서
requirements.txt             # 의존성 라이브러리
```

## 🔧 하드웨어 요구사항

### 필수 하드웨어
- 라즈베리파이 4B+ (권장: 4GB RAM)
- L298N 모터 드라이버 
- 기어모터 4개
- HC-SR04 초음파 센서
- 적외선 라인 센서 3개
- WS2812 LED 스트립 (16개)
- 부저
- 12V 배터리 (모터용)
- 5V 전원 (라즈베리파이용)

### 선택적 하드웨어  
- PCA9685 PWM 확장 보드 (서보 모터용)
- 카메라 모듈 (향후 확장)

## 📦 설치 방법

### 1. 시스템 준비
```bash
# 라즈베리파이 OS 업데이트
sudo apt update && sudo apt upgrade -y

# GPIO 및 I2C 활성화
sudo raspi-config
# → Interface Options → I2C → Enable
# → Interface Options → GPIO → Enable
```

### 2. 프로젝트 클론
```bash
git clone https://github.com/your-username/Adeept_AWR.git
cd Adeept_AWR
```

### 3. 의존성 설치
```bash
# Python 라이브러리 설치
pip3 install -r requirements.txt

# 권한 설정
sudo usermod -a -G gpio $USER
```

### 4. 하드웨어 연결
`pinout.md` 파일을 참조하여 하드웨어를 연결하세요.

## 🚀 사용 방법

### 기본 실행
```bash
python3 main.py  # 메인 자율주행 프로그램 실행
```

### 하드웨어 테스트 실행
각 하드웨어 컴포넌트의 동작을 개별적으로 테스트하려면 다음 명령어를 사용하세요:
```bash
# 기어 모터 테스트
python3 hardware/test_gear_motors.py

# 초음파 센서 테스트
python3 hardware/test_ultrasonic_sensor.py

# 라인 센서 테스트
python3 hardware/test_line_sensors.py

# 서보 모터 테스트
python3 hardware/test_servo_motors.py
```

### 제어 명령어
실행 후 다음 명령어를 입력하세요:
- `s` - 자율주행 시작
- `q` - 프로그램 종료  
- `e` - 비상 정지
- `t` - 현재 상태 확인
- `r` - 시스템 재시작
- `h` - 도움말 보기

### 개별 모듈 테스트
```bash
# 모터 테스트
python3 -m autonomous_robot.actuators.motor_controller

# 라인 센서 테스트  
python3 -m autonomous_robot.sensors.line_sensor

# 초음파 센서 테스트
python3 -m autonomous_robot.sensors.ultrasonic_sensor

# LED 테스트
python3 -m autonomous_robot.actuators.led_controller
```

## 📋 설정

### GPIO 핀 매핑
기본 핀 매핑은 다음과 같습니다:

| 기능 | GPIO | 물리핀 |
|------|------|--------|
| 모터A Enable | 4 | 7 |
| 모터A Pin1 | 14 | 8 |
| 모터A Pin2 | 15 | 10 |
| 모터B Enable | 17 | 11 |
| 모터B Pin1 | 27 | 13 |
| 모터B Pin2 | 18 | 12 |
| LED 스트립 | 18 | 12 |
| 초음파 Trig | 23 | 16 |
| 초음파 Echo | 24 | 18 |
| 라인센서 좌측 | 19 | 35 |
| 라인센서 중앙 | 16 | 36 |
| 라인센서 우측 | 19 | 35 |
| 부저 | 20 | 38 |

상세한 핀아웃 정보는 `pinout.md`를 참조하세요.

## 🔍 문제 해결

### 일반적인 문제들

**Q: GPIO 권한 오류가 발생해요**
```bash
# 권한 설정 후 재부팅
sudo usermod -a -G gpio $USER
sudo reboot
```

**Q: LED가 켜지지 않아요**
```bash
# SPI 활성화 확인
sudo raspi-config
# → Interface Options → SPI → Enable
```

**Q: 모터가 동작하지 않아요**
- 전원 연결 확인 (12V 배터리)
- L298N 연결 확인
- GPIO 핀 매핑 확인

### 디버그 모드
```bash
# 상세 로그와 함께 실행
python3 main.py --debug
```

## 📚 API 문서

### MotorController
```python
from autonomous_robot.actuators.motor_controller import MotorController

motor = MotorController()
motor.initialize_gpio()
motor.move_forward(speed=80)    # 전진
motor.turn_left(speed=60)       # 좌회전
motor.stop_all_motors()         # 정지
```

### LineSensor  
```python
from autonomous_robot.sensors.line_sensor import LineSensor

line_sensor = LineSensor()
line_sensor.initialize_gpio()
command = line_sensor.get_driving_direction()
print(f"주행 명령: {command['action']}")
```

### UltrasonicSensor
```python
from autonomous_robot.sensors.ultrasonic_sensor import UltrasonicSensor

ultrasonic = UltrasonicSensor()
ultrasonic.initialize_gpio()
distance = ultrasonic.get_distance_with_history()
print(f"거리: {distance}cm")
```

## 🤝 기여하기

1. 프로젝트 포크
2. 기능 브랜치 생성 (`git checkout -b feature/새기능`)
3. 변경사항 커밋 (`git commit -am '새기능 추가'`)
4. 브랜치 푸시 (`git push origin feature/새기능`)
5. Pull Request 생성

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🏆 크레딧

- 원본 코드: [Adeept AWR](https://github.com/adeept/Adeept_AWR)
- 개선 및 모듈화: 라즈베리파이 자율주행 프로젝트 팀

## 📞 지원

- 📖 문서: `prod.md`, `pinout.md` 참조
- 🐛 버그 리포트: GitHub Issues
- 💡 기능 요청: GitHub Issues
- 📧 기술 지원: 프로젝트 관리자에게 문의

---

**🚀 즐거운 로봇 개발 되세요!** 🤖