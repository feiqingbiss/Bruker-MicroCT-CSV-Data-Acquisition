# -*- coding: utf-8 -*-
"""
CSV解析模块 - 支持多种直方图单位，每个3D结果独立绑定各单位段
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
            '3d_results': [],
            'date': None,
        }

        hist_blocks = []
        two_d_blocks = []
        three_d_blocks = []

        for i, line in enumerate(self.lines):
            stripped = line.strip()

            # ---- 直方图段 ----
            if 'Histogram' in stripped and 'space' in stripped.lower():
                unit = None
                for j in range(i, min(i + 20, len(self.lines))):
                    if 'Unit:' in self.lines[j]:
                        unit_line = self.lines[j].strip()
                        unit = unit_line.split('Unit:')[-1].strip().strip(',')
                        break
                if unit:
                    hist_blocks.append({'start': i, 'unit': unit})

            # ---- 2D 分析段 ----
            if '2D analysis' in stripped:
                param_idx = None
                data_idx = None
                for j in range(i, min(i + 80, len(self.lines))):
                    if 'File name,Z position' in self.lines[j]:
                        param_idx = j
                        for k in range(j + 1, len(self.lines)):
                            lk = self.lines[k].strip()
                            if not lk:
                                continue
                            if 'um' in lk or '%' in lk or '1/um' in lk:
                                continue
                            if 'Pos.Z' in lk or 'Obj.N' in lk:
                                continue
                            parts = lk.split(',')
                            if len(parts) >= 2:
                                first = parts[0].strip()
                                if re.search(r'\.(bmp|tif|tiff|jpg|jpeg|png)$', first, re.I):
                                    try:
                                        if parts[1].strip():
                                            float(parts[1].strip())
                                        data_idx = k
                                        break
                                    except:
                                        pass
                        break
                if param_idx is not None and data_idx is not None:
                    two_d_blocks.append({
                        'start': i,
                        'param_row_idx': param_idx,
                        'data_start_idx': data_idx
                    })

            # ---- 3D 分析段（只取 "3D-analysis summary"） ----
            if '3D-analysis summary' in stripped and '3D analysis' not in stripped:
                param_idx = None
                data_idx = None
                for j in range(i, min(i + 80, len(self.lines))):
                    line_j = self.lines[j].strip()
                    if 'TV' in line_j and 'BV' in line_j and 'BV/TV' in line_j:
                        param_idx = j
                        for k in range(j + 1, len(self.lines)):
                            lk = self.lines[k].strip()
                            if not lk:
                                continue
                            if 'U^3' in lk or 'U^2' in lk or '1/U' in lk:
                                continue
                            parts = lk.split(',')
                            if len(parts) > 6:
                                try:
                                    float(parts[6].strip())
                                    data_idx = k
                                    break
                                except:
                                    pass
                        break
                if param_idx is not None and data_idx is not None:
                    three_d_blocks.append({
                        'start': i,
                        'param_row_idx': param_idx,
                        'data_row_idx': data_idx
                    })

            # ---- 日期 ----
            if 'Date and time' in stripped:
                parts = stripped.split(',')
                if len(parts) >= 2:
                    date_str = parts[1].strip().split()[0]
                    sections['date'] = format_date(date_str)

        # 按单位分组直方图段
        hist_blocks_by_unit = {}
        for hb in hist_blocks:
            unit = hb['unit']
            if unit not in hist_blocks_by_unit:
                hist_blocks_by_unit[unit] = []
            hist_blocks_by_unit[unit].append(hb)

        # 对每个单位，维护已使用的段索引
        used_per_unit = {unit: [False] * len(blocks) for unit, blocks in hist_blocks_by_unit.items()}

        # 2D 段使用标记
        used_2d = [False] * len(two_d_blocks)

        # 为每个3D段分配直方图和2D段
        for three in three_d_blocks:
            three_start = three['start']

            # ---- 为每种单位分配最近的前一个未使用的段 ----
            hist_starts = {}
            for unit, blocks in hist_blocks_by_unit.items():
                assigned_idx = -1
                for idx in range(len(blocks) - 1, -1, -1):
                    if blocks[idx]['start'] < three_start and not used_per_unit[unit][idx]:
                        assigned_idx = idx
                        break
                if assigned_idx != -1:
                    used_per_unit[unit][assigned_idx] = True
                    hist_starts[unit] = blocks[assigned_idx]['start']
                else:
                    hist_starts[unit] = None

            # ---- 分配2D段 ----
            two_idx = -1
            for idx in range(len(two_d_blocks) - 1, -1, -1):
                if two_d_blocks[idx]['start'] < three_start and not used_2d[idx]:
                    two_idx = idx
                    break
            if two_idx != -1:
                used_2d[two_idx] = True

            sections['3d_results'].append({
                'param_row_idx': three['param_row_idx'],
                'data_row_idx': three['data_row_idx'],
                'hist_starts': hist_starts,
                'two_d_block': two_d_blocks[two_idx] if two_idx != -1 else None,
            })
            sections['has_3d'] = True

        if two_d_blocks:
            sections['has_2d'] = True
            sections['2d_param_row_idx'] = two_d_blocks[0]['param_row_idx'] if two_d_blocks else None
            sections['2d_data_start_idx'] = two_d_blocks[0]['data_start_idx'] if two_d_blocks else None

        return sections

    def get_section_info(self):
        return self.sections

    def has_2d(self):
        return self.sections['has_2d']

    def has_3d(self):
        return self.sections['has_3d']

    def get_date(self):
        return self.sections.get('date')

    def get_3d_count(self):
        return len(self.sections.get('3d_results', []))

    def extract_2d_value(self, param_id, result_index=0):
        results = self.sections.get('3d_results', [])
        if not results or result_index >= len(results):
            return None
        two_d_block = results[result_index].get('two_d_block')
        if not two_d_block:
            return None
        return self._extract_value_from_table(
            two_d_block['param_row_idx'],
            two_d_block['data_start_idx'],
            param_id
        )

    def extract_3d_value(self, param_id, result_index=0):
        results = self.sections.get('3d_results', [])
        if not results or result_index >= len(results):
            return None
        result = results[result_index]
        return self._extract_value_from_table(
            result['param_row_idx'],
            result['data_row_idx'],
            param_id
        )

    def extract_histogram_value(self, param_id, result_index=0):
        """提取直方图均值。param_id 用于确定单位（从 ParamDef 中读取 csv_column 作为单位名）"""
        results = self.sections.get('3d_results', [])
        if not results or result_index >= len(results):
            return None

        param_def = self.config.get_param_def(param_id)
        if not param_def:
            return None
        unit = param_def.get('csv_column', '').strip()
        if not unit:
            return None

        hist_starts = results[result_index].get('hist_starts', {})
        hist_start = hist_starts.get(unit)
        if hist_start is None:
            return None

        for i in range(hist_start, min(hist_start + 60, len(self.lines))):
            if self.lines[i].strip().startswith('Mean,'):
                if i + 1 < len(self.lines):
                    mean_line = self.lines[i + 1].strip().split(',')
                    if mean_line:
                        return safe_float(mean_line[0])
        return None

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

    def is_valid(self):
        return self.sections['has_2d'] or self.sections['has_3d']
