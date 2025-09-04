# 🚀 Adeept AWR 자율주행 로봇 설치 가이드

이 문서는 Adeept AWR 자율주행 로봇을 라즈베리파이에 설치하는 방법을 설명합니다.

## 📋 요구사항

### 하드웨어
- **라즈베리파이 4B** (권장) 또는 3B+
- **Micro SD카드** 32GB 이상 (Class 10)
- **Motor HAT** (PCA9685 PWM 컨트롤러 포함)
- **기어모터 4개** + L298N 드라이버
- **라인센서 3개** (적외선)
- **초음파센서 1개** (HC-SR04)
- **LED 스트립** (WS2812, 16개)
- **부저**
- **외부 배터리** (7.4V-12V, 모터용)

### 소프트웨어
- **라즈베리파이 OS** (Bullseye 이상 권장)
- **Python 3.7+**
- **인터넷 연결** (설치 시에만)

## 🔧 설치 방법

### 1. 자동 설치 (권장)

가장 간단한 방법으로 setup.py 스크립트를 사용합니다.

```bash
# 프로젝트 다운로드
git clone https://github.com/your-repo/Adeept_AWR.git
cd Adeept_AWR

# 자동 설치 실행 (root 권한 필요)
sudo python3 setup.py
```

**자동 설치가 수행하는 작업:**
- ✅ 시스템 업데이트
- ✅ 필수 라이브러리 설치
- ✅ I2C, SPI 인터페이스 활성화
- ✅ 권한 설정
- ✅ 프로젝트 파일 구성
- ✅ 설치 테스트

### 2. 수동 설치

자동 설치가 실패하거나 단계별로 설치하고 싶은 경우:

#### 2.1 시스템 업데이트
```bash
sudo apt update
sudo apt upgrade -y
```

#### 2.2 필수 패키지 설치
```bash
# 시스템 패키지
sudo apt install -y python3-pip python3-dev python3-rpi.gpio i2c-tools git build-essential cmake

# Python 패키지
sudo pip3 install RPi.GPIO
sudo pip3 install rpi_ws281x
sudo pip3 install adafruit-pca9685
sudo pip3 install adafruit-circuitpython-pca9685
sudo pip3 install numpy PyYAML
```

#### 2.3 인터페이스 활성화
```bash
sudo raspi-config
```
다음 옵션들을 활성화하세요:
- **Interface Options** → **I2C** → **Enable**
- **Interface Options** → **SPI** → **Enable**

#### 2.4 재부팅
```bash
sudo reboot
```

## 🧪 설치 확인

설치가 완료되면 다음 명령어로 테스트해보세요:

### 기본 테스트
```bash
# GPIO 라이브러리 테스트
python3 -c "import RPi.GPIO; print('GPIO OK')"

# I2C 인터페이스 확인
i2cdetect -y 1

# LED 라이브러리 테스트 (선택적)
python3 -c "import rpi_ws281x; print('WS281X OK')"

# 서보모터 라이브러리 테스트
python3 -c "import Adafruit_PCA9685; print('PCA9685 OK')"
```

### 하드웨어 개별 테스트
```bash
# 기어모터 테스트
python3 hardware/test_gear_motors.py

# 라인센서 테스트
python3 hardware/test_line_sensors.py

# 초음파센서 테스트
python3 hardware/test_ultrasonic_sensor.py

# LED 스트립 테스트 (root 권한 필요)
sudo python3 hardware/test_led_strip.py

# 서보모터 테스트
python3 hardware/test_servo_motors.py
```

### 통합 시스템 테스트
```bash
# 메인 프로그램 실행
python3 main.py
```

## 🔧 문제 해결

### 일반적인 문제들

#### 1. Permission denied 오류
```bash
# GPIO 그룹에 사용자 추가
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER
sudo usermod -a -G spi $USER

# 로그아웃 후 다시 로그인
```

#### 2. I2C 장치가 감지되지 않음
```bash
# I2C 도구 설치 확인
sudo apt install -y i2c-tools

# I2C 인터페이스 활성화 확인
sudo raspi-config
# Interface Options → I2C → Enable

# 재부팅
sudo reboot

# I2C 장치 스캔
i2cdetect -y 1
```

#### 3. LED 제어 오류 (mmap failed)
```bash
# root 권한으로 실행
sudo python3 hardware/test_led_strip.py

# 또는 udev 규칙 설정
sudo nano /etc/udev/rules.d/99-gpio.rules
# 다음 내용 추가:
# SUBSYSTEM=="mem", GROUP="gpio", MODE="0664"
# KERNEL=="gpiomem", GROUP="gpio", MODE="0664"

sudo udevadm control --reload-rules
sudo reboot
```

#### 4. 서보모터가 동작하지 않음
```bash
# PCA9685 보드 I2C 주소 확인
i2cdetect -y 1
# 0x40 주소에서 장치가 감지되어야 함

# 서보모터 전원 확인 (5V)
# Motor HAT 연결 확인
```

#### 5. 모터가 동작하지 않음
```bash
# L298N 전원 확인 (12V 외부 배터리)
# GPIO 연결 확인
# 개별 테스트 실행
python3 hardware/test_gear_motors.py
```

### 로그 확인
```bash
# 시스템 로그
sudo journalctl -f

# dmesg 로그
dmesg | tail -20

# I2C 관련 로그
dmesg | grep i2c
```

## 📦 추가 라이브러리 (선택적)

### 영상 처리
```bash
sudo pip3 install opencv-python
sudo apt install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev
```

### 웹 인터페이스
```bash
sudo pip3 install flask websockets
```

### 게임/GUI
```bash
sudo pip3 install pygame
sudo apt install -y python3-pygame
```

## 🔄 업데이트

프로젝트 업데이트 시:

```bash
cd Adeept_AWR
git pull origin main

# 새로운 의존성이 있는 경우
pip3 install -r requirements.txt

# 또는 setup.py 재실행
sudo python3 setup.py
```

## 🚀 자동 시작 설정

시스템 부팅 시 로봇 프로그램을 자동으로 시작하려면:

```bash
# systemd 서비스 활성화 (setup.py에서 생성됨)
sudo systemctl enable adeept-awr.service
sudo systemctl start adeept-awr.service

# 상태 확인
sudo systemctl status adeept-awr.service

# 로그 확인
sudo journalctl -u adeept-awr.service -f
```

## 📞 지원

문제가 발생하면:

1. **GitHub Issues**: 버그 리포트 및 기능 요청
2. **Wiki**: 자세한 문서 및 튜토리얼
3. **Discussions**: 질문 및 토론

## 🔗 관련 링크

- [프로젝트 README](README.md)
- [하드웨어 핀아웃](pinout.md)
- [라즈베리파이 공식 문서](https://www.raspberrypi.org/documentation/)
- [GPIO 사용법](https://www.raspberrypi.org/documentation/usage/gpio/)

---

**📝 참고**: 이 가이드는 라즈베리파이 OS Bullseye 기준으로 작성되었습니다. 다른 OS 버전에서는 일부 단계가 다를 수 있습니다.
