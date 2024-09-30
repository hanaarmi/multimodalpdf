# lib/logging_config.py

import datetime
import logging
import sys


def setup_logging(path="./log", level=logging.INFO):
    # 루트 로거 가져오기
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 기존의 모든 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 파일 핸들러 설정
    file_handler = logging.FileHandler(
        f'{path}/app_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
        mode='a'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(name)-12s: %(levelname)-8s %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    return root_logger
