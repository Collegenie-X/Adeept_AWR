#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Adeept AWR 자율주행 로봇 설치 스크립트
- 라즈베리파이 시스템 업데이트
- 필요한 라이브러리 자동 설치
- GPIO, I2C, SPI 인터페이스 활성화
- 권한 설정 및 환경 구성

사용법: sudo python3 setup.py
"""

import os
import sys
import time
import subprocess
import platform


def print_banner():
    """설치 시작 배너 출력"""
    print("=" * 60)
    print("🤖 Adeept AWR 자율주행 로봇 설치 스크립트")
    print("=" * 60)
    print("이 스크립트는 다음 작업을 수행합니다:")
    print("✓ 시스템 업데이트")
    print("✓ 필요한 라이브러리 설치")
    print("✓ 인터페이스 활성화 (I2C, SPI)")
    print("✓ 권한 설정")
    print("✓ 환경 구성")
    print("=" * 60)
    print()


def check_root():
    """루트 권한 확인"""
    if os.geteuid() != 0:
        print("❌ 이 스크립트는 root 권한이 필요합니다.")
        print("다음 명령어로 실행하세요: sudo python3 setup.py")
        sys.exit(1)
    print("✓ 루트 권한 확인됨")


def check_raspberry_pi():
    """라즈베리파이 확인"""
    try:
        with open("/proc/cpuinfo", "r") as f:
            cpuinfo = f.read()
        if "BCM" in cpuinfo and "ARM" in platform.machine():
            print("✓ 라즈베리파이 환경 확인됨")
            return True
        else:
            print("⚠️  라즈베리파이가 아닌 환경에서 실행 중입니다.")
            response = input("계속 진행하시겠습니까? (y/N): ")
            return response.lower() == "y"
    except:
        print("⚠️  시스템 정보를 확인할 수 없습니다.")
        return True


def run_command(command, description, retry_count=3):
    """
    명령어 실행 (재시도 기능 포함)
    :param command: 실행할 명령어
    :param description: 명령어 설명
    :param retry_count: 재시도 횟수
    :return: 성공 여부
    """
    print(f"🔄 {description}...")

    for attempt in range(1, retry_count + 1):
        try:
            result = subprocess.run(
                command, shell=True, check=True, capture_output=True, text=True
            )
            print(f"✓ {description} 완료")
            return True
        except subprocess.CalledProcessError as e:
            if attempt < retry_count:
                print(f"⚠️  시도 {attempt}/{retry_count} 실패, 재시도 중...")
                time.sleep(2)
            else:
                print(f"❌ {description} 실패: {e}")
                print(f"   명령어: {command}")
                if e.stdout:
                    print(f"   출력: {e.stdout}")
                if e.stderr:
                    print(f"   오류: {e.stderr}")
                return False
    return False


def update_system():
    """시스템 업데이트"""
    print("\n📦 시스템 업데이트 중...")

    # 불필요한 패키지 제거 (공간 확보)
    run_command("apt-get purge -y wolfram-engine", "Wolfram Engine 제거")
    run_command("apt-get purge -y libreoffice*", "LibreOffice 제거")
    run_command("apt-get -y clean", "패키지 캐시 정리")
    run_command("apt-get -y autoremove", "불필요한 패키지 제거")

    # 시스템 업데이트
    if not run_command("apt-get update", "패키지 목록 업데이트"):
        print("❌ 패키지 목록 업데이트 실패")
        return False

    if not run_command("apt-get -y upgrade", "시스템 업그레이드"):
        print("❌ 시스템 업그레이드 실패")
        return False

    return True


def install_system_packages():
    """시스템 패키지 설치"""
    print("\n📚 시스템 패키지 설치 중...")

    packages = [
        ("python3-pip", "Python3 패키지 관리자"),
        ("python3-dev", "Python3 개발 헤더"),
        ("python3-rpi.gpio", "GPIO 제어 라이브러리"),
        ("i2c-tools", "I2C 도구"),
        ("git", "Git 버전 관리"),
        ("build-essential", "빌드 도구"),
        ("cmake", "CMake 빌드 시스템"),
        ("libjpeg-dev", "JPEG 라이브러리"),
        ("zlib1g-dev", "압축 라이브러리"),
    ]

    for package, description in packages:
        if not run_command(f"apt-get install -y {package}", f"{description} 설치"):
            print(f"⚠️  {package} 설치 실패, 계속 진행...")

    return True


def install_python_packages():
    """Python 패키지 설치"""
    print("\n🐍 Python 패키지 설치 중...")

    # pip 업그레이드
    run_command("python3 -m pip install --upgrade pip", "pip 업그레이드")

    packages = [
        ("RPi.GPIO>=0.7.0", "GPIO 제어"),
        ("rpi_ws281x>=4.3.0", "WS2812 LED 제어"),
        ("adafruit-pca9685>=1.0.1", "PCA9685 서보모터 제어"),
        ("adafruit-circuitpython-pca9685>=3.4.0", "CircuitPython PCA9685"),
        ("numpy>=1.21.0", "수치 계산"),
        ("opencv-python>=4.5.0", "영상 처리 (선택적)"),
        ("pygame>=2.0.0", "게임/GUI (선택적)"),
        ("PyYAML>=6.0", "설정 파일 처리"),
        ("typing_extensions>=3.10.0", "타입 힌트"),
    ]

    for package, description in packages:
        if not run_command(f"pip3 install {package}", f"{description} 설치"):
            print(f"⚠️  {package} 설치 실패, 계속 진행...")

    return True


def enable_interfaces():
    """라즈베리파이 인터페이스 활성화"""
    print("\n🔧 인터페이스 활성화 중...")

    config_file = "/boot/config.txt"
    if not os.path.exists(config_file):
        config_file = "/boot/firmware/config.txt"  # 새로운 위치

    if not os.path.exists(config_file):
        print("⚠️  config.txt 파일을 찾을 수 없습니다.")
        return False

    # 백업 생성
    backup_file = f"{config_file}.backup.{int(time.time())}"
    run_command(f"cp {config_file} {backup_file}", "config.txt 백업")

    # 필요한 설정들
    settings = [
        ("dtparam=i2c_arm=on", "I2C 활성화"),
        ("dtparam=spi=on", "SPI 활성화"),
        ("enable_uart=1", "UART 활성화"),
        ("dtparam=audio=on", "오디오 활성화"),
        ("gpu_mem=64", "GPU 메모리 설정"),
    ]

    try:
        with open(config_file, "r") as f:
            config_content = f.read()

        modified = False
        for setting, description in settings:
            if setting not in config_content:
                config_content += f"\n# {description}\n{setting}\n"
                modified = True
                print(f"✓ {description} 추가됨")
            else:
                print(f"✓ {description} 이미 설정됨")

        if modified:
            with open(config_file, "w") as f:
                f.write(config_content)
            print("✓ config.txt 업데이트 완료")

    except Exception as e:
        print(f"❌ config.txt 수정 실패: {e}")
        return False

    # 모듈 로드 설정
    modules_file = "/etc/modules"
    modules_to_add = ["i2c-dev", "spi-dev"]

    try:
        with open(modules_file, "r") as f:
            modules_content = f.read()

        modified = False
        for module in modules_to_add:
            if module not in modules_content:
                modules_content += f"{module}\n"
                modified = True
                print(f"✓ {module} 모듈 추가됨")
            else:
                print(f"✓ {module} 모듈 이미 설정됨")

        if modified:
            with open(modules_file, "w") as f:
                f.write(modules_content)
            print("✓ 모듈 설정 업데이트 완료")

    except Exception as e:
        print(f"❌ 모듈 설정 실패: {e}")
        return False

    return True


def setup_permissions():
    """권한 설정"""
    print("\n🔐 권한 설정 중...")

    # GPIO 그룹에 pi 사용자 추가
    run_command("usermod -a -G gpio pi", "GPIO 그룹에 pi 사용자 추가")
    run_command("usermod -a -G i2c pi", "I2C 그룹에 pi 사용자 추가")
    run_command("usermod -a -G spi pi", "SPI 그룹에 pi 사용자 추가")

    # udev 규칙 설정 (LED 제어 권한)
    udev_rule = """# WS2812 LED 제어 권한
