#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
카메라 비전 서비스 모듈
- 카메라 초기화 및 프레임 캡처
- 이미지 전처리 및 변환
- ROI(Region of Interest) 설정
"""

import cv2
import numpy as np
import time
from typing import Optional, Tuple, Dict, Any


class CameraVisionService:
    """카메라 비전 제어 서비스"""

    def __init__(self, camera_id: int = 0, width: int = 320, height: int = 240):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_initialized = False
        
        # 카메라 속성 기본값
        self.brightness = 65
        self.contrast = 80
        self.saturation = 20
        self.gain = 20
        
        # ROI 설정 (상위 영역 사용)
        self.roi_y_offset = 10  # Y 값 (상위에서 얼마나 아래로)
        self.roi_height = 50    # ROI 높이

    def initialize_camera(self) -> bool:
        """카메라 초기화"""
        try:
            print(f"🎥 Initializing camera... (ID: {self.camera_id})")
            
            self.cap = cv2.VideoCapture(self.camera_id)
            if not self.cap.isOpened():
                print("❌ Failed to open camera")
                return False
            
            # 해상도 설정
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # 카메라 속성 설정
            self._apply_camera_settings()
            
            # 초기 프레임 확인
            ret, frame = self.cap.read()
            if not ret:
                print("❌ Failed to read frame from camera")
                return False
                
            print(f"✅ Camera initialized successfully ({self.width}x{self.height})")
            self.is_initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Camera initialization error: {e}")
            return False

    def _apply_camera_settings(self) -> None:
        """카메라 속성 설정 적용"""
        if not self.cap:
            return
            
        try:
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
            self.cap.set(cv2.CAP_PROP_CONTRAST, self.contrast)
            self.cap.set(cv2.CAP_PROP_SATURATION, self.saturation)
            self.cap.set(cv2.CAP_PROP_GAIN, self.gain)
        except Exception as e:
            print(f"⚠️ Camera settings apply error: {e}")

    def capture_frame(self) -> Optional[np.ndarray]:
        """프레임 캡처"""
        if not self.is_initialized or not self.cap:
            return None
            
        try:
            ret, frame = self.cap.read()
            if not ret:
                print("⚠️ Frame capture failed")
                return None
            return frame
        except Exception as e:
            print(f"❌ Frame capture error: {e}")
            return None

    def extract_roi(self, frame: np.ndarray) -> np.ndarray:
        """ROI(관심 영역) 추출 - 상위 영역 사용"""
        if frame is None:
            return np.zeros((self.roi_height, self.width, 3), dtype=np.uint8)
        
        try:
            # 상위 영역 추출
            roi_start_y = self.roi_y_offset
            roi_end_y = self.roi_y_offset + self.roi_height
            
            # 경계 확인
            roi_end_y = min(roi_end_y, frame.shape[0])
            
            roi_frame = frame[roi_start_y:roi_end_y, :]
            return roi_frame
            
        except Exception as e:
            print(f"❌ ROI extraction error: {e}")
            return np.zeros((self.roi_height, self.width, 3), dtype=np.uint8)

    def apply_perspective_transform(self, frame: np.ndarray) -> np.ndarray:
        """퍼스펙티브 변환 적용 (원근 보정)"""
        try:
            # 변환할 포인트 설정 (자동 조정)
            height, width = frame.shape[:2]
            
            # 소스 포인트 (사다리꼴 형태)
            pts_src = np.float32([
                [10, height - 10],          # 좌하
                [width - 10, height - 10],  # 우하
                [width - 10, 10],           # 우상
                [10, 10]                    # 좌상
            ])
            
            # 목표 포인트 (직사각형)
            pts_dst = np.float32([
                [0, height],        # 좌하
                [width, height],    # 우하
                [width, 0],         # 우상
                [0, 0]              # 좌상
            ])
            
            # 변환 행렬 계산
            mat_transform = cv2.getPerspectiveTransform(pts_src, pts_dst)
            
            # 변환 적용
            transformed = cv2.warpPerspective(frame, mat_transform, (width, height))
            return transformed
            
        except Exception as e:
            print(f"❌ Perspective transform error: {e}")
            return frame

    def convert_to_weighted_gray(self, frame: np.ndarray, 
                                r_weight: float = 0.33, 
                                g_weight: float = 0.33, 
                                b_weight: float = 0.33) -> np.ndarray:
        """가중치를 적용한 그레이스케일 변환"""
        try:
            if frame is None or frame.size == 0:
                return np.zeros((self.roi_height, self.width), dtype=np.uint8)
            
            # BGR 순서 (OpenCV)
            b_channel = frame[:, :, 0].astype(np.float32)
            g_channel = frame[:, :, 1].astype(np.float32)
            r_channel = frame[:, :, 2].astype(np.float32)
            
            # 가중치 적용
            weighted = (r_channel * r_weight + 
                       g_channel * g_weight + 
                       b_channel * b_weight)
            
            # 0-255 범위로 클리핑
            weighted = np.clip(weighted, 0, 255).astype(np.uint8)
            return weighted
            
        except Exception as e:
            print(f"❌ Grayscale conversion error: {e}")
            return np.zeros((self.roi_height, self.width), dtype=np.uint8)

    def apply_binary_threshold(self, gray_frame: np.ndarray, 
                              threshold: int = 15) -> np.ndarray:
        """이진화 임계값 적용"""
        try:
            _, binary = cv2.threshold(gray_frame, threshold, 255, cv2.THRESH_BINARY)
            return binary
        except Exception as e:
            print(f"❌ Binary threshold error: {e}")
            return np.zeros_like(gray_frame)

    def get_camera_info(self) -> Dict[str, Any]:
        """현재 카메라 정보 반환"""
        return {
            "camera_id": self.camera_id,
            "width": self.width,
            "height": self.height,
            "is_initialized": self.is_initialized,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "saturation": self.saturation,
            "gain": self.gain,
            "roi_y_offset": self.roi_y_offset,
            "roi_height": self.roi_height
        }

    def update_camera_settings(self, **kwargs) -> None:
        """카메라 설정 업데이트"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        if self.is_initialized:
            self._apply_camera_settings()

    def cleanup(self) -> None:
        """카메라 리소스 정리"""
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
                print("✅ Camera resources cleaned up successfully")
            
            cv2.destroyAllWindows()
            self.is_initialized = False
            
        except Exception as e:
            print(f"⚠️ Camera cleanup error: {e}")

    def __del__(self):
        """소멸자 - 자동 정리"""
        self.cleanup()
