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
    path_obj = Path(file_path)
    
    if method == 'parent_folder_file_prefix':
        parent_name = path_obj.parent.parent.name
        file_prefix = path_obj.stem.split('_')[0]
        if parent_name and file_prefix:
            return f"{parent_name}_{file_prefix}"
    
    elif method == 'parent_folder':
        return path_obj.parent.parent.name
    
    elif method == 'file_prefix':
        return path_obj.stem.split('_')[0]
    
    elif method == 'grandparent_folder':
        return path_obj.parent.parent.parent.name
    
    return None


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
