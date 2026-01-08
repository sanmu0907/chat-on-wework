#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整迁移打包脚本
用于将项目原封不动地迁移到另一台电脑，包含所有配置和数据
"""

import os
import sys
import zipfile
import tarfile
import argparse
from pathlib import Path
from datetime import datetime

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 完整迁移排除规则文件
PACKIGNORE_FILE = PROJECT_ROOT / ".packignore.full"

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "dist"


def load_ignore_patterns():
    """加载 .packignore.full 中的排除规则"""
    patterns = []

    if not PACKIGNORE_FILE.exists():
        print(f"Warning: {PACKIGNORE_FILE} not found, using minimal patterns")
        return get_minimal_patterns()

    with open(PACKIGNORE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            patterns.append(line)

    return patterns


def get_minimal_patterns():
    """最小排除规则（只排除绝对不需要的）"""
    return [
        '__pycache__/',
        '*.pyc',
        'venv/',
        'env/',
        '.venv/',
        'dist/',
        '*.zip',
        '*.tar.gz',
        '*.rar',
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
                # 跳过有问题的文件
                skipped_files.append(file_path)
                continue

    if skipped_files:
        print(f"\nWarning: Skipped {len(skipped_files)} problematic files:")
        for f in skipped_files[:5]:
            print(f"  - {f}")
        if len(skipped_files) > 5:
            print(f"  ... and {len(skipped_files) - 5} more")

    return files_to_pack


def show_important_files(files):
    """显示将要打包的重要文件"""
    important_files = [
        'config.json',
        'plugins/config.json',
        'plugins/plugins.json',
    ]

    data_dirs = [
        'tmp/',
    ]

    print("\n=== Important files to be packed ===")

    for imp in important_files:
        if imp in files:
            print(f"  [OK] {imp} (INCLUDED)")
        else:
            print(f"  [--] {imp} (not found)")

    for data_dir in data_dirs:
        data_files = [f for f in files if f.startswith(data_dir)]
        if data_files:
            print(f"  [OK] {data_dir} ({len(data_files)} files)")
        else:
            print(f"  [--] {data_dir} (empty or not found)")

    print("\n[!] This package will include ALL your configurations and data!")


def create_zip_package(files, output_file, root_dir):
    """创建 ZIP 压缩包"""
    print(f"\nCreating FULL MIGRATION package: {output_file}")
    print(f"Total files: {len(files)}")

    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for i, file in enumerate(files, 1):
            file_path = os.path.join(root_dir, file)
            arcname = os.path.join('dify-on-wechat', file)
            zipf.write(file_path, arcname)

            if i % 100 == 0:
                print(f"  Packed {i}/{len(files)} files...")

    print(f"[OK] Package created: {output_file}")
    print(f"  Size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='完整迁移打包工具')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='自动确认，跳过交互式提示')
    args = parser.parse_args()

    print("=" * 60)
    print("  Dify-on-WeChat FULL MIGRATION Packaging Tool")
    print("  完整迁移打包工具（包含所有配置和数据）")
    print("=" * 60)

    # 加载排除规则
    print("\nLoading exclusion patterns...")
    patterns = load_ignore_patterns()
    print(f"  Loaded {len(patterns)} patterns")

    # 获取所有文件
    print("\nScanning project files...")
    files = get_all_files(PROJECT_ROOT, patterns)
    print(f"  Found {len(files)} files to pack")

    # 显示重要文件
    show_important_files(files)

    # 确认
    print("\n" + "=" * 60)
    print("[!] WARNING: This will create a COMPLETE BACKUP including:")
    print("  - config.json (with API keys and tokens)")
    print("  - plugins/config.json")
    print("  - plugins/plugins.json")
    print("  - tmp/ directory (cached data)")
    print("  - All user data and settings")
    print("\n[!] Keep this package SAFE and PRIVATE!")
    print("=" * 60)

    if not args.yes:
        response = input("\nContinue with full migration packaging? (y/n): ")
        if response.lower() != 'y':
            print("Packaging cancelled.")
            return
    else:
        print("\n[Auto-confirmed with -y flag, proceeding...]")

    # 创建输出目录
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 生成文件名（带时间戳和 FULL 标记）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_file = OUTPUT_DIR / f"dify-on-wechat_FULL_{timestamp}.zip"

    # 创建压缩包
    create_zip_package(files, zip_file, PROJECT_ROOT)

    # 总结
    print("\n" + "=" * 60)
    print("  FULL MIGRATION Package Created!")
    print("=" * 60)
    print(f"\nPackage: {zip_file.name}")
    print(f"Size:    {os.path.getsize(zip_file) / 1024 / 1024:.2f} MB")
    print(f"Files:   {len(files)}")

    print("\n" + "=" * 60)
    print("Migration steps on target machine:")
    print("  1. Transfer this ZIP file to target machine")
    print("  2. Extract: unzip <file>.zip")
    print("  3. cd dify-on-wechat")
    print("  4. Install Python dependencies:")
    print("     pip install -r requirements.txt")
    print("  5. Start directly (config already included):")
    print("     python app.py")
    print("\n[!] IMPORTANT:")
    print("  - If Python version differs, reinstall dependencies")
    print("  - If OS differs (Windows<->Linux), some paths may need adjustment")
    print("  - For wework channel: need same Windows version + WeCom client")
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
