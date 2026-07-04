# -*- coding: utf-8 -*-
"""
数据处理核心模块 - 支持两种模式
1. 标准模板（长骨专用）区分松质骨皮质骨参数：松质+皮质配对
2. 通用模板（直接提取参数）：每个CSV独立提取，不配对
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

        # 判断是否为通用模板模式（直接提取参数，不配对）
        self.is_single_mode = ('通用模板' in template_name)

        self.samples = defaultdict(list)
        self.results = []
        self.errors = []
        self.warnings = []
        self.stats = {'total': 0, 'success': 0, 'skipped': 0, 'warning': 0, 'error': 0}
        self._stop_flag = False

    def _log(self, msg, tag='info'):
        if self.log_callback:
            self.log_callback(msg, tag) if tag else self.log_callback(msg)

    def _add_error(self, sample_id, file_path, param_id, message):
        self.errors.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sample_id': sample_id,
            'file_path': file_path,
            'param_id': param_id,
            'message': message
        })
        self.stats['error'] += 1

    def _add_warning(self, sample_id, file_path, message, param_id=''):
        self.warnings.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sample_id': sample_id,
            'file_path': file_path,
            'param_id': param_id,
            'message': message
        })
        self.stats['warning'] += 1

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

            # 单品模板模式：用相对路径作为样品ID（避免同名文件冲突）
            if self.is_single_mode:
                # 使用相对于根目录的路径作为唯一标识
                rel_path = os.path.relpath(file_path, self.root_dir)
                sample_id = rel_path.replace(os.sep, '_').replace('.csv', '')
                if len(sample_id) > 80:
                    sample_id = sample_id[:80]
            else:
                # 标准模板模式：从路径提取样品ID
                sample_id = extract_sample_id(file_path, id_method)
                if not sample_id:
                    self._log(f"警告: 无法提取样品ID: {file_path}", 'warning')
                    self._add_warning('unknown', file_path, f"无法提取样品ID: {file_path}")
                    continue

            # 单品模板模式：不区分松质/皮质，统一为 'single'
            if self.is_single_mode:
                file_type = 'single'
            else:
                file_type = 'cortical' if sections['has_2d'] else 'trabecular'

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

            if self.is_single_mode:
                self._log(f"处理样品: {sample_id} (文件数: {len(files)})")
                for file_info in files:
                    parser = file_info['parser']
                    self._extract_row_data_single(sample_id, parser)
            else:
                # 标准模板模式：配对处理
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

        self._log(f"处理完成: 成功 {self.stats['success']}, 跳过 {self.stats['skipped']}, "
                  f"警告 {self.stats['warning']}, 错误 {self.stats['error']}")

    def _extract_row_data_single(self, sample_id, parser):
        """★ 单品模板模式：单个CSV独立提取"""
        row_data = {
            'DATE_META': parser.get_date() if parser else None,
            'SAMPLE_ID_META': sample_id,
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
                self._add_warning(
                    sample_id,
                    parser.file_path if parser else '',
                    f"未知提取指令: {extract_id}",
                    extract_id
                )
                continue

            source = rule['source']
            param_id = rule['param_id']
            value = None

            if source == '3D':
                value = parser.extract_3d_value(param_id)
            elif source == '2D':
                value = parser.extract_2d_value(param_id)
            elif source == 'Histogram':
                value = parser.extract_histogram_value('BMD')
                if value is None:
                    self._add_warning(
                        sample_id,
                        parser.file_path if parser else '',
                        f"直方图 BMD 提取失败: {extract_id} 返回 None",
                        extract_id
                    )
            else:
                value = None

            extracted_values[extract_id] = value

            if self.verbose:
                status = '✓' if value is not None else '✗'
                self._log(f"      {status} {extract_id} ← {source} = {value}", 'detail')

            if value is None and source != 'Histogram':
                self._add_error(
                    sample_id,
                    parser.file_path if parser else '',
                    extract_id,
                    f"提取失败: {extract_id} 返回 None"
                )

        # 计算参数
        for col_def in columns:
            extract_id = col_def['extract_id']
            if extract_id in self.config.calc_params:
                calc_result = self._calc_param_single(extract_id, extracted_values, sample_id, parser)
                extracted_values[extract_id] = calc_result
                if self.verbose:
                    status = '✓' if calc_result is not None else '✗'
                    self._log(f"      [计算] {extract_id} {status} = {calc_result}", 'detail')

        for extract_id, value in extracted_values.items():
            row_data[extract_id] = value

        self.results.append(row_data)

        extracted_count = sum(1 for v in extracted_values.values() if v is not None)
        failed_count = len(extracted_values) - extracted_count
        self._log(f"  ✅ 提取汇总: ✓ {extracted_count} 个参数, ✗ {failed_count} 个参数缺失",
                  'success' if failed_count == 0 else 'warning')

    def _calc_param_single(self, calc_id, extracted_values, sample_id, parser):
        """单品模式的计算参数"""
        calc_def = self.config.get_calc_param(calc_id)
        if not calc_def:
            self._add_warning(
                sample_id,
                parser.file_path if parser else '',
                f"计算参数定义缺失: {calc_id}",
                calc_id
            )
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
            self._add_warning(
                sample_id,
                parser.file_path if parser else '',
                f"计算参数 {calc_id} 依赖缺失: {', '.join(missing)}",
                calc_id
            )
            return None

        expr = formula
        for ph in placeholders:
            if deps.get(ph) is None:
                return None
            expr = expr.replace(f'{{{ph}}}', str(deps[ph]))
        try:
            return eval(expr)
        except Exception as e:
            self._add_error(
                sample_id,
                parser.file_path if parser else '',
                calc_id,
                f"计算失败: {calc_id} - {e}"
            )
            return None

    def _extract_row_data_pair(self, sample_id, trab_parser, cort_parser):
        """★ 标准模板模式：松质+皮质配对提取"""
        parser = trab_parser or cort_parser
        row_data = {
            'DATE_META': parser.get_date() if parser else None,
            'SAMPLE_ID_META': sample_id,
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
                self._add_warning(
                    sample_id,
                    parser.file_path if parser else '',
                    f"未知提取指令: {extract_id}",
                    extract_id
                )
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
                        if value is None:
                            self._add_warning(
                                sample_id,
                                trab_parser.file_path,
                                f"直方图 BMD 提取失败: {extract_id}",
                                extract_id
                            )
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
                        if value is None:
                            self._add_warning(
                                sample_id,
                                cort_parser.file_path,
                                f"直方图 BMD 提取失败: {extract_id}",
                                extract_id
                            )
                else:
                    value = None
            else:
                value = None

            extracted_values[extract_id] = value

            if self.verbose:
                status = '✓' if value is not None else '✗'
                src = '松质' if '_trab_' in extract_id else '皮质' if '_cort_' in extract_id else '未知'
                self._log(f"      {status} {extract_id} ← {src} = {value}", 'detail')

            if value is None and source != 'Histogram':
                file_path = ''
                if '_trab_' in extract_id and trab_parser:
                    file_path = trab_parser.file_path
                elif '_cort_' in extract_id and cort_parser:
                    file_path = cort_parser.file_path
                self._add_error(
                    sample_id,
                    file_path,
                    extract_id,
                    f"提取失败: {extract_id} 返回 None"
                )

        # 计算参数
        for col_def in columns:
            extract_id = col_def['extract_id']
            if extract_id in self.config.calc_params:
                calc_result = self._calc_param_pair(extract_id, extracted_values, sample_id, parser)
                extracted_values[extract_id] = calc_result
                if self.verbose:
                    status = '✓' if calc_result is not None else '✗'
                    self._log(f"      [计算] {extract_id} {status} = {calc_result}", 'detail')

        for extract_id, value in extracted_values.items():
            row_data[extract_id] = value

        self.results.append(row_data)

        extracted_count = sum(1 for v in extracted_values.values() if v is not None)
        failed_count = len(extracted_values) - extracted_count
        self._log(f"  ✅ 提取汇总: ✓ {extracted_count} 个参数, ✗ {failed_count} 个参数缺失",
                  'success' if failed_count == 0 else 'warning')

    def _calc_param_pair(self, calc_id, extracted_values, sample_id, parser):
        """配对模式的计算参数"""
        calc_def = self.config.get_calc_param(calc_id)
        if not calc_def:
            self._add_warning(
                sample_id,
                parser.file_path if parser else '',
                f"计算参数定义缺失: {calc_id}",
                calc_id
            )
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
            self._add_warning(
                sample_id,
                parser.file_path if parser else '',
                f"计算参数 {calc_id} 依赖缺失: {', '.join(missing)}",
                calc_id
            )
            return None

        expr = formula
        for ph in placeholders:
            if deps.get(ph) is None:
                return None
            expr = expr.replace(f'{{{ph}}}', str(deps[ph]))
        try:
            return eval(expr)
        except Exception as e:
            self._add_error(
                sample_id,
                parser.file_path if parser else '',
                calc_id,
                f"计算失败: {calc_id} - {e}"
            )
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