SUBSYSTEM=="mem", GROUP="gpio", MODE="0664"
KERNEL=="gpiomem", GROUP="gpio", MODE="0664"
"""

    try:
        with open("/etc/udev/rules.d/99-gpio.rules", "w") as f:
            f.write(udev_rule)
        print("✓ GPIO udev 규칙 설정 완료")
    except Exception as e:
        print(f"⚠️  udev 규칙 설정 실패: {e}")

    return True


def create_systemd_service():
    """시스템 서비스 생성 (선택적)"""
    print("\n⚙️  시스템 서비스 설정 중...")

    service_content = """[Unit]
Description=Adeept AWR Autonomous Robot
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Adeept_AWR
ExecStart=/usr/bin/python3 /home/pi/Adeept_AWR/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    try:
        with open("/etc/systemd/system/adeept-awr.service", "w") as f:
            f.write(service_content)

        run_command("systemctl daemon-reload", "systemd 데몬 재로드")
        print("✓ systemd 서비스 생성 완료")
        print("  서비스 시작: sudo systemctl start adeept-awr")
        print("  자동 시작: sudo systemctl enable adeept-awr")

    except Exception as e:
        print(f"⚠️  systemd 서비스 생성 실패: {e}")

    return True


def setup_project_files():
    """프로젝트 파일 설정"""
    print("\n📁 프로젝트 파일 설정 중...")

    # 실행 권한 설정
    script_files = [
        "main.py",
        "hardware/test_gear_motors.py",
        "hardware/test_line_sensors.py",
        "hardware/test_ultrasonic_sensor.py",
        "hardware/test_led_strip.py",
        "hardware/test_servo_motors.py",
    ]

    for script in script_files:
        if os.path.exists(script):
            run_command(f"chmod +x {script}", f"{script} 실행 권한 설정")
        else:
            print(f"⚠️  {script} 파일을 찾을 수 없습니다.")

    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        run_command(f"chown -R pi:pi {log_dir}", "로그 디렉토리 권한 설정")
        print(f"✓ {log_dir} 디렉토리 생성 완료")

    return True


