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
    支持占位符：
      - {grandparent}：祖父文件夹名（路径倒数第3级）
      - {parent}：父文件夹名（路径倒数第2级）
      - {file_prefix}：文件名（不含扩展名）的第一个下划线前的部分
      - {stem}：完整的文件名（不含扩展名）
      - {folder_N}：从路径倒数第N级文件夹名（N≥1，1为最末级）
      - {regex:pattern}：从完整路径中按正则表达式提取第一个匹配组
    method 可以是预定义名称（如 'parent_folder_file_prefix'）或自定义模板字符串（以 '{' 开头）。
    """
    path_obj = Path(file_path)
    stem = path_obj.stem
    # 构建路径各级文件夹列表（从根到文件所在目录）
    parts = []
    p = path_obj.parent
    while p != p.parent:
        parts.append(p.name)
        p = p.parent
    parts = parts[::-1]  # 从根到最末级
    # parts 索引0为根目录名，索引-1为最末级文件夹名

    grandparent = parts[-3] if len(parts) >= 3 else ''
    parent = parts[-2] if len(parts) >= 2 else ''
    file_prefix = stem.split('_')[0] if '_' in stem else stem

    # 如果是自定义模板字符串（以 '{' 开头）
    if method.startswith('{'):
        result = method
        # 先处理简单占位符
        result = result.replace('{grandparent}', grandparent)
        result = result.replace('{parent}', parent)
        result = result.replace('{file_prefix}', file_prefix)
        result = result.replace('{stem}', stem)

        # 处理 {folder_N}
        def replace_folder(match):
            try:
                n = int(match.group(1))
                if n >= 1 and n <= len(parts):
                    return parts[-n]
                else:
                    return ''
            except:
                return ''
        result = re.sub(r'\{folder_(\d+)\}', replace_folder, result)

        # 处理 {regex:pattern}
        def replace_regex(match):
            pattern = match.group(1)
            try:
                m = re.search(pattern, str(path_obj))
                if m:
                    return m.group(1) if m.groups() else m.group(0)
                else:
                    return ''
            except:
                return ''
        result = re.sub(r'\{regex:([^}]+)\}', replace_regex, result)

        return result

    # 预定义方法（兼容旧版）
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