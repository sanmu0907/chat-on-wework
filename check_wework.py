# 检查企业微信安装情况
import os
import sys

print("=== 检查企业微信安装 ===\n")

# 常见的企业微信安装路径
possible_paths = [
    r"C:\Program Files (x86)\WXWork\WeCom.exe",
    r"C:\Program Files\WXWork\WeCom.exe",
    r"C:\Users\{}\AppData\Local\WXWork\WeCom.exe".format(os.getenv('USERNAME')),
]

print("1. 检查常见安装路径:")
found_paths = []
for path in possible_paths:
    if os.path.exists(path):
        print(f"   ✓ 找到: {path}")
        found_paths.append(path)
    else:
        print(f"   ✗ 未找到: {path}")

if not found_paths:
    print("\n⚠️  在常见路径下未找到企业微信，请手动查找 WeCom.exe 文件")
    print("   可以尝试在文件资源管理器中搜索 'WeCom.exe'")
else:
    print(f"\n✓ 找到 {len(found_paths)} 个企业微信安装")

print("\n2. 检查 ntwork 默认配置:")
try:
    import ntwork
    from ntwork import conf
    print(f"   默认路径: {conf.DEFAULT_WEWORK_EXE_PATH}")
    print(f"   期望版本: {conf.DEFAULT_WEWORK_VERSION}")
except Exception as e:
    print(f"   ✗ 读取失败: {e}")

print("\n=== 解决方案 ===")
print("请手动设置企业微信路径，在 app.py 启动前添加以下代码：")
print()
if found_paths:
    print(f'wework_path = r"{found_paths[0]}"')
else:
    print('wework_path = r"C:\\你的企业微信路径\\WeCom.exe"')
print('wework.set_wework_exe_path(wework_path, [4, 0, 8, 6027])')
print()