def test_installation():
    """설치 테스트"""
    print("\n🧪 설치 테스트 중...")

    tests = [
        ("python3 -c 'import RPi.GPIO; print(\"GPIO OK\")'", "GPIO 라이브러리 테스트"),
        (
            "python3 -c 'import rpi_ws281x; print(\"WS281X OK\")'",
            "LED 라이브러리 테스트",
        ),
        (
            "python3 -c 'import Adafruit_PCA9685; print(\"PCA9685 OK\")'",
            "서보모터 라이브러리 테스트",
        ),
        ("i2cdetect -y 1", "I2C 인터페이스 테스트"),
        ("ls /dev/gpiomem", "GPIO 메모리 접근 테스트"),
    ]

    success_count = 0
    for command, description in tests:
        if run_command(command, description):
            success_count += 1
        else:
            print(f"⚠️  {description} 실패")

    print(f"\n테스트 결과: {success_count}/{len(tests)} 성공")
    return success_count == len(tests)


def main():
    """메인 설치 함수"""
    print_banner()

    # 시스템 확인
    check_root()
    if not check_raspberry_pi():
        print("❌ 설치를 중단합니다.")
        sys.exit(1)

    print("\n🚀 설치를 시작합니다...")
    time.sleep(2)

    # 설치 단계별 실행
    steps = [
        (update_system, "시스템 업데이트"),
        (install_system_packages, "시스템 패키지 설치"),
        (install_python_packages, "Python 패키지 설치"),
        (enable_interfaces, "인터페이스 활성화"),
        (setup_permissions, "권한 설정"),
        (setup_project_files, "프로젝트 파일 설정"),
        (create_systemd_service, "시스템 서비스 설정"),
        (test_installation, "설치 테스트"),
    ]

    completed_steps = 0
    for step_func, step_name in steps:
        print(f"\n{'='*20} {step_name} {'='*20}")
        try:
            if step_func():
                completed_steps += 1
                print(f"✓ {step_name} 완료")
            else:
                print(f"⚠️  {step_name} 부분적 실패")
        except Exception as e:
            print(f"❌ {step_name} 오류: {e}")

    # 설치 완료 메시지
    print("\n" + "=" * 60)
    print("🎉 Adeept AWR 자율주행 로봇 설치 완료!")
    print("=" * 60)
    print(f"완료된 단계: {completed_steps}/{len(steps)}")

    if completed_steps >= len(steps) - 1:  # 마지막 테스트는 선택적
        print("\n✅ 설치가 성공적으로 완료되었습니다!")
        print("\n📖 사용 방법:")
        print("  python3 main.py                    # 메인 프로그램 실행")
        print("  python3 hardware/test_*.py         # 개별 하드웨어 테스트")
        print("  sudo python3 hardware/test_led_strip.py  # LED 테스트 (root 권한)")

        print("\n🔄 재부팅이 필요할 수 있습니다:")
        print("  sudo reboot")

        print("\n📚 자세한 정보:")
        print("  README.md        # 프로젝트 설명서")
        print("  pinout.md        # 핀아웃 정보")

    else:
        print("\n⚠️  일부 단계가 실패했습니다.")
        print("로그를 확인하고 수동으로 해결해 주세요.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ 설치가 사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        sys.exit(1)
