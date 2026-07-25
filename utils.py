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
    支持占位符：{grandparent}, {parent}, {file_prefix}, {stem}, {folder_N}, {regex:pattern}
    """
    path_obj = Path(file_path)
    stem = path_obj.stem
    parts = []
    p = path_obj.parent
    while p != p.parent:
        parts.append(p.name)
        p = p.parent
    parts = parts[::-1]  # 从根到最末级

    grandparent = parts[-3] if len(parts) >= 3 else ''
    parent = parts[-2] if len(parts) >= 2 else ''
    file_prefix = stem.split('_')[0] if '_' in stem else stem

    if method.startswith('{'):
        result = method
        result = result.replace('{grandparent}', grandparent)
        result = result.replace('{parent}', parent)
        result = result.replace('{file_prefix}', file_prefix)
        result = result.replace('{stem}', stem)

        def replace_folder(match):
            try:
                n = int(match.group(1))
                return parts[-n] if 1 <= n <= len(parts) else ''
            except:
                return ''
        result = re.sub(r'\{folder_(\d+)\}', replace_folder, result)

        def replace_regex(match):
            pattern = match.group(1)
            try:
                m = re.search(pattern, str(path_obj))
                return m.group(1) if m and m.groups() else (m.group(0) if m else '')
            except:
                return ''
        result = re.sub(r'\{regex:([^}]+)\}', replace_regex, result)
        return result

    # 预定义方法（兼容旧版）
    if method == 'parent_folder_file_prefix':
        return f"{parent}_{file_prefix}" if parent and file_prefix else (file_prefix or stem)
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
    match = re.search(r'VOI(?:\((\d+)\))?', file_path, re.IGNORECASE)
    if match:
        return (True, int(match.group(1)) if match.group(1) else 0)
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
        files.extend(glob.glob(pattern, recursive=True))
    return files