# -*- coding: utf-8 -*-
"""
数据处理核心模块
"""

import os
import re
import glob
import pandas as pd
from collections import defaultdict
from pathlib import Path
from datetime import datetime

from config_loader import ConfigLoader
from csv_parser import CSVParser
from utils import extract_sample_id, extract_voi_index, safe_float


def natural_key(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]


class SampleProcessor:
    def __init__(self, config_loader, root_dir, template_name,
                 log_callback=None, progress_callback=None, verbose=False):
        self.config = config_loader
        self.root_dir = root_dir
        self.template_name = template_name
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.verbose = verbose

        self.is_single_mode = ('一个样品CSV内多个ROI分析结果' in template_name)
        self.is_voi_mode = ('一组样品不同部位、重复同名CSV' in template_name)

        self.samples = defaultdict(list)
        self.results = []
        self.errors = []
        self.warnings = []
        self.stats = {'total': 0, 'success': 0, 'skipped': 0, 'warning': 0, 'error': 0}
        self._stop_flag = False

    def _log(self, msg, tag='info'):
        if self.log_callback:
            self.log_callback(msg, tag)

    def _add_error(self, sample_id, file_path, param_id, message):
        self.errors.append({'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'sample_id': sample_id, 'file_path': file_path,
                            'param_id': param_id, 'message': message})
        self.stats['error'] += 1

    def _add_warning(self, sample_id, file_path, message, param_id=''):
        self.warnings.append({'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                              'sample_id': sample_id, 'file_path': file_path,
                              'param_id': param_id, 'message': message})
        self.stats['warning'] += 1

    def _progress(self, current, total, msg=''):
        if self.progress_callback:
            self.progress_callback(current, total, msg)

    def stop(self):
        self._stop_flag = True

    def scan_files(self):
        self._log("正在扫描CSV文件...")
        id_rule = self.config.get_sample_id_rule(self.template_name)
        self._log(f"样品ID规则: {id_rule}", 'info')

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

            if self.is_voi_mode:
                stem = os.path.splitext(os.path.basename(file_path))[0]
                sample_id = stem.split('_')[0] if '_' in stem else stem
                folder_name = os.path.basename(os.path.dirname(file_path))
                parent_folder_name = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
                is_voi_pattern, voi_idx = extract_voi_index(file_path)
            else:
                sample_id = extract_sample_id(file_path, id_rule)
                if not sample_id:
                    self._log(f"警告: 无法提取样品ID: {file_path}", 'warning')
                    self._add_warning('unknown', file_path, f"无法提取样品ID: {file_path}")
                    continue
                folder_name = ''
                parent_folder_name = ''
                is_voi_pattern = False
                voi_idx = 0

            if self.is_single_mode:
                file_type = 'single'
            elif self.is_voi_mode:
                file_type = 'voi'
            else:
                file_type = 'cortical' if sections['has_2d'] else 'trabecular'

            if self.is_single_mode:
                _3d_count = parser.get_3d_count()
                if _3d_count > 1:
                    self._log(f"  检测到 {_3d_count} 个3D分析结果，将分别提取", 'detail')

            self._log(f"  识别: {os.path.basename(file_path)} → {file_type}", 'detail')
            self.samples[sample_id].append({
                'path': file_path,
                'type': file_type,
                'sections': sections,
                'parser': parser,
                'folder_name': folder_name,
                'parent_folder_name': parent_folder_name,
                'voi_idx': voi_idx,
                'is_voi_pattern': is_voi_pattern,
            })

        self.stats['total'] = len(self.samples)
        self._log(f"有效样品: {len(self.samples)} 个，有效文件: {valid_count} 个")

    def process_all(self):
        total = len(self.samples)
        processed = 0
        for sample_id, files in sorted(self.samples.items(), key=lambda item: natural_key(item[0])):
            if self._stop_flag:
                break
            processed += 1
            self._progress(processed, total, f"处理: {sample_id}")

            if self.is_single_mode:
                self._process_single_mode(sample_id, files)
            elif self.is_voi_mode:
                self._process_voi_mode(sample_id, files)
            else:
                self._process_pair_mode(sample_id, files)

        self._log(f"处理完成: 成功 {self.stats['success']}, 跳过 {self.stats['skipped']}, "
                  f"警告 {self.stats['warning']}, 错误 {self.stats['error']}")

    # ---------- 统一提取核心 ----------
    def _extract_from_parsers(self, parsers, sample_id, columns, mode='single', result_index=0):
        extracted = {}
        for col_def in columns:
            extract_id = col_def['extract_id']
            if extract_id in ['DATE_META', 'SAMPLE_ID_META', 'FOLDER_NAME']:
                continue
            if extract_id in self.config.calc_params:
                continue

            rule = self.config.get_extract_rule(extract_id)
            if not rule:
                self._add_warning(sample_id, '', f"未知提取指令: {extract_id}", extract_id)
                continue

            source = rule['source']
            param_id = rule['param_id']
            value = None

            if mode == 'single':
                parser = parsers[0] if parsers else None
                if parser:
                    if source == '3D':
                        value = parser.extract_value('3D', param_id, result_index)
                    elif source == '2D':
                        value = parser.extract_value('2D', param_id, result_index)
                    elif source == 'Histogram':
                        value = parser.extract_value('Histogram', param_id, result_index)
                        if value is None:
                            self._add_warning(sample_id, parser.file_path, f"直方图提取失败: {extract_id}", extract_id)
            elif mode == 'pair':
                if '_trab_' in extract_id:
                    parser = parsers.get('trab')
                elif '_cort_' in extract_id:
                    parser = parsers.get('cort')
                else:
                    parser = None
                if parser:
                    if source == '3D':
                        value = parser.extract_value('3D', param_id, 0)
                    elif source == '2D':
                        value = parser.extract_value('2D', param_id, 0)
                    elif source == 'Histogram':
                        value = parser.extract_value('Histogram', param_id, 0)
                        if value is None:
                            self._add_warning(sample_id, parser.file_path, f"直方图提取失败: {extract_id}", extract_id)
                else:
                    value = None
            elif mode == 'voi':
                parser = parsers[0] if parsers else None
                if parser:
                    if source == '3D':
                        value = parser.extract_value('3D', param_id, 0)
                    elif source == '2D':
                        value = parser.extract_value('2D', param_id, 0)
                    elif source == 'Histogram':
                        value = parser.extract_value('Histogram', param_id, 0)

            extracted[extract_id] = value
            if self.verbose and value is not None:
                self._log(f"      {extract_id} = {value}", 'detail')
            if value is None and source != 'Histogram':
                file_path = parser.file_path if parser else ''
                self._add_error(sample_id, file_path, extract_id, f"提取失败: {extract_id} 返回 None")

        # 计算参数
        for col_def in columns:
            extract_id = col_def['extract_id']
            if extract_id in self.config.calc_params:
                # 获取有效的parser用于错误日志
                valid_parser = None
                if mode == 'single' and parsers:
                    valid_parser = parsers[0]
                elif mode == 'pair':
                    valid_parser = parsers.get('trab') or parsers.get('cort')
                elif mode == 'voi' and parsers:
                    valid_parser = parsers[0]
                calc_value = self._calc_param(extract_id, extracted, sample_id, valid_parser)
                extracted[extract_id] = calc_value
                if self.verbose and calc_value is not None:
                    self._log(f"      [计算] {extract_id} = {calc_value}", 'detail')

        return extracted

    def _calc_param(self, calc_id, extracted_values, sample_id, parser):
        calc_def = self.config.get_calc_param(calc_id)
        if not calc_def:
            self._add_warning(sample_id, parser.file_path if parser else '', f"计算参数定义缺失: {calc_id}", calc_id)
            return None
        formula = calc_def.get('formula', '')
        placeholders = re.findall(r'\{([^}]+)\}', formula)
        deps = {}
        missing = []
        for ph in placeholders:
            if ph in extracted_values:
                deps[ph] = extracted_values[ph]
            else:
                deps[ph] = None
                missing.append(ph)
        if missing:
            self._add_warning(sample_id, parser.file_path if parser else '',
                              f"计算参数 {calc_id} 依赖缺失: {', '.join(missing)}", calc_id)
            return None
        expr = formula
        for ph in placeholders:
            if deps.get(ph) is None:
                return None
            expr = expr.replace(f'{{{ph}}}', str(deps[ph]))
        try:
            return eval(expr)
        except Exception as e:
            self._add_error(sample_id, parser.file_path if parser else '', calc_id, f"计算失败: {calc_id} - {e}")
            return None

    # ---------- 三种处理模式 ----------
    def _process_single_mode(self, sample_id, files):
        self._log(f"处理样品: {sample_id} (文件数: {len(files)})")
        for file_info in files:
            parser = file_info['parser']
            _3d_count = parser.get_3d_count()
            if _3d_count <= 1:
                self._extract_row_data_single(sample_id, parser, result_index=0)
                self.stats['success'] += 1
            else:
                self._log(f"  📊 该文件包含 {_3d_count} 个3D分析结果", 'info')
                for idx in range(_3d_count):
                    result_suffix = f"_R{idx+1}"
                    result_id = sample_id + result_suffix
                    self._log(f"    提取结果 {idx+1}/{_3d_count}: {result_id}", 'detail')
                    self._extract_row_data_single(result_id, parser, result_index=idx)
                    self.stats['success'] += 1

    def _extract_row_data_single(self, sample_id, parser, result_index=0):
        columns = self.config.get_template_columns(self.template_name)
        row_data = {'DATE_META': parser.get_date() if parser else None,
                    'SAMPLE_ID_META': sample_id}
        extracted = self._extract_from_parsers([parser], sample_id, columns, 'single', result_index)
        row_data.update(extracted)
        self.results.append(row_data)
        extracted_count = sum(1 for v in extracted.values() if v is not None)
        failed_count = len(extracted) - extracted_count
        self._log(f"  ✅ 提取汇总: ✓ {extracted_count} 个参数, ✗ {failed_count} 个参数缺失",
                  'success' if failed_count == 0 else 'warning')

    def _process_voi_mode(self, sample_id, files):
        # 按路径排序（含VOI编号优先）
        def sort_key(f):
            if f.get('is_voi_pattern', False):
                return (0, f.get('voi_idx', 0), f.get('path', ''))
            else:
                return (1, 0, f.get('path', ''))
        files_sorted = sorted(files, key=sort_key)
        self._log(f"处理样品: {sample_id} (扫描到 {len(files_sorted)} 个文件夹)")

        columns = self.config.get_template_columns(self.template_name)
        voi_rows = []
        for file_info in files_sorted:
            parser = file_info['parser']
            row_data = {'DATE_META': parser.get_date() if parser else None,
                        'SAMPLE_ID_META': sample_id,
                        'FOLDER_NAME': file_info.get('folder_name', ''),
                        'PARENT_FOLDER_NAME': file_info.get('parent_folder_name', '')}
            extracted = self._extract_from_parsers([parser], sample_id, columns, 'voi', 0)
            row_data.update(extracted)
            # 检查是否有数据
            has_data = any(v is not None and str(v).strip() != '' for k, v in extracted.items()
                           if k not in ['DATE_META', 'SAMPLE_ID_META', 'FOLDER_NAME'])
            if has_data:
                voi_rows.append(row_data)
                self._log(f"  ✅ 有效文件夹: {file_info.get('folder_name', '')}", 'info')
            else:
                self._log(f"  ⚠ 跳过空数据文件夹: {file_info.get('folder_name', '')}", 'warning')

        if not voi_rows:
            self._log(f"  ⚠ 没有有效数据，跳过样品 {sample_id}", 'warning')
            return

        self._log(f"  📊 实际合并 {len(voi_rows)} 个有效文件夹", 'info')
        merged_row = self._merge_voi_rows_with_spacer(voi_rows, sample_id)
        self.results.append(merged_row)
        self.stats['success'] += 1

    def _merge_voi_rows_with_spacer(self, rows, sample_id):
        if not rows:
            return {}
        base_row = {'日期': rows[0]['DATE_META'], '样品ID': sample_id}
        columns = self.config.get_template_columns(self.template_name)
        id_to_col = {}
        for col in columns:
            eid = col['extract_id']
            if eid not in ['DATE_META', 'SAMPLE_ID_META', 'FOLDER_NAME']:
                id_to_col[eid] = col['column_name']
        param_ids = list(id_to_col.keys())

        folder_names = [row.get('FOLDER_NAME', f'Folder{i+1}') for i, row in enumerate(rows)]
        seen = {}
        unique_suffixes = []
        for name in folder_names:
            if name not in seen:
                seen[name] = 1
                unique_suffixes.append(name)
            else:
                seen[name] += 1
                unique_suffixes.append(f"{name}_{seen[name]}")

        for i, row in enumerate(rows):
            if i > 0:
                base_row[f"间隔_{i}_1"] = None
                base_row[f"间隔_{i}_2"] = None

            suffix = f"_{unique_suffixes[i]}"
            folder_name = row.get('FOLDER_NAME', '')
            parent_folder = row.get('PARENT_FOLDER_NAME', '')
            display_folder = f"{parent_folder}_{folder_name}" if parent_folder else folder_name
            base_row[f"文件夹名{suffix}"] = display_folder

            for param_id in param_ids:
                col_name = id_to_col[param_id]
                key = f"{col_name}{suffix}"
                base_row[key] = row.get(param_id, None)

        return base_row

    def _process_pair_mode(self, sample_id, files):
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
            self._extract_row_data_pair(sample_id, trab_parser, cort_parser)
            self.stats['success'] += 1
            if not (trab_parser and cort_parser):
                if trab_parser and not cort_parser:
                    self._log(f"  ⚠ 警告: 仅找到 松质 骨数据，皮质侧将留空", 'warning')
                    self._add_warning(sample_id, trab_parser.file_path, "仅找到松质骨数据，皮质侧留空")
                elif cort_parser and not trab_parser:
                    self._log(f"  ⚠ 警告: 仅找到 皮质 骨数据，松质侧将留空", 'warning')
                    self._add_warning(sample_id, cort_parser.file_path, "仅找到皮质骨数据，松质侧留空")
        else:
            self.stats['skipped'] += 1
            self._log(f"  ✗ 跳过: 无有效数据", 'warning')
            self._add_warning(sample_id, '', "无有效数据")

    def _extract_row_data_pair(self, sample_id, trab_parser, cort_parser):
        parser = trab_parser or cort_parser
        row_data = {'DATE_META': parser.get_date() if parser else None,
                    'SAMPLE_ID_META': sample_id}
        columns = self.config.get_template_columns(self.template_name)
        parsers = {'trab': trab_parser, 'cort': cort_parser}
        extracted = self._extract_from_parsers(parsers, sample_id, columns, 'pair', 0)
        row_data.update(extracted)
        self.results.append(row_data)
        extracted_count = sum(1 for v in extracted.values() if v is not None)
        failed_count = len(extracted) - extracted_count
        self._log(f"  ✅ 提取汇总: ✓ {extracted_count} 个参数, ✗ {failed_count} 个参数缺失",
                  'success' if failed_count == 0 else 'warning')

    # ---------- 导出方法 ----------
    def export_to_excel(self, output_path):
        if not self.results:
            self._log("没有数据可导出")
            return False

        if self.is_voi_mode:
            df = pd.DataFrame(self.results)
            current_cols = df.columns.tolist()
            ordered_cols = []
            for col in ['日期', '样品ID']:
                if col in current_cols:
                    ordered_cols.append(col)
            for col in current_cols:
                if col not in ordered_cols:
                    ordered_cols.append(col)
            df = df[ordered_cols]
            df.to_excel(output_path, index=False, sheet_name='结果')
            self._log(f"已导出到: {output_path}")
            return True

        if self.is_single_mode:
            columns = self.config.get_template_columns(self.template_name)
            columns = sorted(columns, key=lambda x: x['order'])
            col_names = [c['column_name'] for c in columns]
            col_extract_ids = [c['extract_id'] for c in columns]

            groups = {}
            for row_data in self.results:
                sample_id = row_data.get('SAMPLE_ID_META', '')
                base_sample = sample_id
                if sample_id:
                    match = re.match(r'(.+)_R\d+$', sample_id)
                    if match:
                        base_sample = match.group(1)
                    else:
                        base_sample = sample_id
                groups.setdefault(base_sample, []).append(row_data)

            max_results = max((len(rows) for rows in groups.values()), default=0)
            expanded_rows = []
            for base_sample, rows in groups.items():
                date_val = rows[0].get('DATE_META', None)
                new_row = [date_val, base_sample]
                for idx in range(max_results):
                    if idx < len(rows):
                        row_dict = rows[idx]
                        param_values = [row_dict.get(eid, None) for eid in col_extract_ids if eid not in ['DATE_META', 'SAMPLE_ID_META']]
                    else:
                        param_values = [None] * (len(col_extract_ids) - 2)
                    new_row.extend(param_values)
                    if idx < max_results - 1:
                        new_row.extend([None, None])
                expanded_rows.append(new_row)

            new_col_names = ['日期', '样品ID']
            for idx in range(max_results):
                suffix = f"_结果{idx+1}" if max_results > 1 else ""
                for col_name in col_names:
                    if col_name not in ['日期', '样品ID']:
                        new_col_names.append(f"{col_name}{suffix}")
                if idx < max_results - 1:
                    new_col_names.append("")
                    new_col_names.append("")

            df = pd.DataFrame(expanded_rows, columns=new_col_names)
            df.to_excel(output_path, index=False, sheet_name='结果')
            self._log(f"已导出到: {output_path}")
            return True

        # 配对模式
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

    def export_errors(self, output_path):
        if not self.errors and not self.warnings:
            self._log("没有错误或警告可导出")
            return False
        error_rows = []
        for e in self.errors:
            error_rows.append({
                '类型': '错误',
                '时间': e.get('timestamp', ''),
                '样品ID': e.get('sample_id', ''),
                '文件路径': e.get('file_path', ''),
                '参数': e.get('param_id', ''),
                '信息': e.get('message', '')
            })
        for w in self.warnings:
            error_rows.append({
                '类型': '警告',
                '时间': w.get('timestamp', ''),
                '样品ID': w.get('sample_id', ''),
                '文件路径': w.get('file_path', ''),
                '参数': w.get('param_id', ''),
                '信息': w.get('message', '')
            })
        df = pd.DataFrame(error_rows)
        df.to_excel(output_path, index=False, sheet_name='错误日志')
        self._log(f"错误日志已导出到: {output_path}")
        return True

    def get_stats(self):
        return self.stats

    def get_results(self):
        return self.results

    def get_errors(self):
        return self.errors

    def get_warnings(self):
        return self.warnings