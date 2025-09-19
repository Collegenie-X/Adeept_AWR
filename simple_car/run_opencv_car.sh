#!/bin/bash

# OpenCV 카메라 기반 자율주행차 실행 스크립트
# OpenCV Camera-based Autonomous Car Runner Script

echo "🚗 Starting OpenCV Camera-based Autonomous Car"
echo "=============================================="

# 현재 디렉토리 확인
if [ ! -f "free_car_opencv.py" ]; then
    echo "❌ free_car_opencv.py not found in current directory"
    echo "💡 Please run this script from the simple_car directory"
    exit 1
fi

# Python 버전 확인
echo "🐍 Checking Python environment..."
python3 --version

# OpenCV 확인
echo "📷 Checking OpenCV..."
python3 -c "import cv2; print(f'OpenCV {cv2.__version__} is available')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ OpenCV not found!"
    echo "💡 Install with: sudo apt install python3-opencv"
    exit 1
fi

# 카메라 디바이스 확인
echo "📹 Checking camera devices..."
if ls /dev/video* >/dev/null 2>&1; then
    echo "✅ Camera devices found:"
    ls -la /dev/video* | head -3
else
    echo "⚠️ No camera devices found"
    echo "💡 Running anyway (will use simulation mode)"
fi

# GPU 메모리 확인 (라즈베리파이인 경우)
if command -v vcgencmd >/dev/null 2>&1; then
    echo "🧠 Checking GPU memory..."
    gpu_mem=$(vcgencmd get_mem gpu 2>/dev/null | cut -d= -f2 | cut -d'M' -f1)
    if [ ! -z "$gpu_mem" ]; then
        echo "   GPU Memory: ${gpu_mem}M"
        if [ "$gpu_mem" -lt 64 ]; then
            echo "⚠️ Low GPU memory. Consider increasing to 128M"
            echo "💡 sudo raspi-config -> Advanced -> Memory Split -> 128"
        fi
    fi
fi

# 권한 확인
echo "🔐 Checking permissions..."
if groups $USER | grep -q video; then
    echo "✅ User has video group access"
else
    echo "⚠️ User not in video group"
    echo "💡 Run: sudo usermod -a -G video $USER && sudo reboot"
fi

echo ""
echo "🚀 Starting program..."
echo "Press Ctrl+C to stop safely"
echo ""

# 프로그램 실행
python3 free_car_opencv.py

echo ""
echo "✅ Program ended"
