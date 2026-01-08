#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目打包脚本
用于创建可部署的项目压缩包
"""

import os
import sys
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
import re

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 打包排除规则文件
PACKIGNORE_FILE = PROJECT_ROOT / ".packignore"

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "dist"


def load_ignore_patterns():
    """加载 .packignore 中的排除规则"""
    patterns = []

    if not PACKIGNORE_FILE.exists():
        print(f"Warning: {PACKIGNORE_FILE} not found, using default patterns")
        return get_default_patterns()

    with open(PACKIGNORE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            patterns.append(line)

    return patterns


def get_default_patterns():
    """默认排除规则"""
    return [
        '__pycache__/',
        '*.pyc',
        '.git/',
        'tmp/',
        '*.log',
        'config.json',
        'venv/',
        'env/',
        '.venv/',
        '*.db',
        '*.rar',
        '*.zip',
        '*.tar.gz',
    ]


def should_exclude(path_str, patterns):
    """判断路径是否应该被排除"""
    path = Path(path_str)

    for pattern in patterns:
        # 目录匹配
        if pattern.endswith('/'):
            pattern_name = pattern.rstrip('/')
            if pattern_name in path.parts:
                return True
        # 通配符匹配
        elif '*' in pattern:
            if path.match(pattern):
                return True
        # 精确匹配
        else:
            if path.name == pattern or str(path) == pattern:
                return True

    return False


def get_all_files(root_dir, patterns):
    """获取所有需要打包的文件"""
    files_to_pack = []
    skipped_files = []

    for root, dirs, files in os.walk(root_dir):
        # 过滤目录
        dirs[:] = [d for d in dirs if not should_exclude(os.path.join(root, d), patterns)]

        for file in files:
            file_path = os.path.join(root, file)

            try:
                relative_path = os.path.relpath(file_path, root_dir)

                if not should_exclude(relative_path, patterns):
                    files_to_pack.append(relative_path)
            except (ValueError, OSError) as e:
                # 跳过有问题的文件（如 Windows 保留设备名）
                skipped_files.append(file_path)
                continue

    if skipped_files:
        print(f"\nWarning: Skipped {len(skipped_files)} problematic files:")
        for f in skipped_files[:5]:  # 只显示前5个
            print(f"  - {f}")
        if len(skipped_files) > 5:
            print(f"  ... and {len(skipped_files) - 5} more")

    return files_to_pack


def create_zip_package(files, output_file, root_dir):
    """创建 ZIP 压缩包"""
    print(f"\nCreating ZIP package: {output_file}")
    print(f"Total files: {len(files)}")

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, file in enumerate(files, 1):
            file_path = os.path.join(root_dir, file)
            arcname = os.path.join('dify-on-wechat', file)
            zipf.write(file_path, arcname)

            if i % 100 == 0:
                print(f"  Packed {i}/{len(files)} files...")

    print(f"[OK] ZIP package created: {output_file}")
    print(f"  Size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")


def create_tar_package(files, output_file, root_dir):
    """创建 TAR.GZ 压缩包"""
    print(f"\nCreating TAR.GZ package: {output_file}")
    print(f"Total files: {len(files)}")

    with tarfile.open(output_file, 'w:gz') as tarf:
        for i, file in enumerate(files, 1):
            file_path = os.path.join(root_dir, file)
            arcname = os.path.join('dify-on-wechat', file)
            tarf.add(file_path, arcname=arcname)

            if i % 100 == 0:
                print(f"  Packed {i}/{len(files)} files...")

    print(f"[OK] TAR.GZ package created: {output_file}")
    print(f"  Size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")


def verify_essential_files(files):
    """验证必要文件是否存在"""
    essential_files = [
        'app.py',
        'plugin_manager.py',
        'requirements.txt',
        'INSTALL.md',
        'CLAUDE.md',
        'config-template.json',
        'README_RESUME.txt',
    ]

    essential_dirs = [
        'bot',
        'bridge',
        'channel',
        'common',
        'lib',
        'plugins',
    ]

    print("\n=== Verifying essential files ===")

    missing = []
    for ef in essential_files:
        if ef not in files:
            missing.append(ef)
            print(f"  [X] Missing: {ef}")
        else:
            print(f"  [OK] Found: {ef}")

    for ed in essential_dirs:
        dir_files = [f for f in files if f.startswith(ed + os.sep)]
        if not dir_files:
            missing.append(ed + '/')
            print(f"  [X] Missing directory: {ed}/")
        else:
            print(f"  [OK] Found directory: {ed}/ ({len(dir_files)} files)")

    if missing:
        print(f"\n[!] Warning: {len(missing)} essential files/dirs missing:")
        for m in missing:
            print(f"    - {m}")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Packaging cancelled.")
            sys.exit(1)
    else:
        print("\n[OK] All essential files verified!")


def main():
    print("=" * 60)
    print("  Dify-on-WeChat Project Packaging Tool")
    print("=" * 60)

    # 加载排除规则
    print("\nLoading exclusion patterns...")
    patterns = load_ignore_patterns()
    print(f"  Loaded {len(patterns)} patterns")

    # 获取所有文件
    print("\nScanning project files...")
    files = get_all_files(PROJECT_ROOT, patterns)
    print(f"  Found {len(files)} files to pack")

    # 验证必要文件
    verify_essential_files(files)

    # 创建输出目录
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 生成文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_file = OUTPUT_DIR / f"dify-on-wechat_{timestamp}.zip"
    tar_file = OUTPUT_DIR / f"dify-on-wechat_{timestamp}.tar.gz"

    # 询问用户要创建哪种格式
    print("\nSelect package format:")
    print("  1. ZIP (Windows recommended)")
    print("  2. TAR.GZ (Linux/Mac recommended)")
    print("  3. Both")

    choice = input("\nYour choice (1/2/3) [default: 3]: ").strip() or "3"

    # 创建压缩包
    if choice in ['1', '3']:
        create_zip_package(files, zip_file, PROJECT_ROOT)

    if choice in ['2', '3']:
        create_tar_package(files, tar_file, PROJECT_ROOT)

    # 总结
    print("\n" + "=" * 60)
    print("  Packaging Complete!")
    print("=" * 60)
    print("\nPackage(s) created in:", OUTPUT_DIR)

    if choice in ['1', '3']:
        print(f"\n  ZIP:     {zip_file.name}")
        print(f"  Size:    {os.path.getsize(zip_file) / 1024 / 1024:.2f} MB")

    if choice in ['2', '3']:
        print(f"\n  TAR.GZ:  {tar_file.name}")
        print(f"  Size:    {os.path.getsize(tar_file) / 1024 / 1024:.2f} MB")

    print("\n" + "=" * 60)
    print("Next steps:")
    print("  1. Transfer the package to target machine")
    print("  2. Extract: unzip <file>.zip  or  tar -xzf <file>.tar.gz")
    print("  3. Follow instructions in INSTALL.md")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPackaging cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
