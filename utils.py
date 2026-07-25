# -*- coding: utf-8 -*-
"""
工具函数模块
提供通用辅助功能
"""

import os
import re
import glob
from datetime import datetime
from pathlib import Path


def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def format_date(date_str):
    try:
        return datetime.strptime(date_str, '%d.%m.%Y').strftime('%Y-%m-%d')
    except:
        return datetime.now().strftime('%Y-%m-%d')


def extract_sample_id(file_path, method='parent_folder_file_prefix'):
    """
    根据 method 提取样品ID。
    method 可以是：
      - 'parent_folder_file_prefix': 父文件夹名 + "_" + 文件名前缀
      - 'parent_folder': 父文件夹名
      - 'file_prefix': 文件名前缀
      - 'grandparent_folder': 祖父文件夹名
      - 'full_path': 完整路径（替换分隔符为下划线）
      - 自定义模板字符串，如 '{grandparent}_{parent}_{file_prefix}'
    """
    path_obj = Path(file_path)
    stem = path_obj.stem
    parts = []
    p = path_obj
    while p.parent != p:
        parts.append(p.name)
        p = p.parent
    parts = parts[::-1]
    grandparent = parts[-3] if len(parts) >= 3 else ''
    parent = parts[-2] if len(parts) >= 2 else ''
    file_prefix = stem.split('_')[0] if '_' in stem else stem

    if method.startswith('{'):
        result = method
        result = result.replace('{grandparent}', grandparent)
        result = result.replace('{parent}', parent)
        result = result.replace('{file_prefix}', file_prefix)
        result = result.replace('{stem}', stem)
        return result

    if method == 'parent_folder_file_prefix':
        if parent and file_prefix:
            return f"{parent}_{file_prefix}"
        elif file_prefix:
            return file_prefix
        else:
            return stem
    elif method == 'parent_folder':
        return parent
    elif method == 'file_prefix':
        return file_prefix
    elif method == 'grandparent_folder':
        return grandparent
    elif method == 'full_path':
        return path_obj.as_posix().replace('/', '_')
    return None


def extract_voi_index(file_path):
    """
    从路径中提取 VOI 序号和是否匹配VOI模式。
    返回 (is_voi_pattern, voi_index)
    is_voi_pattern: 是否匹配 "VOI" 或 "VOI(数字)" 模式
    voi_index: 数字（不匹配时返回 0）
    """
    # 匹配 VOI(数字) 或 VOI
    match = re.search(r'VOI(?:\((\d+)\))?', file_path, re.IGNORECASE)
    if match:
        if match.group(1):
            return (True, int(match.group(1)))
        else:
            return (True, 0)
    return (False, 0)


def is_numeric(value):
    try:
        float(value)
        return True
    except:
        return False


def safe_float(value):
    try:
        return float(value)
    except:
        return None


def safe_int(value):
    try:
        return int(float(value))
    except:
        return None


def find_files_by_extension(root_dir, extensions):
    files = []
    for ext in extensions:
        pattern = os.path.join(root_dir, '**', f'*.{ext}')
        files.extend([f for f in glob.glob(pattern, recursive=True)])
    return files