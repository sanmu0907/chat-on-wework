#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目打包脚本 - 打包为ZIP格式（Windows友好）
"""
import os
import zipfile
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
        'pack_project_zip.py',
    ]

    for pattern in exclude_patterns:
        if pattern in name:
            return True
    return False

def pack_project_zip():
    """打包项目为ZIP"""
    # 获取当前目录
    current_dir = os.getcwd()
    project_name = os.path.basename(current_dir)

    # 生成打包文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join("..", f"{project_name}_full_backup_{timestamp}.zip")

    print(f"开始打包项目（ZIP格式）...")
    print(f"项目目录: {current_dir}")
    print(f"输出文件: {output_file}")

    file_count = 0
    total_size = 0

    # 创建ZIP文件
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("."):
            # 移除应排除的目录
            dirs[:] = [d for d in dirs if not should_exclude(d)]

            # 跳过tmp和logs目录的内容
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
                    # 计算相对路径（去掉开头的./）
                    arcname = file_path[2:] if file_path.startswith('.\\') or file_path.startswith('./') else file_path
                    zipf.write(file_path, arcname)

                    file_count += 1
                    file_size = os.path.getsize(file_path)
                    total_size += file_size

                    if file_count % 100 == 0:
                        print(f"已打包 {file_count} 个文件...")
                except Exception as e:
                    print(f"跳过文件 {file_path}: {e}")

    # 获取打包文件大小
    pack_size = os.path.getsize(output_file)

    print(f"\n打包完成！")
    print(f"文件数量: {file_count}")
    print(f"原始大小: {total_size / 1024 / 1024:.2f} MB")
    print(f"打包大小: {pack_size / 1024 / 1024:.2f} MB")
    print(f"压缩率: {(1 - pack_size / total_size) * 100:.1f}%")
    print(f"输出文件: {os.path.abspath(output_file)}")

    return output_file, file_count

if __name__ == "__main__":
    try:
        output_file, file_count = pack_project_zip()
        print(f"\n[OK] 打包成功!")
        print(f"文件: {output_file}")
        print(f"数量: {file_count} 个文件")
    except Exception as e:
        print(f"\n[ERROR] 打包失败: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
