"""
扫描项目依赖的脚本
"""
import os
import re
from pathlib import Path

# Python 标准库列表(部分)
STDLIB_MODULES = {
    'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections', 'concurrent',
    'configparser', 'copy', 'csv', 'dataclasses', 'datetime', 'decimal', 'difflib',
    'enum', 'functools', 'glob', 'hashlib', 'hmac', 'html', 'http', 'importlib',
    'inspect', 'io', 'itertools', 'json', 'logging', 'math', 'mimetypes', 'multiprocessing',
    'operator', 'os', 'pathlib', 'pickle', 'platform', 'queue', 'random', 're',
    'shutil', 'signal', 'socket', 'sqlite3', 'ssl', 'statistics', 'string', 'struct',
    'subprocess', 'sys', 'tempfile', 'textwrap', 'threading', 'time', 'traceback',
    'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref', 'xml', 'zipfile',
    'zlib', '__future__', 'contextlib', 'secrets', 'binascii', 'codecs', 'errno',
    'getpass', 'select', 'selectors', 'array', 'ctypes', 'gc', 'types', 'builtins'
}

def extract_imports(file_path):
    """提取Python文件中的import语句"""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 匹配 import xxx
        for match in re.finditer(r'^\s*import\s+([a-zA-Z0-9_\.]+)', content, re.MULTILINE):
            module = match.group(1).split('.')[0]
            imports.add(module)

        # 匹配 from xxx import
        for match in re.finditer(r'^\s*from\s+([a-zA-Z0-9_\.]+)\s+import', content, re.MULTILINE):
            module = match.group(1).split('.')[0]
            imports.add(module)

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return imports

def is_local_module(module_name, project_root):
    """判断是否是本地模块"""
    local_modules = {'bot', 'bridge', 'channel', 'common', 'config', 'lib', 'plugins', 'voice', 'translate'}
    return module_name in local_modules

def scan_directory(directory, project_root):
    """扫描目录下的所有Python文件"""
    all_imports = set()

    for root, dirs, files in os.walk(directory):
        # 跳过 __pycache__ 等目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.github', 'venv', 'env', '.venv']]

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                imports = extract_imports(file_path)
                all_imports.update(imports)

    # 过滤掉标准库和本地模块
    third_party = set()
    for module in all_imports:
        if module not in STDLIB_MODULES and not is_local_module(module, project_root):
            third_party.add(module)

    return sorted(third_party)

def main():
    project_root = Path(__file__).parent

    print("=== 扫描主项目依赖 ===")

    # 扫描主项目 (排除 plugins 目录)
    main_imports = set()
    for item in ['bot', 'bridge', 'channel', 'common', 'lib', 'voice', 'translate']:
        item_path = project_root / item
        if item_path.exists():
            imports = scan_directory(item_path, project_root)
            main_imports.update(imports)

    # 扫描根目录的 .py 文件
    for py_file in project_root.glob('*.py'):
        if py_file.name != 'scan_dependencies.py':
            imports = extract_imports(py_file)
            for module in imports:
                if module not in STDLIB_MODULES and not is_local_module(module, project_root):
                    main_imports.add(module)

    print("\n主项目第三方依赖:")
    for module in sorted(main_imports):
        print(f"  - {module}")

    print(f"\n共 {len(main_imports)} 个第三方依赖")

    # 扫描插件
    plugins_dir = project_root / 'plugins'
    if plugins_dir.exists():
        print("\n=== 扫描插件依赖 ===\n")

        for plugin_dir in sorted(plugins_dir.iterdir()):
            if plugin_dir.is_dir() and not plugin_dir.name.startswith('__'):
                plugin_imports = set()

                for py_file in plugin_dir.rglob('*.py'):
                    imports = extract_imports(py_file)
                    for module in imports:
                        if module not in STDLIB_MODULES and not is_local_module(module, project_root):
                            plugin_imports.add(module)

                # 移除主项目已有的依赖
                plugin_specific = plugin_imports - main_imports

                if plugin_imports:
                    print(f"{plugin_dir.name}:")
                    print(f"  总依赖: {sorted(plugin_imports)}")
                    if plugin_specific:
                        print(f"  插件特有: {sorted(plugin_specific)}")
                    else:
                        print(f"  插件特有: (无,都在主项目中)")
                    print()

if __name__ == '__main__':
    main()
