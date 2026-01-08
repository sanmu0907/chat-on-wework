#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
部署环境检查脚本
用于验证目标机器是否满足运行要求
"""

import sys
import os
import subprocess
from pathlib import Path

# 颜色输出支持
try:
    import colorama
    colorama.init()
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
except:
    GREEN = RED = YELLOW = BLUE = RESET = ''


def print_header(text):
    print(f"\n{BLUE}{'=' * 60}{RESET}")
    print(f"{BLUE}  {text}{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")


def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text):
    print(f"  {text}")


def check_python_version():
    """检查 Python 版本"""
    print_header("Python 版本检查")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    print_info(f"Python 版本: {version_str}")

    if version.major == 3 and version.minor >= 8:
        print_success(f"Python 版本满足要求 (>= 3.8)")
        return True
    else:
        print_error(f"Python 版本过低，需要 >= 3.8，当前: {version_str}")
        return False


def check_pip():
    """检查 pip 是否可用"""
    print_header("pip 检查")

    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print_info(result.stdout.strip())
            print_success("pip 可用")
            return True
        else:
            print_error("pip 不可用")
            return False
    except Exception as e:
        print_error(f"pip 检查失败: {e}")
        return False


def check_project_structure():
    """检查项目结构完整性"""
    print_header("项目结构检查")

    required_files = [
        'app.py',
        'plugin_manager.py',
        'requirements.txt',
        'config-template.json',
        'INSTALL.md',
    ]

    required_dirs = [
        'bot',
        'bridge',
        'channel',
        'common',
        'lib',
        'plugins',
    ]

    all_ok = True

    print_info("检查必要文件:")
    for file in required_files:
        if Path(file).exists():
            print_success(f"  {file}")
        else:
            print_error(f"  {file} (缺失)")
            all_ok = False

    print_info("\n检查必要目录:")
    for dir in required_dirs:
        if Path(dir).is_dir():
            print_success(f"  {dir}/")
        else:
            print_error(f"  {dir}/ (缺失)")
            all_ok = False

    if all_ok:
        print_success("\n项目结构完整")
    else:
        print_error("\n项目结构不完整，可能缺失文件")

    return all_ok


def check_config():
    """检查配置文件"""
    print_header("配置文件检查")

    if Path('config.json').exists():
        print_success("config.json 已存在")
        print_warning("  建议检查配置内容是否正确")
        return True
    elif Path('config-template.json').exists():
        print_warning("config.json 不存在，但找到模板文件")
        print_info("  请执行: cp config-template.json config.json")
        print_info("  然后编辑 config.json 填入你的配置")
        return False
    else:
        print_error("配置文件和模板都不存在")
        return False


def check_network():
    """检查网络连接"""
    print_header("网络连接检查")

    try:
        import socket
        socket.create_connection(("pypi.org", 443), timeout=5)
        print_success("可以访问 PyPI (pypi.org)")
        return True
    except Exception as e:
        print_warning("无法访问 PyPI")
        print_info("  如果需要安装依赖，请配置镜像源或确保网络通畅")
        print_info("  可以使用: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple")
        return False


def check_dependencies():
    """检查依赖是否已安装"""
    print_header("依赖检查")

    if not Path('requirements.txt').exists():
        print_error("requirements.txt 不存在，无法检查依赖")
        return False

    print_info("读取 requirements.txt...")

    with open('requirements.txt', 'r', encoding='utf-8') as f:
        deps = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # 提取包名（去掉版本号）
                pkg = line.split('>=')[0].split('==')[0].split('<')[0].split('>')[0].strip()
                if pkg:
                    deps.append(pkg)

    print_info(f"共 {len(deps)} 个依赖包需要检查\n")

    installed = []
    missing = []

    for pkg in deps:
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', 'show', pkg],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                installed.append(pkg)
                print_success(f"  {pkg}")
            else:
                missing.append(pkg)
                print_error(f"  {pkg}")
        except Exception as e:
            missing.append(pkg)
            print_error(f"  {pkg} (检查失败)")

    print()
    if missing:
        print_warning(f"{len(missing)} 个依赖未安装:")
        for pkg in missing[:10]:  # 只显示前10个
            print_info(f"  - {pkg}")
        if len(missing) > 10:
            print_info(f"  ... 还有 {len(missing) - 10} 个")

        print_info("\n安装依赖:")
        print_info("  pip install -r requirements.txt")
        return False
    else:
        print_success(f"所有 {len(installed)} 个主要依赖已安装")
        return True


def check_writable():
    """检查目录写入权限"""
    print_header("权限检查")

    test_dirs = ['tmp', 'plugins']

    all_ok = True
    for dir_name in test_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True)
                print_success(f"{dir_name}/ 目录已创建")
            except Exception as e:
                print_error(f"无法创建 {dir_name}/ 目录: {e}")
                all_ok = False
                continue

        # 测试写入
        test_file = dir_path / '.write_test'
        try:
            test_file.write_text('test')
            test_file.unlink()
            print_success(f"{dir_name}/ 目录可写")
        except Exception as e:
            print_error(f"{dir_name}/ 目录不可写: {e}")
            all_ok = False

    return all_ok


def generate_report(checks):
    """生成检查报告"""
    print_header("检查总结")

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    for name, result in checks.items():
        if result:
            print_success(name)
        else:
            print_error(name)

    print(f"\n通过: {passed}/{total}")

    if passed == total:
        print_success("\n✓ 所有检查通过！可以开始部署")
        print_info("\n下一步:")
        print_info("  1. 如未安装依赖: pip install -r requirements.txt")
        print_info("  2. 配置: cp config-template.json config.json && 编辑 config.json")
        print_info("  3. 启动: python app.py")
        return True
    else:
        print_warning(f"\n⚠ {total - passed} 项检查未通过")
        print_info("\n请根据上述提示解决问题后再启动项目")
        return False


def main():
    print(f"{BLUE}")
    print("=" * 60)
    print("  Dify-on-WeChat 部署环境检查")
    print("=" * 60)
    print(f"{RESET}")

    # 执行各项检查
    checks = {
        "Python 版本": check_python_version(),
        "pip 工具": check_pip(),
        "项目结构": check_project_structure(),
        "配置文件": check_config(),
        "网络连接": check_network(),
        "依赖安装": check_dependencies(),
        "目录权限": check_writable(),
    }

    # 生成报告
    all_passed = generate_report(checks)

    print()
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
