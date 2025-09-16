#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
라인 센서 서비스 모듈
- 하드웨어 컨트롤러(`hardware.test_line_sensors.LineSensorController`) 래핑
- 필요 시 `autonomous_robot/sensors/line_sensor_noise_filter.py` 활용 가능
"""

from typing import Optional, Dict, Any

try:
    from hardware.test_line_sensors import LineSensorController

    _HARDWARE = True
except Exception:
    LineSensorController = None  # type: ignore
    _HARDWARE = False


class LineSensorService:
    """라인 센서 서비스 클래스"""

    def __init__(self) -> None:
        self.controller: Optional[LineSensorController] = None
        if _HARDWARE:
            try:
                self.controller = LineSensorController()
            except Exception:
                self.controller = None

    def get_position_info(self) -> Dict[str, Any]:
        """하드웨어 형식의 표준화된 딕셔너리를 반환
        - 센서 미존재 시 기본값은 1(검정 바닥)로 설정하여 기존 로직과 호환
        """
        # Early return for simulation mode
        if self.controller is None:
            return {"position": None, "sensors": {"left": 1, "middle": 1, "right": 1}}
            
        try:
            info = self.controller.get_line_position()
            # Early return for valid dict
            if isinstance(info, dict):
                return info
        except Exception:
            pass
            
        # Fallback for any error case
        return {"position": None, "sensors": {"left": 1, "middle": 1, "right": 1}}

    def cleanup(self) -> None:
        try:
            if self.controller:
                self.controller.cleanup()
        except Exception:
            pass
