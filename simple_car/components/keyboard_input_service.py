#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
키보드 입력 서비스 모듈
- 터미널 의존 키 입력(화살표/문자/스페이스/Ctrl+C) 처리
- 메뉴 출력 유틸 제공 (상위에서 문자열만 받아 출력하도록 단순화)
"""

import sys
import select
import termios
import tty
from typing import Optional


class KeyboardInputService:
    """키보드 입력 처리 서비스 클래스"""

    def __init__(self) -> None:
        self._old_settings = None

    def read_single_key(self, timeout_seconds: float = 0.02) -> Optional[str]:
        """Enter 없이 단일 키를 읽어 반환. 없으면 None"""
        try:
            self._old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())
                if select.select([sys.stdin], [], [], timeout_seconds) == (
                    [sys.stdin],
                    [],
                    [],
                ):
                    char = sys.stdin.read(1)

                    if char == " ":
                        return "space"

                    if char == "\x1b":
                        second = None
                        if select.select([sys.stdin], [], [], timeout_seconds)[0]:
                            second = sys.stdin.read(1)
                        if not second:
                            return "esc"
                        if second in ("[", "O"):
                            if select.select([sys.stdin], [], [], timeout_seconds)[0]:
                                third = sys.stdin.read(1)
                            else:
                                return "esc"
                            if third == "A":
                                return "up"
                            if third == "B":
                                return "down"
                            if third == "C":
                                return "right"
                            if third == "D":
                                return "left"
                            return "esc"
                        return "esc"

                    # 기본 문자
                    return char.lower()
                return None
            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)
        except Exception:
            return None

    def read_line(self) -> Optional[str]:
        """Enter가 필요한 라인 입력 읽기"""
        try:
            return input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None
