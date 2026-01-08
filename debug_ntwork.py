import os
os.environ['ntwork_LOG'] = "ERROR"

print("=== ntwork 详细诊断 ===\n")

# 1. 设置路径
from ntwork import conf
print("1. 默认配置:")
print(f"   DEFAULT_WEWORK_EXE_PATH: {conf.DEFAULT_WEWORK_EXE_PATH}")
print(f"   DEFAULT_WEWORK_VERSION: {conf.DEFAULT_WEWORK_VERSION}")

# 2. 修改配置
conf.DEFAULT_WEWORK_EXE_PATH = r"D:\WXWork\WXWork.exe"
conf.DEFAULT_WEWORK_VERSION = [4, 0, 8, 6027]

print("\n2. 修改后配置:")
print(f"   DEFAULT_WEWORK_EXE_PATH: {conf.DEFAULT_WEWORK_EXE_PATH}")
print(f"   DEFAULT_WEWORK_VERSION: {conf.DEFAULT_WEWORK_VERSION}")

# 3. 检查文件
print(f"\n3. 文件检查:")
print(f"   文件存在: {os.path.exists(conf.DEFAULT_WEWORK_EXE_PATH)}")

# 4. 尝试创建 WeWork 实例
print("\n4. 尝试创建 WeWork 实例...")
try:
    import ntwork
    print("   导入 ntwork 成功")

    # 检查 WeWorkMgr
    from ntwork.core.mgr import WeWorkMgr
    print("   导入 WeWorkMgr 成功")

    # 尝试手动设置路径
    try:
        mgr = WeWorkMgr()
        print(f"   WeWorkMgr 创建成功")
        print(f"   WeWorkMgr._wework_exe_path: {mgr._wework_exe_path if hasattr(mgr, '_wework_exe_path') else 'N/A'}")
        print(f"   WeWorkMgr._wework_version: {mgr._wework_version if hasattr(mgr, '_wework_version') else 'N/A'}")
    except Exception as e:
        print(f"   WeWorkMgr 创建失败: {e}")
        import traceback
        traceback.print_exc()

    # 尝试创建 WeWork
    print("\n5. 创建 WeWork 对象...")
    wework = ntwork.WeWork()
    print("   ✓ WeWork 创建成功！")

except ntwork.exception.WeWorkVersionNotMatchError as e:
    print(f"   ✗ 版本不匹配错误")
    print(f"\n详细错误信息:")
    import traceback
    traceback.print_exc()

    # 尝试读取 ntwork 内部的版本检查逻辑
    print("\n6. 分析 ntwork 源码...")
    try:
        import inspect
        from ntwork.core.mgr import WeWorkMgr
        source = inspect.getsource(WeWorkMgr.set_wework_exe_path)
        print("   set_wework_exe_path 方法源码:")
        print("-" * 60)
        print(source)
        print("-" * 60)
    except Exception as e2:
        print(f"   无法读取源码: {e2}")

except Exception as e:
    print(f"   ✗ 其他错误: {e}")
    import traceback
    traceback.print_exc()
