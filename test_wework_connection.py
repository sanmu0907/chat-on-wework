"""
企业微信连接诊断脚本
"""
import os
os.environ['ntwork_LOG'] = "DEBUG"  # 改为DEBUG模式查看详细日志
import ntwork
from ntwork import conf

# 设置企业微信路径
conf.DEFAULT_WEWORK_EXE_PATH = r"F:\WXWork\WXWork.exe"
conf.DEFAULT_WEWORK_VERSION = "4.0.8.6027"

print("=" * 50)
print("企业微信连接诊断")
print("=" * 50)
print(f"企业微信路径: {conf.DEFAULT_WEWORK_EXE_PATH}")
print(f"企业微信版本: {conf.DEFAULT_WEWORK_VERSION}")
print(f"文件是否存在: {os.path.exists(conf.DEFAULT_WEWORK_EXE_PATH)}")
print("=" * 50)

print("\n正在创建ntwork实例...")
wework = ntwork.WeWork()

print("正在调用open()...")
wework.open(smart=True)

print("正在等待登录...")
login_info = wework.wait_login()

if login_info:
    print(f"\n✅ 登录成功!")
    print(f"User ID: {login_info.get('user_id')}")
    print(f"昵称: {login_info.get('nickname')}")
    print(f"用户名: {login_info.get('username')}")
else:
    print("\n❌ 登录失败或超时")

ntwork.exit_()
