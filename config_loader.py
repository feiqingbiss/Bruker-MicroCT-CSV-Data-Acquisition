# -*- coding: utf-8 -*-
"""
配置加载模块 - 使用 _trab / _cort / _2D / _3D 组合唯一参数ID
"""

import os
import pandas as pd


class ConfigLoader:
    def __init__(self, config_path=None):
        self.config_path = config_path
        self.param_defs = {}
        self.extract_rules = {}
        self.calc_params = {}
        self.template_def = []
        self.template_names = []
        self.path_rules = {}
        self.gray_unit_config = {}
        self._loaded = False

    def load(self, config_path=None):
        if config_path:
            self.config_path = config_path
        if not self.config_path or not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        try:
            xl = pd.ExcelFile(self.config_path)
            if 'ParamDef' in xl.sheet_names:
                df = pd.read_excel(self.config_path, sheet_name='ParamDef')
                for _, row in df.iterrows():
                    pid = str(row['参数ID']).strip()
                    self.param_defs[pid] = {
                        'full_name': str(row.get('完整名称', '')).strip(),
                        'csv_column': str(row.get('CSV列名', '')).strip(),
                        'alias': [a.strip() for a in str(row.get('别名', '')).split(',') if a.strip()],
                        'unit': str(row.get('单位', '')).strip(),
                        'data_type': str(row.get('数据类型', 'float')).strip(),
                        'source': str(row.get('来源段', '')).strip(),
                    }
            if 'ExtractRules' in xl.sheet_names:
                df = pd.read_excel(self.config_path, sheet_name='ExtractRules')
                for _, row in df.iterrows():
                    rid = str(row['指令ID']).strip()
                    self.extract_rules[rid] = {
                        'param_id': str(row['参数ID']).strip(),
                        'source': str(row['来源段']).strip(),
                        'unit': str(row.get('单位', '')).strip(),
                        'data_type': str(row.get('数据类型', 'float')).strip(),
                        'extract_type': str(row.get('提取方式', 'direct')).strip(),
                        'offset': int(row.get('偏移量', 0)) if pd.notna(row.get('偏移量', 0)) else 0,
                    }
            if 'CalcParams' in xl.sheet_names:
                df = pd.read_excel(self.config_path, sheet_name='CalcParams')
                for _, row in df.iterrows():
                    cid = str(row['参数ID']).strip()
                    self.calc_params[cid] = {
                        'display_name': str(row.get('显示名称', '')).strip(),
                        'formula': str(row.get('计算公式', '')).strip(),
                        'unit': str(row.get('单位', '')).strip(),
                        'data_type': str(row.get('数据类型', 'float')).strip(),
                    }
            if 'TemplateDef' in xl.sheet_names:
                df = pd.read_excel(self.config_path, sheet_name='TemplateDef')
                df = df.sort_values('顺序')
                self.template_names = df['模板名称'].unique().tolist()
                for _, row in df.iterrows():
                    self.template_def.append({
                        'column_name': str(row['列名']).strip(),
                        'extract_id': str(row['提取指令']).strip(),
                        'order': int(row['顺序']),
                        'template': str(row.get('模板名称', '默认')).strip(),
                    })
            if 'PathRules' in xl.sheet_names:
                df = pd.read_excel(self.config_path, sheet_name='PathRules')
                for _, row in df.iterrows():
                    self.path_rules[str(row['配置项']).strip()] = str(row['值']).strip()
            if 'GrayUnitConfig' in xl.sheet_names:
                df = pd.read_excel(self.config_path, sheet_name='GrayUnitConfig')
                for _, row in df.iterrows():
                    self.gray_unit_config[str(row['配置项']).strip()] = str(row['值']).strip()
            self._loaded = True
            return True
        except Exception as e:
            raise Exception(f"配置文件加载失败: {e}")

    def get_template_columns(self, template_name='默认'):
        return [col for col in self.template_def if col['template'] == template_name]

    def get_extract_rule(self, rule_id):
        return self.extract_rules.get(rule_id)

    def get_param_def(self, param_id):
        return self.param_defs.get(param_id)

    def get_calc_param(self, param_id):
        return self.calc_params.get(param_id)

    def is_loaded(self):
        return self._loaded


