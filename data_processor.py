# -*- coding: utf-8 -*-
"""
数据处理核心模块 - 使用 extract_id 作为键，完全隔离松质/皮质数据
"""

import os
import re
import glob
import pandas as pd
from collections import defaultdict
from pathlib import Path

from config_loader import ConfigLoader
from csv_parser import CSVParser
from utils import extract_sample_id, safe_float


class SampleProcessor:
    def __init__(self, config_loader, root_dir, template_name,
                 log_callback=None, progress_callback=None, verbose=False):
        self.config = config_loader
        self.root_dir = root_dir
        self.template_name = template_name
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.verbose = verbose
        self.samples = defaultdict(list)
        self.results = []
        self.stats = {'total': 0, 'success': 0, 'skipped': 0, 'warning': 0}
        self._stop_flag = False

    def _log(self, msg, tag='info'):
        if self.log_callback:
            self.log_callback(msg, tag) if tag else self.log_callback(msg)

    def _progress(self, current, total, msg=''):
        if self.progress_callback:
            self.progress_callback(current, total, msg)

    def stop(self):
        self._stop_flag = True

    def scan_files(self):
        self._log("正在扫描CSV文件...")
        id_method = self.config.path_rules.get('ID提取方式', 'parent_folder_file_prefix')
        csv_files = glob.glob(os.path.join(self.root_dir, '**', '*.csv'), recursive=True)
        self._log(f"找到 {len(csv_files)} 个CSV文件")
        valid_count = 0
        
        for file_path in csv_files:
            if self._stop_flag:
                return
            parser = CSVParser(file_path, self.config, self.log_callback)
            if not parser.is_valid():
                continue
            valid_count += 1
            sections = parser.get_section_info()
            sample_id = extract_sample_id(file_path, id_method)
            if not sample_id:
                self._log(f"警告: 无法提取样品ID: {file_path}", 'warning')
                continue

            if sections['has_2d']:
                file_type = 'cortical'
            else:
                file_type = 'trabecular'

            self._log(f"  识别: {os.path.basename(file_path)} → {file_type}", 'detail')

            self.samples[sample_id].append({
                'path': file_path,
                'type': file_type,
                'sections': sections,
                'parser': parser,
            })
        self.stats['total'] = len(self.samples)
        self._log(f"有效样品: {len(self.samples)} 个，有效文件: {valid_count} 个")

    def process_all(self):
        total = len(self.samples)
        processed = 0
        for sample_id, files in self.samples.items():
            if self._stop_flag:
                break
            processed += 1
            self._progress(processed, total, f"处理: {sample_id}")
            has_trab = any(f['type'] == 'trabecular' for f in files)
            has_cort = any(f['type'] == 'cortical' for f in files)
            file_info = []
            if has_trab:
                file_info.append('松质')
            if has_cort:
                file_info.append('皮质')
            self._log(f"处理样品: {sample_id} (文件数: {len(files)}, 包含: {' + '.join(file_info)})")
            trab_files = [f for f in files if f['type'] == 'trabecular']
            cort_files = [f for f in files if f['type'] == 'cortical']
            trab_parser = trab_files[0]['parser'] if trab_files else None
            cort_parser = cort_files[0]['parser'] if cort_files else None

            if trab_parser:
                self._log(f"  松质骨parser: {os.path.basename(trab_parser.file_path)}", 'detail')
            if cort_parser:
                self._log(f"  皮质骨parser: {os.path.basename(cort_parser.file_path)}", 'detail')

            if trab_parser or cort_parser:
                row_data = self._extract_row_data(sample_id, trab_parser, cort_parser)
                self.results.append(row_data)
                self.stats['success'] += 1
                if not (trab_parser and cort_parser):
                    self.stats['warning'] += 1
                    missing = '皮质' if trab_parser else '松质'
                    self._log(f"  ⚠ 警告: 仅找到 {missing} 骨数据，缺失侧将留空", 'warning')
            else:
                self.stats['skipped'] += 1
                self._log(f"  ✗ 跳过: 无有效数据", 'warning')
        self._log(f"处理完成: 成功 {self.stats['success']}, 跳过 {self.stats['skipped']}, 警告 {self.stats['warning']}")

    def _extract_row_data(self, sample_id, trab_parser, cort_parser):
        parser = trab_parser or cort_parser
        row_data = {
            'DATE_META': parser.get_date() if parser else None,
            'SAMPLE_ID_META': sample_id,
            'FEMUR_META': '1#'
        }

        columns = self.config.get_template_columns(self.template_name)
        if self.verbose:
            self._log(f"  📋 开始按模板顺序提取参数 (共 {len(columns)} 列):", 'detail')

        extracted_values = {}

        for col_def in columns:
            extract_id = col_def['extract_id']
            if extract_id in row_data or extract_id in self.config.calc_params:
                continue

            rule = self.config.get_extract_rule(extract_id)
            if not rule:
                continue

            source = rule['source']
            param_id = rule['param_id']
            value = None
            
            if '_trab_' in extract_id:
                if trab_parser:
                    if source == '3D':
                        value = trab_parser.extract_3d_value(param_id)
                    elif source == 'Histogram':
                        value = trab_parser.extract_histogram_value('BMD')
                else:
                    value = None
            elif '_cort_' in extract_id:
                if cort_parser:
                    if source == '3D':
                        value = cort_parser.extract_3d_value(param_id)
                    elif source == '2D':
                        value = cort_parser.extract_2d_value(param_id)
                    elif source == 'Histogram':
                        value = cort_parser.extract_histogram_value('BMD')
                else:
                    value = None
            else:
                value = None

            extracted_values[extract_id] = value
            if self.verbose:
                status = '✓' if value is not None else '✗'
                src = '松质' if '_trab_' in extract_id else '皮质' if '_cort_' in extract_id else '未知'
                self._log(f"      {status} {extract_id} ← {src} = {value}", 'detail')

        for col_def in columns:
            extract_id = col_def['extract_id']
            if extract_id in self.config.calc_params:
                calc_result = self._calc_param(extract_id, extracted_values)
                extracted_values[extract_id] = calc_result
                if self.verbose:
                    status = '✓' if calc_result is not None else '✗'
                    self._log(f"      [计算] {extract_id} {status} = {calc_result}", 'detail')

        for extract_id, value in extracted_values.items():
            row_data[extract_id] = value

        extracted_count = sum(1 for v in extracted_values.values() if v is not None)
        failed_count = len(extracted_values) - extracted_count
        self._log(f"  ✅ 提取汇总: ✓ {extracted_count} 个参数, ✗ {failed_count} 个参数缺失",
                  'success' if failed_count == 0 else 'warning')
        return row_data

    def _calc_param(self, calc_id, extracted_values):
        calc_def = self.config.get_calc_param(calc_id)
        if not calc_def:
            return None
        formula = calc_def.get('formula', '')
        placeholders = re.findall(r'\{([^}]+)\}', formula)

        deps = {}
        for ph in placeholders:
            if ph in extracted_values:
                deps[ph] = extracted_values[ph]
            else:
                deps[ph] = None

        for ph in placeholders:
            if deps.get(ph) is None:
                if self.verbose:
                    self._log(f"      [计算] {calc_id} 依赖 {ph} 缺失", 'warning')
                return None

        expr = formula
        for ph in placeholders:
            expr = expr.replace(f'{{{ph}}}', str(deps[ph]))
        try:
            return eval(expr)
        except Exception as e:
            if self.verbose:
                self._log(f"      [计算] {calc_id} 计算失败: {e}", 'error')
            return None

    def export_to_excel(self, output_path):
        if not self.results:
            self._log("没有数据可导出")
            return False
        
        columns = self.config.get_template_columns(self.template_name)
        columns = sorted(columns, key=lambda x: x['order'])
        col_names = [c['column_name'] for c in columns]
        col_extract_ids = [c['extract_id'] for c in columns]
        
        data_rows = []
        for row_data in self.results:
            row = [row_data.get(eid, None) for eid in col_extract_ids]
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows, columns=col_names)
        df.to_excel(output_path, index=False, sheet_name='结果')
        self._log(f"已导出到: {output_path}")
        return True

    def get_stats(self):
        return self.stats

    def get_results(self):
        return self.results
