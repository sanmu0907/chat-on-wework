import os
import ntwork

print("=== ntwork 模块结构探索 ===\n")

# 1. 查看 ntwork 安装路径
ntwork_path = os.path.dirname(ntwork.__file__)
print(f"ntwork 安装路径: {ntwork_path}\n")

# 2. 列出所有模块
print("ntwork 包含的模块和文件:")
for root, dirs, files in os.walk(ntwork_path):
    level = root.replace(ntwork_path, '').count(os.sep)
    indent = '  ' * level
    rel_path = os.path.relpath(root, ntwork_path)
    if rel_path == '.':
        print(f"{indent}ntwork/")
    else:
        print(f"{indent}{os.path.basename(root)}/")

    sub_indent = '  ' * (level + 1)
    for file in files:
        if file.endswith(('.py', '.dll', '.pyd')):
            print(f"{sub_indent}{file}")

# 3. 查看 ntwork 暴露的所有属性
print("\n" + "="*60)
print("ntwork 模块属性:")
print("="*60)
for attr in dir(ntwork):
    if not attr.startswith('_'):
        print(f"  - {attr}")

# 4. 尝试导入可能的工具模块
print("\n" + "="*60)
print("尝试导入各种可能的模块:")
print("="*60)

possible_imports = [
    "ntwork.utils.tools",
    "ntwork.utils",
    "ntwork.core.mgr",
    "ntwork.conf",
    "ntwork.config",
]

for module_name in possible_imports:
    try:
        module = __import__(module_name, fromlist=[''])
        print(f"✓ {module_name}")
        # 显示模块的属性
        attrs = [a for a in dir(module) if not a.startswith('_')]
        if attrs:
            print(f"  属性: {', '.join(attrs[:10])}")
    except Exception as e:
        print(f"✗ {module_name}: {e}")
