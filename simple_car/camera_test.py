#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
라즈베리파이 카메라 테스트 스크립트
Raspberry Pi Camera Test Script

라즈베리파이에서 카메라 문제 진단 및 테스트
"""

import cv2
import numpy as np
import time
import sys


def test_camera_backends():
    """다양한 카메라 백엔드 테스트"""
    print("🔍 Testing different camera backends...")
    
    backends = [
        (cv2.CAP_ANY, "CAP_ANY"),
        (cv2.CAP_V4L2, "CAP_V4L2"), 
        (cv2.CAP_GSTREAMER, "CAP_GSTREAMER"),
        (cv2.CAP_FFMPEG, "CAP_FFMPEG")
    ]
    
    working_backends = []
    
    for backend_id, backend_name in backends:
        try:
            print(f"  Testing {backend_name}...")
            cap = cv2.VideoCapture(0, backend_id)
            
            if cap.isOpened():
                # 해상도 설정 시도
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
                
                # 프레임 읽기 시도
                time.sleep(1)  # 카메라 초기화 대기
                ret, frame = cap.read()
                
                if ret and frame is not None and frame.size > 0:
                    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    print(f"    ✅ {backend_name} - Success ({actual_width}x{actual_height})")
                    working_backends.append((backend_id, backend_name))
                else:
                    print(f"    ❌ {backend_name} - Failed to read frame")
                cap.release()
            else:
                print(f"    ❌ {backend_name} - Failed to open")
                
        except Exception as e:
            print(f"    ❌ {backend_name} - Error: {e}")
    
    return working_backends


def test_camera_resolutions(backend_id):
    """다양한 해상도 테스트"""
    print(f"\n📐 Testing different resolutions with backend {backend_id}...")
    
    resolutions = [
        (160, 120),
        (320, 240), 
        (640, 480),
        (800, 600),
        (1024, 768)
    ]
    
    working_resolutions = []
    
    for width, height in resolutions:
        try:
            cap = cv2.VideoCapture(0, backend_id)
            if not cap.isOpened():
                continue
                
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
            time.sleep(0.5)
            ret, frame = cap.read()
            
            if ret and frame is not None and frame.size > 0:
                actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"  ✅ {width}x{height} -> actual: {actual_width}x{actual_height}")
                working_resolutions.append((actual_width, actual_height))
            else:
                print(f"  ❌ {width}x{height} - Failed")
                
            cap.release()
            
        except Exception as e:
            print(f"  ❌ {width}x{height} - Error: {e}")
    
    return working_resolutions


def safe_camera_capture(backend_id=cv2.CAP_V4L2, width=320, height=240):
    """안전한 카메라 캡처 (에러 처리 포함)"""
    print(f"\n📷 Starting safe camera capture...")
    print(f"Backend: {backend_id}, Resolution: {width}x{height}")
    
    cap = None
    try:
        # 카메라 초기화
        cap = cv2.VideoCapture(0, backend_id)
        if not cap.isOpened():
            print("❌ Failed to open camera")
            return False
        
        # 해상도 설정
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # 카메라 버퍼 크기 줄이기 (메모리 절약)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # FPS 제한 (메모리 절약)
        cap.set(cv2.CAP_PROP_FPS, 15)
        
        print("⏳ Waiting for camera to initialize...")
        time.sleep(2)  # 카메라 초기화 대기
        
        frame_count = 0
        print("\n🎥 Camera test started. Press 'q' to quit, 's' to save frame")
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                print(f"\r❌ Failed to read frame {frame_count}", end="", flush=True)
                time.sleep(0.1)
                continue
                
            if frame is None or frame.size == 0:
                print(f"\r⚠️ Empty frame {frame_count}", end="", flush=True)
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            # 프레임 정보 표시
            h, w = frame.shape[:2]
            print(f"\r✅ Frame {frame_count}: {w}x{h} pixels", end="", flush=True)
            
            # 프레임 저장용 키 체크 (X11 없이)
            # 실제 라즈베리파이에서는 키 입력을 다르게 처리해야 할 수 있음
            try:
                # cv2.imshow 대신 파일로 저장
                if frame_count == 1:
                    cv2.imwrite('test_frame.jpg', frame)
                    print(f"\n📁 First frame saved as 'test_frame.jpg'")
                
                if frame_count >= 30:  # 30프레임 후 종료
                    print(f"\n✅ Test completed successfully! {frame_count} frames captured")
                    break
                    
            except Exception as e:
                print(f"\n⚠️ Display error: {e}")
                # X11 디스플레이 없어도 계속 진행
                
            time.sleep(0.1)  # CPU 사용량 제한
        
        return True
        
    except Exception as e:
        print(f"\n❌ Camera capture error: {e}")
        return False
        
    finally:
        if cap:
            cap.release()
        cv2.destroyAllWindows()


def check_system_info():
    """시스템 정보 확인"""
    print("🖥️ System Information:")
    
    try:
        import platform
        print(f"  OS: {platform.system()} {platform.release()}")
        print(f"  Python: {sys.version}")
        print(f"  OpenCV: {cv2.__version__}")
    except:
        pass
    
    # 카메라 디바이스 확인
    import os
    print("\n📹 Camera devices:")
    
    video_devices = []
    for i in range(5):
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            video_devices.append(device_path)
    
    if video_devices:
        print(f"  Found: {video_devices}")
    else:
        print("  No /dev/video* devices found")
    
    # 메모리 정보
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if 'MemAvailable' in line:
                    mem_kb = int(line.split()[1])
                    mem_mb = mem_kb // 1024
                    print(f"  Available Memory: {mem_mb} MB")
                    break
    except:
        pass


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("🔬 Raspberry Pi Camera Diagnostic Tool")
    print("=" * 60)
    
    # 시스템 정보 확인
    check_system_info()
    
    # 백엔드 테스트
    working_backends = test_camera_backends()
    
    if not working_backends:
        print("\n❌ No working camera backends found!")
        print("\n💡 Troubleshooting tips:")
        print("  1. Check camera connection")
        print("  2. Enable camera: sudo raspi-config")
        print("  3. Increase GPU memory: sudo raspi-config -> Advanced -> Memory Split -> 128")
        print("  4. Load camera module: sudo modprobe bcm2835-v4l2")
        print("  5. Check permissions: sudo usermod -a -G video $USER")
        print("  6. Reboot system")
        return
    
    # 첫 번째 작동하는 백엔드로 해상도 테스트
    best_backend = working_backends[0][0]
    working_resolutions = test_camera_resolutions(best_backend)
    
    if working_resolutions:
        # 가장 작은 해상도로 안전한 캡처 테스트
        test_width, test_height = working_resolutions[0]
        safe_camera_capture(best_backend, test_width, test_height)
    else:
        print("\n❌ No working resolutions found!")


if __name__ == "__main__":
    main()