def generate_default_config(path):
    """生成默认配置文件（不含 DA / DA_ratio）"""

    all_params = [
        ('TAr', 'Tissue area', 'T.Ar', 'um^2'),
        ('BAr', 'Bone area', 'B.Ar', 'um^2'),
        ('TPm', 'Tissue perimeter', 'T.Pm', 'um'),
        ('BPm', 'Bone perimeter', 'B.Pm', 'um'),
        ('Po_cl', 'Closed porosity', 'Po(cl)', '%'),
        ('Po_tot', 'Total porosity', 'Po(tot)', '%'),
        ('TV', 'Tissue volume', 'TV', 'um^3'),
        ('BV', 'Bone volume', 'BV', 'um^3'),
        ('BVTV', 'Percent bone volume', 'BV/TV', '%'),
        ('BSBV', 'Bone surface/volume', 'BS/BV', '1/um'),
        ('TbTh', 'Trabecular thickness', 'Tb.Th', 'um'),
        ('TbSp', 'Trabecular separation', 'Tb.Sp', 'um'),
        ('TbN', 'Trabecular number', 'Tb.N', '1/um'),
        ('BMD', 'BMD', 'BMD', 'g/cm3'),
    ]

    with pd.ExcelWriter(path, engine='openpyxl') as writer:

        param_def_rows = []
        for pid, name, col, unit in all_params:
            param_def_rows.append({
                '参数ID': pid,
                '完整名称': name,
                'CSV列名': col,
                '别名': '',
                '单位': unit,
                '数据类型': 'float',
                '来源段': '2D' if pid in ['TAr', 'BAr', 'TPm', 'BPm', 'Po_cl', 'Po_tot'] else '3D'
            })
        pd.DataFrame(param_def_rows).to_excel(writer, sheet_name='ParamDef', index=False)

        extract_rows = []

        for pid in ['TV', 'BV', 'BVTV', 'BSBV', 'TbTh', 'TbSp', 'TbN']:
            extract_rows.append({'指令ID': f'{pid}_trab_3D', '参数ID': pid, '来源段': '3D',
                                 '单位': '', '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})

        for pid in ['TV', 'BV', 'BVTV', 'BSBV', 'TbTh', 'TbSp', 'TbN', 'Po_cl', 'Po_tot']:
            extract_rows.append({'指令ID': f'{pid}_cort_3D', '参数ID': pid, '来源段': '3D',
                                 '单位': '', '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})

        for pid in ['TAr', 'BAr', 'TPm', 'BPm']:
            extract_rows.append({'指令ID': f'{pid}_cort_2D', '参数ID': pid, '来源段': '2D',
                                 '单位': '', '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})

        extract_rows.append({'指令ID': 'BMD_trab_H', '参数ID': 'BMD', '来源段': 'Histogram',
                             '单位': 'g/cm3', '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})
        extract_rows.append({'指令ID': 'BMD_cort_H', '参数ID': 'BMD', '来源段': 'Histogram',
                             '单位': 'g/cm3', '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})

        pd.DataFrame(extract_rows).to_excel(writer, sheet_name='ExtractRules', index=False)

        calc_params = pd.DataFrame([
            {'参数ID': 'BAr_calc', '显示名称': 'Bone area (calc)',
             '计算公式': '{TAr_cort_2D} - {BAr_cort_2D}', '单位': 'um^2', '数据类型': 'float'},
            {'参数ID': 'BArRatio_calc', '显示名称': 'Bone area ratio',
             '计算公式': '({BAr_calc} / {TAr_cort_2D}) * 100', '单位': '%', '数据类型': 'float'},
        ])
        calc_params.to_excel(writer, sheet_name='CalcParams', index=False)

        template_def = pd.DataFrame([
            {'模板名称': '标准模板', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1},
            {'模板名称': '标准模板', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2},
            {'模板名称': '标准模板', '列名': '股骨', '提取指令': 'FEMUR_META', '顺序': 3},
            {'模板名称': '标准模板', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 4},
            {'模板名称': '标准模板', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 5},
            {'模板名称': '标准模板', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 6},
            {'模板名称': '标准模板', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 7},
            {'模板名称': '标准模板', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 8},
            {'模板名称': '标准模板', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 9},
            {'模板名称': '标准模板', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 10},
            {'模板名称': '标准模板', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 11},
            {'模板名称': '标准模板', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_cort_H', '顺序': 12},
            {'模板名称': '标准模板', '列名': 'BV/TV(%)', '提取指令': 'BVTV_cort_3D', '顺序': 13},
            {'模板名称': '标准模板', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_cort_3D', '顺序': 14},
            {'模板名称': '标准模板', '列名': 'Ct.Th (um)', '提取指令': 'TbTh_cort_3D', '顺序': 15},
            {'模板名称': '标准模板', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_cort_3D', '顺序': 16},
            {'模板名称': '标准模板', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_cort_3D', '顺序': 17},
            {'模板名称': '标准模板', '列名': 'T.Ar(um^2)', '提取指令': 'TAr_cort_2D', '顺序': 18},
            {'模板名称': '标准模板', '列名': 'B.Ar(um^2)', '提取指令': 'BAr_calc', '顺序': 19},
            {'模板名称': '标准模板', '列名': 'M.Ar(um^2)', '提取指令': 'BAr_cort_2D', '顺序': 20},
            {'模板名称': '标准模板', '列名': 'B.Ar/T.Ar(%)', '提取指令': 'BArRatio_calc', '顺序': 21},
            {'模板名称': '标准模板', '列名': 'T.Pm(um)', '提取指令': 'TPm_cort_2D', '顺序': 22},
            {'模板名称': '标准模板', '列名': 'M.Pm(um)', '提取指令': 'BPm_cort_2D', '顺序': 23},
        ])
        template_def.to_excel(writer, sheet_name='TemplateDef', index=False)

        pd.DataFrame([
            {'配置项': 'ID提取方式', '值': 'parent_folder_file_prefix'},
            {'配置项': '日期提取方式', '值': 'csv_header'},
        ]).to_excel(writer, sheet_name='PathRules', index=False)

        pd.DataFrame([
            {'配置项': '默认灰度单位', '值': 'BMD'},
        ]).to_excel(writer, sheet_name='GrayUnitConfig', index=False)
