# -*- coding: utf-8 -*-
"""
CSV解析模块 - 增强2D数据行检测
"""

import os
import re
from utils import safe_float, format_date


class CSVParser:
    def __init__(self, file_path, config_loader, log_callback=None):
        self.file_path = file_path
        self.config = config_loader
        self.log_callback = log_callback
        self.lines = self._read_file()
        self.bmd_mean = None
        self.sections = self._identify_sections()

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    def _read_file(self):
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        for enc in encodings:
            try:
                with open(self.file_path, 'r', encoding=enc, errors='ignore') as f:
                    return f.readlines()
            except:
                continue
        return []

    def _identify_sections(self):
        sections = {
            'has_2d': False,
            'has_3d': False,
            'has_histogram': False,
            '2d_param_row_idx': None,
            '2d_data_start_idx': None,
            '3d_param_row_idx': None,
            '3d_data_row_idx': None,
            'date': None,
        }
        for i, line in enumerate(self.lines):
            stripped = line.strip()
            # 2D
            if '2D analysis' in stripped:
                for j in range(i, min(i+80, len(self.lines))):
                    if 'File name,Z position' in self.lines[j]:
                        sections['has_2d'] = True
                        sections['2d_param_row_idx'] = j
                        # 查找数据起始行
                        for k in range(j + 1, len(self.lines)):
                            lk = self.lines[k].strip()
                            if not lk:
                                continue
                            # 跳过单位行和缩写行
                            if 'um' in lk or '%' in lk or '1/um' in lk:
                                continue
                            if 'Pos.Z' in lk or 'Obj.N' in lk:
                                continue
                            parts = lk.split(',')
                            if len(parts) >= 2:
                                first = parts[0].strip()
                                # 检查是否是数据行：以图片扩展名结尾，或包含下划线和数字
                                if re.search(r'\.(bmp|tif|tiff|jpg|jpeg|png)$', first, re.I):
                                    try:
                                        if parts[1].strip():
                                            float(parts[1].strip())
                                        sections['2d_data_start_idx'] = k
                                        break
                                    except:
                                        pass
                                # 如果第一列包含下划线和数字，也尝试作为数据行
                                elif '_' in first and any(c.isdigit() for c in first):
                                    try:
                                        if parts[1].strip():
                                            float(parts[1].strip())
                                        sections['2d_data_start_idx'] = k
                                        break
                                    except:
                                        pass
                        break
                # 如果还没有找到数据行，尝试更宽松的匹配
                if sections['has_2d'] and sections['2d_data_start_idx'] is None:
                    for k in range(sections['2d_param_row_idx'] + 1, len(self.lines)):
                        lk = self.lines[k].strip()
                        if not lk:
                            continue
                        if 'um' in lk or '%' in lk:
                            continue
                        if 'Pos.Z' in lk or 'Obj.N' in lk:
                            continue
                        parts = lk.split(',')
                        if len(parts) >= 2:
                            first = parts[0].strip()
                            # 如果第一列包含下划线或数字，视为潜在数据行
                            if '_' in first or any(c.isdigit() for c in first):
                                try:
                                    if parts[1].strip():
                                        float(parts[1].strip())
                                    sections['2d_data_start_idx'] = k
                                    break
                                except:
                                    pass
            # 3D
            if '3D analysis' in stripped or '3D-analysis summary' in stripped:
                sections['has_3d'] = True
                for j in range(i, min(i+80, len(self.lines))):
                    if 'TV' in self.lines[j] and 'BV' in self.lines[j] and 'BV/TV' in self.lines[j]:
                        sections['3d_param_row_idx'] = j
                        for k in range(j+1, len(self.lines)):
                            lk = self.lines[k].strip()
                            if not lk:
                                continue
                            if 'U^3' in lk or 'U^2' in lk or '1/U' in lk:
                                continue
                            parts = lk.split(',')
                            if len(parts) > 6:
                                try:
                                    float(parts[6].strip())
                                    sections['3d_data_row_idx'] = k
                                    break
                                except:
                                    pass
                        break
            # Histogram
            if 'Histogram' in stripped and 'space' in stripped.lower():
                sections['has_histogram'] = True
                for j in range(i, min(i+60, len(self.lines))):
                    if 'Unit:' in self.lines[j]:
                        unit_line = self.lines[j].strip()
                        unit = unit_line.split('Unit:')[-1].strip().strip(',')
                        # 记录直方图单位
                        sections['histogram_unit'] = unit
                        if unit == 'BMD':
                            for k in range(j, min(j+25, len(self.lines))):
                                if self.lines[k].strip().startswith('Mean,'):
                                    if k+1 < len(self.lines):
                                        mean_line = self.lines[k+1].strip().split(',')
                                        if mean_line:
                                            val = safe_float(mean_line[0])
                                            self.bmd_mean = val
                                    break
                            break
            # Date
            if 'Date and time' in stripped:
                parts = stripped.split(',')
                if len(parts) >= 2:
                    date_str = parts[1].strip().split()[0]
                    sections['date'] = format_date(date_str)
        return sections

    def get_section_info(self):
        return self.sections

    def has_2d(self):
        return self.sections['has_2d']

    def has_3d(self):
        return self.sections['has_3d']

    def get_date(self):
        return self.sections.get('date')

    def extract_2d_value(self, param_id):
        if not self.sections['has_2d']:
            return None
        if self.sections['2d_param_row_idx'] is None or self.sections['2d_data_start_idx'] is None:
            return None
        return self._extract_value_from_table(
            self.sections['2d_param_row_idx'],
            self.sections['2d_data_start_idx'],
            param_id
        )

    def extract_3d_value(self, param_id):
        if not self.sections['has_3d']:
            return None
        if self.sections['3d_param_row_idx'] is None or self.sections['3d_data_row_idx'] is None:
            return None
        return self._extract_value_from_table(
            self.sections['3d_param_row_idx'],
            self.sections['3d_data_row_idx'],
            param_id
        )

    def _extract_value_from_table(self, param_row_idx, data_row_idx, param_id):
        param_row = self.lines[param_row_idx].strip()
        param_cols = param_row.split(',')
        param_def = self.config.get_param_def(param_id)
        if not param_def:
            return None

        candidates = []
        csv_col = param_def.get('csv_column', '').strip()
        full_name = param_def.get('full_name', '').strip()
        aliases = param_def.get('alias', [])
        if csv_col:
            candidates.append(csv_col)
        if full_name:
            candidates.append(full_name)
        for alias in aliases:
            if alias and alias not in candidates:
                candidates.append(alias)

        col_idx = None
        for i, col in enumerate(param_cols):
            col_clean = col.strip()
            if col_clean in candidates:
                col_idx = i
                break
        if col_idx is None:
            return None

        data_line = self.lines[data_row_idx].strip()
        data_parts = data_line.split(',')
        if col_idx < len(data_parts):
            val = data_parts[col_idx].strip()
            if val:
                if '(' in val and ')' in val:
                    m = re.match(r'([\d.]+)\s*\(([\d.]+)\)', val)
                    if m:
                        if param_id == 'DA_ratio':
                            return float(m.group(2))
                        if param_id == 'DA':
                            return float(m.group(1))
                return safe_float(val) or val
        return None

    def extract_histogram_value(self, unit):
        if unit == 'BMD':
            return self.bmd_mean
        return None

    def is_valid(self):
        return self.sections['has_2d'] or self.sections['has_3d']
