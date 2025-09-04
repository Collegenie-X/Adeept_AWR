# 🤖 Adeept AWR 자율주행 로봇

라즈베리파이 기반 4륜 자율주행 로봇 프로젝트입니다. 라인 추적, 장애물 회피, LED 상태 표시 등의 기능을 통합한 완전한 자율주행 시스템을 제공합니다.

## 📋 프로젝트 개요

### 🎯 주요 기능
- **라인 추적**: 3개 적외선 센서를 이용한 정밀한 라인 추적
- **장애물 회피**: 초음파 센서를 이용한 실시간 장애물 감지 및 회피
- **자율 주행**: 라인 추적과 장애물 회피를 결합한 완전 자율 주행
- **LED 상태 표시**: 16개 WS2812 LED로 로봇 상태 시각화
- **수동 제어**: 키보드를 이용한 직접 제어 모드

### 🔧 하드웨어 구성
- **컨트롤러**: 라즈베리파이 4B + Motor HAT
- **구동부**: 4개 기어모터 + L298N 드라이버
- **센서**: 라인센서 3개 + 초음파센서 1개
- **출력**: WS2812 LED 스트립 16개 + 부저
- **서보모터**: PCA9685 PWM 컨트롤러 (16채널)

## 🚀 빠른 시작

### 1. 자동 설치 (권장)
```bash
# 프로젝트 다운로드
git clone https://github.com/your-repo/Adeept_AWR.git
cd Adeept_AWR

# 자동 설치 스크립트 실행
sudo python3 setup.py
```

### 2. 수동 설치
```bash
# 기본 시스템 패키지
sudo apt update
sudo apt install python3-pip python3-rpi.gpio i2c-tools

# Python 라이브러리 일괄 설치
pip3 install -r requirements.txt

# 또는 개별 설치
sudo pip3 install rpi-ws281x adafruit-pca9685

# 인터페이스 활성화
sudo raspi-config  # Interface Options → I2C, SPI → Enable

# 재부팅
sudo reboot
```

### 3. 프로젝트 실행
```bash
# 통합 자율주행 로봇 실행
python3 main.py

# 개별 하드웨어 테스트
python3 hardware/test_gear_motors.py      # 모터 테스트
python3 hardware/test_line_sensors.py    # 라인센서 테스트
python3 hardware/test_ultrasonic_sensor.py  # 초음파센서 테스트
sudo python3 hardware/test_led_strip.py     # LED 테스트 (root 권한 필요)
python3 hardware/test_servo_motors.py   # 서보모터 테스트
```

### 4. 조작 방법
메인 프로그램 실행 후 다음 명령어로 조작:
- `1`: 라인 추적 모드
- `2`: 장애물 회피 모드  
- `3`: 자율 주행 모드
- `4`: 수동 제어 모드
- `w/a/s/d`: 전진/좌회전/후진/우회전 (수동 모드)
- `space`: 정지
- `s`: 센서 데이터 확인
- `servo <채널> <각도>`: 서보모터 제어 (예: servo 0 90)
- `center <채널>`: 서보모터 중앙 위치 (예: center 0)
- `sweep <채널>`: 서보모터 스윕 동작 (예: sweep 0)
- `q`: 종료

## 📍 핀아웃 정보

### GPIO 핀 매핑
| 구성요소 | GPIO | 물리핀 | 기능 |
|---------|------|--------|------|
| 모터 A Enable | 4 | 7 | 우측 모터 PWM |
| 모터 A Pin1 | 14 | 8 | 우측 모터 방향1 |
| 모터 A Pin2 | 15 | 10 | 우측 모터 방향2 |
| 모터 B Enable | 17 | 11 | 좌측 모터 PWM |
| 모터 B Pin1 | 27 | 13 | 좌측 모터 방향1 |
| 모터 B Pin2 | 18 | 12 | 좌측 모터 방향2 |
| 초음파 Trigger | 11 | 23 | HC-SR04 트리거 |
| 초음파 Echo | 8 | 24 | HC-SR04 에코 |
| 라인센서 좌측 | 20 | 38 | 좌측 라인감지 |
| 라인센서 중앙 | 16 | 36 | 중앙 라인감지 |
| 라인센서 우측 | 19 | 35 | 우측 라인감지 |
| LED 스트립 | 12 | 32 | WS2812 제어 |
| 부저 | 20 | 38 | 사운드 출력 |

