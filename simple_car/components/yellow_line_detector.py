#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
노란색 라인 감지 및 방향 판단 모듈
- HSV 기반 노란색 영역 감지
- 히스토그램 분석을 통한 방향 결정
- 좌/우/직진 판단 로직
"""

import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional


class YellowLineDetector:
    """노란색 라인 감지 및 방향 판단 클래스"""

    def __init__(self):
        # 노란색 HSV 범위 설정
        self.yellow_hsv_lower = np.array([20, 100, 100])   # 노란색 하한값
        self.yellow_hsv_upper = np.array([30, 255, 255])   # 노란색 상한값
        
        # 방향 판단 임계값
        self.direction_threshold = 50000  # 좌우 판단 기준값
        
        # 히스토그램 분석 설정
        self.left_ratio = 1/5      # 왼쪽 영역 비율 (0~20%)
        self.right_ratio = 4/5     # 오른쪽 영역 시작 비율 (80~100%)
        
        # 디버그 모드
        self.debug_mode = False
        self.show_debug_windows = False

    def detect_yellow_regions(self, frame: np.ndarray) -> np.ndarray:
        """노란색 영역 감지"""
        try:
            if frame is None or frame.size == 0:
                return np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8) if frame is not None else np.zeros((50, 320), dtype=np.uint8)
            
            # BGR에서 HSV로 변환
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            # 노란색 마스크 생성
            yellow_mask = cv2.inRange(hsv, self.yellow_hsv_lower, self.yellow_hsv_upper)
            
            # 노이즈 제거 (모폴로지 연산)
            kernel = np.ones((3, 3), np.uint8)
            yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)
            yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel)
            
            if self.show_debug_windows:
                cv2.imshow('HSV', hsv)
                cv2.imshow('Yellow Mask', yellow_mask)
            
            return yellow_mask
            
        except Exception as e:
            print(f"❌ Yellow detection error: {e}")
            return np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8) if frame is not None else np.zeros((50, 320), dtype=np.uint8)

    def analyze_histogram(self, binary_frame: np.ndarray) -> Dict[str, Any]:
        """히스토그램 분석을 통한 좌우 분포 계산"""
        try:
            if binary_frame is None or binary_frame.size == 0:
                return {
                    "histogram": np.zeros(320),
                    "left_sum": 0,
                    "right_sum": 0,
                    "total_sum": 0,
                    "left_ratio": 0.0,
                    "right_ratio": 0.0
                }
            
            # 수직 히스토그램 계산 (각 열의 흰색 픽셀 합)
            histogram = np.sum(binary_frame, axis=0)
            
            # 히스토그램 길이
            hist_length = len(histogram)
            
            if hist_length == 0:
                return {
                    "histogram": np.zeros(320),
                    "left_sum": 0,
                    "right_sum": 0,
                    "total_sum": 0,
                    "left_ratio": 0.0,
                    "right_ratio": 0.0
                }
            
            # 좌측과 우측 영역 분할
            left_end = int(hist_length * self.left_ratio)
            right_start = int(hist_length * self.right_ratio)
            
            # 각 영역의 합계 계산
            left_sum = int(np.sum(histogram[:left_end]))
            right_sum = int(np.sum(histogram[right_start:]))
            total_sum = int(np.sum(histogram))
            
            # 비율 계산 (0으로 나누기 방지)
            left_ratio = left_sum / total_sum if total_sum > 0 else 0.0
            right_ratio = right_sum / total_sum if total_sum > 0 else 0.0
            
            return {
                "histogram": histogram,
                "left_sum": left_sum,
                "right_sum": right_sum,
                "total_sum": total_sum,
                "left_ratio": left_ratio,
                "right_ratio": right_ratio,
                "left_end": left_end,
                "right_start": right_start
            }
            
        except Exception as e:
            print(f"❌ Histogram analysis error: {e}")
            return {
                "histogram": np.zeros(320),
                "left_sum": 0,
                "right_sum": 0,
                "total_sum": 0,
                "left_ratio": 0.0,
                "right_ratio": 0.0
            }

    def decide_direction(self, histogram_data: Dict[str, Any]) -> str:
        """히스토그램 데이터를 기반으로 방향 결정"""
        try:
            left_sum = histogram_data.get("left_sum", 0)
            right_sum = histogram_data.get("right_sum", 0)
            total_sum = histogram_data.get("total_sum", 0)
            
            # 디버그 출력
            if self.debug_mode:
                print(f"  Left: {left_sum}, Right: {right_sum}, Total: {total_sum}")
                print(f"  Difference: {abs(right_sum - left_sum)}")
            
            # 총합이 너무 작으면 직진 (라인이 거의 없음)
            if total_sum < 1000:
                return "UP"
            
            # 좌우 차이가 임계값보다 크면 방향 결정
            difference = abs(right_sum - left_sum)
            
            if difference > self.direction_threshold:
                if right_sum > left_sum:
                    return "LEFT"  # 오른쪽에 더 많은 라인 → 왼쪽으로 이동
                else:
                    return "RIGHT"  # 왼쪽에 더 많은 라인 → 오른쪽으로 이동
            else:
                return "UP"  # 좌우 균형 → 직진
                
        except Exception as e:
            print(f"❌ Direction decision error: {e}")
            return "UP"

    def process_frame_for_direction(self, frame: np.ndarray) -> Dict[str, Any]:
        """프레임을 처리하여 방향 결정까지 수행"""
        try:
            # 1. 노란색 영역 감지
            yellow_mask = self.detect_yellow_regions(frame)
            
            # 2. 히스토그램 분석
            histogram_data = self.analyze_histogram(yellow_mask)
            
            # 3. 방향 결정
            direction = self.decide_direction(histogram_data)
            
            # 결과 종합
            result = {
                "direction": direction,
                "yellow_mask": yellow_mask,
                "histogram_data": histogram_data,
                "frame_shape": frame.shape if frame is not None else (0, 0, 0)
            }
            
            if self.debug_mode:
                print(f"🎯 Decided direction: {direction}")
            
            return result
            
        except Exception as e:
            print(f"❌ Frame processing error: {e}")
            return {
                "direction": "UP",
                "yellow_mask": np.zeros((50, 320), dtype=np.uint8),
                "histogram_data": self.analyze_histogram(None),
                "frame_shape": (0, 0, 0)
            }

    def visualize_detection(self, frame: np.ndarray, 
                          yellow_mask: np.ndarray, 
                          histogram_data: Dict[str, Any], 
                          direction: str) -> None:
        """감지 결과 시각화 (디버그용)"""
        if not self.show_debug_windows:
            return
            
        try:
            if frame is None or yellow_mask is None:
                return
            
            # 원본 프레임에 노란색 영역 오버레이
            colored_mask = cv2.cvtColor(yellow_mask, cv2.COLOR_GRAY2BGR)
            overlay = cv2.addWeighted(frame, 0.7, colored_mask, 0.3, 0)
            
            # 히스토그램 시각화
            histogram = histogram_data.get("histogram", np.zeros(320))
            hist_img = np.zeros((200, len(histogram), 3), dtype=np.uint8)
            
            if len(histogram) > 0:
                max_val = np.max(histogram) if np.max(histogram) > 0 else 1
                for i, val in enumerate(histogram):
                    height = int((val / max_val) * 180)
                    cv2.line(hist_img, (i, 200), (i, 200 - height), (255, 255, 255), 1)
                
                # 좌/우 영역 표시
                left_end = histogram_data.get("left_end", 0)
                right_start = histogram_data.get("right_start", len(histogram))
                
                cv2.line(hist_img, (left_end, 0), (left_end, 200), (0, 255, 0), 2)
                cv2.line(hist_img, (right_start, 0), (right_start, 200), (0, 0, 255), 2)
            
            # 방향 정보 표시
            cv2.putText(overlay, f"Direction: {direction}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            
            left_sum = histogram_data.get("left_sum", 0)
            right_sum = histogram_data.get("right_sum", 0)
            cv2.putText(overlay, f"L:{left_sum} R:{right_sum}", (10, 60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # 윈도우 표시
            cv2.imshow('Yellow Detection', overlay)
            cv2.imshow('Histogram', hist_img)
            
        except Exception as e:
            print(f"❌ Visualization error: {e}")

    def set_detection_parameters(self, **kwargs) -> None:
        """감지 파라미터 설정"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                if self.debug_mode:
                    print(f"✓ {key} = {value}")

    def get_detection_info(self) -> Dict[str, Any]:
        """현재 감지 설정 정보 반환"""
        return {
            "yellow_hsv_lower": self.yellow_hsv_lower.tolist(),
            "yellow_hsv_upper": self.yellow_hsv_upper.tolist(),
            "direction_threshold": self.direction_threshold,
            "left_ratio": self.left_ratio,
            "right_ratio": self.right_ratio,
            "debug_mode": self.debug_mode,
            "show_debug_windows": self.show_debug_windows
        }

    def cleanup(self) -> None:
        """리소스 정리"""
        try:
            if self.show_debug_windows:
                cv2.destroyAllWindows()
        except:
            pass
