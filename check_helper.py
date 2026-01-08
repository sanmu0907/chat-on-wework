import os
from ntwork.utils.tools import get_helper_file

version = [4, 0, 8, 6027]

print("=== 查找 helper 文件 ===\n")
print(f"版本: {version}")

try:
    helper_file = get_helper_file(version)
    print(f"\nhelper 文件路径:")
    print(f"  {helper_file}")
    print(f"\n文件存在: {os.path.exists(helper_file)}")

    if not os.path.exists(helper_file):
        print("\n❌ helper 文件不存在！")

        # 查看 helper 文件所在目录
        helper_dir = os.path.dirname(helper_file)
        print(f"\nhelper 目录: {helper_dir}")
        print(f"目录存在: {os.path.exists(helper_dir)}")

        if os.path.exists(helper_dir):
            print("\n该目录下已有的文件:")
            for f in os.listdir(helper_dir):
                print(f"  - {f}")

        # 查看 ntwork 安装目录
        import ntwork
        ntwork_path = os.path.dirname(ntwork.__file__)
        print(f"\nntwork 安装路径: {ntwork_path}")

        # 查找所有可能的 helper 文件
        print("\n查找 ntwork 中所有的 .dll 文件:")
        for root, dirs, files in os.walk(ntwork_path):
            for file in files:
                if file.endswith('.dll') or 'helper' in file.lower():
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, ntwork_path)
                    print(f"  - {rel_path}")
    else:
        print("\n✓ helper 文件存在")

except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()

# 查看 get_helper_file 源码
print("\n" + "="*60)
print("get_helper_file 函数源码:")
print("="*60)
try:
    import inspect
    source = inspect.getsource(get_helper_file)
    print(source)
except Exception as e:
    print(f"无法读取源码: {e}")
