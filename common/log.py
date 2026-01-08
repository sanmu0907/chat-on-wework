import logging
import sys
import io


def _reset_logger(log):
    for handler in log.handlers:
        handler.close()
        log.removeHandler(handler)
        del handler
    log.handlers.clear()
    log.propagate = False

    # 文件日志（始终添加，使用 UTF-8 编码）
    file_handle = logging.FileHandler("run.log", encoding="utf-8")
    file_handle.setFormatter(
        logging.Formatter(
            "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    log.addHandler(file_handle)

    # 控制台日志（仅在 stdout 可用时添加，pythonw.exe 下 stdout 为 None）
    if sys.stdout is not None:
        # 使用 UTF-8 编码包装 stdout，避免 Windows GBK 编码问题（emoji 等）
        # errors='replace' 会将无法编码的字符替换为 '?'，避免崩溃
        try:
            # 尝试重新配置 stdout 为 UTF-8
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
                stream = sys.stdout
            else:
                # Python 3.6 及更早版本，使用 TextIOWrapper
                stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

            console_handle = logging.StreamHandler(stream)
            console_handle.setFormatter(
                logging.Formatter(
                    "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            log.addHandler(console_handle)
        except Exception as e:
            # 如果控制台配置失败，仅使用文件日志（不抛出异常）
            pass


def _get_logger():
    log = logging.getLogger("log")
    _reset_logger(log)
    log.setLevel(logging.INFO)
    return log


# 日志句柄
logger = _get_logger()
