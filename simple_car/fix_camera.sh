#!/bin/bash

# 라즈베리파이 카메라 문제 해결 스크립트
# Raspberry Pi Camera Problem Fix Script

echo "🔧 Raspberry Pi Camera Fix Script"
echo "================================="

# 현재 사용자 확인
echo "👤 Current user: $(whoami)"

# 1. 카메라 모듈 활성화 확인
echo "📷 Checking camera module status..."
if lsmod | grep -q bcm2835_v4l2; then
    echo "✅ Camera module is loaded"
else
    echo "⚠️ Camera module not loaded, attempting to load..."
    sudo modprobe bcm2835-v4l2
    if [ $? -eq 0 ]; then
        echo "✅ Camera module loaded successfully"
    else
        echo "❌ Failed to load camera module"
    fi
fi

# 2. GPU 메모리 분할 확인
echo "🧠 Checking GPU memory split..."
gpu_mem=$(vcgencmd get_mem gpu | cut -d= -f2 | cut -d'M' -f1)
echo "   Current GPU memory: ${gpu_mem}M"

if [ "$gpu_mem" -lt 128 ]; then
    echo "⚠️ GPU memory is low (recommended: 128M or higher)"
    echo "💡 To fix: sudo raspi-config -> Advanced Options -> Memory Split -> 128"
else
    echo "✅ GPU memory is sufficient"
fi

# 3. 카메라 디바이스 확인
echo "📹 Checking camera devices..."
if ls /dev/video* >/dev/null 2>&1; then
    echo "✅ Found camera devices:"
    ls -la /dev/video*
else
    echo "❌ No camera devices found"
    echo "💡 Try: sudo modprobe uvcvideo"
fi

# 4. 사용자 권한 확인
echo "🔐 Checking user permissions..."
if groups $USER | grep -q video; then
    echo "✅ User is in video group"
else
    echo "⚠️ User not in video group, adding..."
    sudo usermod -a -G video $USER
    echo "✅ User added to video group (reboot required)"
fi

# 5. 시스템 메모리 확인
echo "💾 Checking system memory..."
mem_available=$(awk '/MemAvailable/ {print $2}' /proc/meminfo)
mem_mb=$((mem_available / 1024))
echo "   Available memory: ${mem_mb}MB"

if [ "$mem_mb" -lt 100 ]; then
    echo "⚠️ Low memory available"
    echo "💡 Consider closing other applications"
else
    echo "✅ Memory looks good"
fi

# 6. OpenCV 버전 확인
echo "🐍 Checking OpenCV installation..."
python3 -c "import cv2; print(f'OpenCV version: {cv2.__version__}')" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ OpenCV is installed"
else
    echo "❌ OpenCV not found"
    echo "💡 Install with: sudo apt install python3-opencv"
fi

# 7. 카메라 설정 확인 (라즈베리파이 카메라인 경우)
echo "🔍 Checking Raspberry Pi camera config..."
if grep -q "^camera_auto_detect=1" /boot/config.txt 2>/dev/null; then
    echo "✅ Camera auto-detect enabled"
elif grep -q "^start_x=1" /boot/config.txt 2>/dev/null; then
    echo "✅ Legacy camera support enabled"
else
    echo "⚠️ Camera may not be enabled in config"
    echo "💡 Enable with: sudo raspi-config -> Interface Options -> Camera"
fi

# 8. 해결 방법 제안
echo ""
echo "🔧 Recommended fixes for common issues:"
echo "======================================="
echo ""
echo "1. For 'Failed to allocate required memory' error:"
echo "   sudo raspi-config -> Advanced Options -> Memory Split -> 128"
echo "   sudo reboot"
echo ""
echo "2. For permission issues:"
echo "   sudo usermod -a -G video \$USER"
echo "   sudo reboot"
echo ""
echo "3. For USB camera issues:"
echo "   sudo modprobe uvcvideo"
echo "   Try different USB ports"
echo ""
echo "4. For Raspberry Pi camera issues:"
echo "   sudo raspi-config -> Interface Options -> Camera -> Enable"
echo "   sudo reboot"
echo ""
echo "5. If still not working:"
echo "   Try lower resolution (160x120)"
echo "   Reduce frame rate"
echo "   Use CAP_V4L2 backend"
echo ""
echo "6. Test camera with provided script:"
echo "   python3 camera_test.py"
echo ""
echo "✅ Camera diagnostic completed!"
