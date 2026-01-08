import os
import struct

def get_file_version(file_path):
    """获取Windows PE文件的版本信息"""
    try:
        # 使用 Windows API 获取文件版本
        import win32api
        info = win32api.GetFileVersionInfo(file_path, "\\")
        ms = info['FileVersionMS']
        ls = info['FileVersionLS']
        version = [
            win32api.HIWORD(ms),
            win32api.LOWORD(ms),
            win32api.HIWORD(ls),
            win32api.LOWORD(ls)
        ]
        return version
    except ImportError:
        print("需要安装 pywin32: pip install pywin32")
        return None
    except Exception as e:
        print(f"获取版本失败: {e}")
        return None

# 检查文件路径
wework_path = r"D:\WXWork\WXWork.exe"
print(f"检查路径: {wework_path}")
print(f"文件存在: {os.path.exists(wework_path)}")
print()

if os.path.exists(wework_path):
    # 获取文件版本
    version = get_file_version(wework_path)
    if version:
        print(f"实际版本: {version}")
        print(f"版本字符串: {'.'.join(map(str, version))}")
        print(f"期望版本: [4, 0, 8, 6027]")
        print(f"版本匹配: {version == [4, 0, 8, 6027]}")

    # 检查文件大小
    size = os.path.getsize(wework_path)
    print(f"\n文件大小: {size:,} 字节 ({size/1024/1024:.2f} MB)")
else:
    print("❌ 文件不存在，请检查路径！")
    print("\n可能的路径：")
    print("  1. D:\\WXWork\\WXWork.exe")
    print("  2. D:\\WXWork\\WeCom.exe")
    print("  3. D:\\WXWork\\4.0.8.6027\\WXWork.exe")

# 检查D盘WXWork目录结构
print("\n=== D:\\WXWork 目录结构 ===")
wxwork_dir = r"D:\WXWork"
if os.path.exists(wxwork_dir):
    for root, dirs, files in os.walk(wxwork_dir):
        level = root.replace(wxwork_dir, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            if file.endswith('.exe'):
                print(f'{subindent}{file}')
        if level > 2:  # 只显示3层
            break
else:
    print("D:\\WXWork 目录不存在")
