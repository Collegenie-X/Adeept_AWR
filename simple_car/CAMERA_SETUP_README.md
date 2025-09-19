# 📷 Raspberry Pi Camera Setup Guide

OpenCV 카메라 기반 자율주행차 설정 가이드

## 🚨 카메라 오류 해결 방법

### 에러 메시지: "Failed to allocate required memory"

이 에러는 라즈베리파이에서 카메라 메모리 할당 문제로 발생합니다.

## 🔧 해결 방법 (단계별)

### 1. 자동 진단 및 수정 실행
```bash
# 카메라 진단 스크립트 실행
bash fix_camera.sh

# 카메라 테스트 스크립트 실행  
python3 camera_test.py
```

### 2. GPU 메모리 증가 (가장 중요!)
```bash
sudo raspi-config
```
- **Advanced Options** → **Memory Split** → **128** 입력
- 재부팅: `sudo reboot`

### 3. 카메라 모듈 활성화
```bash
sudo raspi-config
```
- **Interface Options** → **Camera** → **Enable**
- 재부팅: `sudo reboot`

### 4. 카메라 모듈 로드
```bash
# 라즈베리파이 카메라용
sudo modprobe bcm2835-v4l2

# USB 카메라용
sudo modprobe uvcvideo
```

### 5. 사용자 권한 설정
```bash
sudo usermod -a -G video $USER
sudo reboot
```

### 6. 시스템 업데이트
```bash
sudo apt update
sudo apt upgrade
sudo apt install python3-opencv
```

## 🚀 프로그램 실행

### 방법 1: 자동 실행 스크립트
```bash
cd simple_car
bash run_opencv_car.sh
```

### 방법 2: 직접 실행
```bash
cd simple_car
python3 free_car_opencv.py
```

## 🔍 문제 진단

### 카메라 디바이스 확인
```bash
ls -la /dev/video*
```

### 카메라 모듈 확인
```bash
lsmod | grep -E "uvcvideo|bcm2835"
```

### GPU 메모리 확인
```bash
vcgencmd get_mem gpu
```

### OpenCV 설치 확인
```bash
python3 -c "import cv2; print(cv2.__version__)"
```

## 💡 추가 팁

### 1. 메모리 부족 시
- 다른 프로그램 종료
- 스왑 파일 활성화
- 더 낮은 해상도 사용 (160x120)

### 2. USB 카메라 사용 시
- 다른 USB 포트 시도
- 전원이 충분한 USB 허브 사용
- USB 2.0 포트 사용

### 3. 라즈베리파이 카메라 사용 시
- 케이블 연결 확인
- 카메라 모듈 정품 여부 확인
- `/boot/config.txt`에서 카메라 설정 확인

## 🎛️ 프로그램 제어 방법

### 기본 제어
- **Enter**: 자동 주행 시작
- **Space**: 즉시 정지
- **q**: 프로그램 종료

### 카메라 전용 제어
- **v**: 비전 디버그 모드 ON/OFF
- **c**: 카메라 시스템 상태 확인
- **n/m**: 방향 판단 임계값 조정

### 속도 조절
- **1/2**: 전진 속도 조절
- **3/4**: 약한 회전 속도 조절
- **5/6**: 강한 회전 속도 조절

### 수동 제어
- **w,a,s,d**: 수동 이동
- **화살표 키**: 수동 이동

## 🐛 여전히 문제가 있다면

1. **시스템 재부팅**
   ```bash
   sudo reboot
   ```

2. **카메라 하드웨어 확인**
   - 연결 상태 점검
   - 다른 카메라로 테스트

3. **로그 확인**
   ```bash
   dmesg | grep -i camera
   dmesg | grep -i video
   ```

4. **시뮬레이션 모드로 실행**
   - 카메라 없이도 프로그램 동작 확인 가능
   - 키보드 제어로 기본 기능 테스트

## 📁 파일 설명

- `free_car_opencv.py`: 메인 프로그램
- `camera_test.py`: 카메라 진단 도구
- `fix_camera.sh`: 자동 수정 스크립트
- `run_opencv_car.sh`: 실행 스크립트
- `components/camera_vision_service.py`: 카메라 제어 모듈
- `components/yellow_line_detector.py`: 노란선 감지 모듈

## ✅ 성공적인 실행 예시

```
🎥 Initializing camera... (ID: 0)
  Trying V4L2 (Video4Linux)...
✅ Success with V4L2 (Video4Linux)
✅ Camera ready: 320x240
Hardware(camera=✅, motor=False, ultrasonic=False) ready
📷 Camera: 320x240
🎯 Detection: Yellow line tracking with histogram analysis
```

이 가이드를 따라하면 라즈베리파이에서 카메라 문제를 해결할 수 있습니다! 🎉