⚠️ **주의**: GPIO 20번 핀이 라인센서 좌측과 부저에서 공유됩니다.

## 📁 프로젝트 구조

```
Adeept_AWR/
├── main.py                           # 메인 통합 제어 프로그램
├── pinout.md                         # 상세 핀아웃 정보
├── README.md                         # 프로젝트 설명서
├── requirements.txt                  # 의존성 패키지 목록
├── hardware/                         # 하드웨어 제어 모듈
│   ├── test_gear_motors.py          # 기어모터 테스트
│   ├── test_line_sensors.py         # 라인센서 테스트  
│   ├── test_ultrasonic_sensor.py    # 초음파센서 테스트
│   ├── test_led_strip.py            # LED 스트립 테스트
│   └── test_servo_motors.py         # 서보모터 테스트
├── autonomous_robot/                 # 자율주행 로직 모듈
│   ├── actuators/                   # 액추에이터 제어
│   ├── sensors/                     # 센서 처리
│   ├── controllers/                 # 제어 알고리즘
│   └── utils/                       # 유틸리티 함수
├── code/                            # 원본 Adeept 코드
├── datasheet/                       # 하드웨어 데이터시트
└── document/                        # 프로젝트 문서
```

## 🔧 개발 가이드

### 모듈 구조
각 하드웨어 구성요소는 독립적인 모듈로 설계되어 있습니다:

- **GearMotorController**: 4개 기어모터 제어
- **LineSensorController**: 3개 라인센서 처리  
- **UltrasonicSensor**: 초음파 거리측정
- **LEDStripController**: 16개 WS2812 LED 제어

### 알고리즘 특징
- **PID 제어**: 부드러운 라인 추적 구현
- **상태 기반**: 로봇 상태에 따른 LED 색상 변경
- **안전 우선**: 장애물 감지 시 즉시 회피 동작
- **모듈형 설계**: 각 기능을 독립적으로 테스트 및 개발 가능

## 🚨 문제 해결

### 일반적인 문제
1. **Permission denied 오류**
   - LED 제어 시: `sudo python3 test_led_strip.py`
   - GPIO 접근 권한 필요

2. **센서 값이 이상할 때**
   - 연결 상태 확인
   - 개별 테스트 파일로 하드웨어 점검

3. **모터가 동작하지 않을 때**
   - 전원 공급 확인 (12V 외부 배터리)
   - L298N 연결 상태 확인

### 디버깅 도구
```bash
# GPIO 상태 확인
gpio readall

# I2C 장치 스캔  
i2cdetect -y 1

# 개별 하드웨어 테스트
python3 hardware/test_*.py

# 설치 테스트
python3 -c "import RPi.GPIO; print('GPIO OK')"
python3 -c "import rpi_ws281x; print('LED OK')"
python3 -c "import Adafruit_PCA9685; print('Servo OK')"
```

## 🚀 자동 설치 스크립트

`setup.py` 스크립트가 자동으로 수행하는 작업:

### ✅ 시스템 환경 구성
- 라즈베리파이 확인
- 시스템 업데이트 및 업그레이드
- 불필요한 패키지 제거 (공간 확보)

### ✅ 라이브러리 설치
- 필수 시스템 패키지 설치
- Python 라이브러리 자동 설치
- 의존성 해결

### ✅ 하드웨어 인터페이스 활성화
- I2C 인터페이스 활성화
- SPI 인터페이스 활성화  
- GPIO 접근 권한 설정

### ✅ 프로젝트 구성
- 실행 권한 설정
- 로그 디렉토리 생성
- systemd 서비스 생성 (자동 시작 지원)

### ✅ 설치 테스트
- 각 라이브러리 동작 확인
- 하드웨어 인터페이스 테스트
- 전체 시스템 검증

### 사용법
```bash
# 기본 설치
sudo python3 setup.py

# 설치 후 자동 시작 설정
sudo systemctl enable adeept-awr.service
sudo systemctl start adeept-awr.service
```

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 LICENSE 파일을 참조하세요.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)  
5. Open a Pull Request

## 📞 지원 및 문의

- 🐛 버그 리포트: GitHub Issues
- 💡 기능 제안: GitHub Discussions
- 📧 직접 문의: [이메일 주소]

---

**⚠️ 중요**: 실제 하드웨어 연결 시 pinout.md 파일의 상세 정보를 반드시 확인하세요.

**🔧 개발 환경**: Python 3.7+, 라즈베리파이 OS