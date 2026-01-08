import os
import time
os.environ['ntwork_LOG'] = "ERROR"
import ntwork
from ntwork import conf

# 设置企业微信路径为F盘的指定版本
conf.DEFAULT_WEWORK_EXE_PATH = r"E:\WXWork\WXWork.exe"
conf.DEFAULT_WEWORK_VERSION = "4.0.8.6027"

wework = ntwork.WeWork()


def forever():
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        ntwork.exit_()
        os._exit(0)


