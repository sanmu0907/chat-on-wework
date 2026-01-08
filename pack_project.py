#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目打包脚本 - 打包完整项目包括配置和依赖
"""
import os
import tarfile
import datetime
import sys

def should_exclude(name):
    """判断文件/目录名是否应该排除"""
    exclude_patterns = [
        '.git',
        '__pycache__',
        '.pyc',
        '.DS_Store',
        'nohup.out',
        'pack_project.py',
    ]

    for pattern in exclude_patterns:
        if pattern in name:
            return True
    return False

def pack_project():
    """打包项目"""
    # 获取当前目录
    current_dir = os.getcwd()
    project_name = os.path.basename(current_dir)

    # 生成打包文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join("..", f"{project_name}_full_backup_{timestamp}.tar.gz")

    print(f"开始打包项目...")
    print(f"项目目录: {current_dir}")
    print(f"输出文件: {output_file}")

    file_count = 0

    # 创建tar.gz文件
    with tarfile.open(output_file, "w:gz") as tar:
        for root, dirs, files in os.walk("."):
            # 移除应排除的目录
            dirs[:] = [d for d in dirs if not should_exclude(d)]

            # 跳过tmp和logs目录的内容（但保留目录本身）
            if 'tmp' in root or 'logs' in root:
                if root not in ['./tmp', './logs', '.\\tmp', '.\\logs']:
                    continue

            # 添加文件
            for file in files:
                if should_exclude(file):
                    continue

                file_path = os.path.join(root, file)

                # 跳过tmp和logs目录中的文件
                if '\\tmp\\' in file_path or '/tmp/' in file_path:
                    continue
                if '\\logs\\' in file_path or '/logs/' in file_path:
                    continue

                try:
                    tar.add(file_path)
                    file_count += 1
                    if file_count % 100 == 0:
                        print(f"已打包 {file_count} 个文件...")
                except Exception as e:
                    print(f"跳过文件 {file_path}: {e}")

    # 获取打包文件大小
    pack_size = os.path.getsize(output_file)

    print(f"\n打包完成！")
    print(f"文件数量: {file_count}")
    print(f"打包大小: {pack_size / 1024 / 1024:.2f} MB")
    print(f"输出文件: {os.path.abspath(output_file)}")

    return output_file

if __name__ == "__main__":
    try:
        output_file = pack_project()
        print(f"\n✓ 打包成功!")
    except Exception as e:
        print(f"\n✗ 打包失败: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
