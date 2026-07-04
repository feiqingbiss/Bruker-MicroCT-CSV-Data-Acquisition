# -*- coding: utf-8 -*-
"""
配置加载模块 - 包含全部2D/3D参数以及多种直方图参数（BMD/Index/HU/Attenuation）
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
                self.param_defs = {}
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
                self.extract_rules = {}
                for _, row in df.iterrows():
                    rid = str(row['指令ID']).strip()
                    if not rid:
                        continue
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
                df = df.sort_values(['模板名称', '顺序'])
                self.template_names = df['模板名称'].unique().tolist()
                self.template_def = []
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
    """生成默认配置文件，包含全部2D/3D参数以及多种直方图参数"""

    # ---- 完整的2D参数（37个） ----
    params_2d = [
        ('PosZ', 'Z position', 'Pos.Z', 'um'),
        ('ObjN', 'Number of objects', 'Obj.N', ''),
        ('TAr', 'Tissue area', 'T.Ar', 'um^2'),
        ('BAr', 'Bone area', 'B.Ar', 'um^2'),
        ('BArRatio', 'Percent bone area', 'B.Ar/T.Ar', '%'),
        ('TPm', 'Tissue perimeter', 'T.Pm', 'um'),
        ('BPm', 'Bone perimeter', 'B.Pm', 'um'),
        ('BPmBAr', 'Bone perimeter/area', 'B.Pm/B.Ar', '1/um'),
        ('AvObjAr', 'Average object area', 'Av.Obj.Ar', 'um^2'),
        ('AvObjECDa', 'Avg obj equiv circle diameter', 'Av.Obj.ECDa', 'um'),
        ('TbPf', 'Trabecular pattern factor', 'Tb.Pf', '1/um'),
        ('EuN', 'Euler number', 'Eu.N', ''),
        ('PoNcl', 'Number of closed pores', 'Po.N(cl)', ''),
        ('PoArcl', 'Area of closed pores', 'Po.Ar(cl)', 'um^2'),
        ('PoPmcl', 'Perimeter of closed pores', 'Po.Pm(cl)', 'um'),
        ('Po_cl', 'Closed porosity', 'Po(cl)', '%'),
        ('PoArop', 'Area of open pore space', 'Po.Ar(op)', 'um^2'),
        ('PoArtot', 'Total area of pore space', 'Po.Ar(tot)', 'um^2'),
        ('Po_op', 'Open porosity', 'Po(op)', '%'),
        ('Po_tot', 'Total porosity', 'Po(tot)', '%'),
        ('CrdX', 'Centroid (x)', 'Crd.X', 'um'),
        ('CrdY', 'Centroid (y)', 'Crd.Y', 'um'),
        ('MMIx', 'Moment of inertia (x)', 'MMI(x)', 'um^4'),
        ('MMIy', 'Moment of inertia (y)', 'MMI(y)', 'um^4'),
        ('MMIpolar', 'Polar moment of inertia', 'MMI(polar)', 'um^4'),
        ('GrRx', 'Radius of gyration (x)', 'Gr.R(x)', 'um'),
        ('GrRy', 'Radius of gyration (y)', 'Gr.R(y)', 'um'),
        ('GrRpolar', 'Polar radius of gyration', 'Gr.R(polar)', 'um'),
        ('PrInxy', 'Product of inertia (xy)', 'Pr.In(xy)', 'um^4'),
        ('MMImax', 'Principal moment of inertia (max)', 'MMI(max)', 'um^4'),
        ('MMImin', 'Principal moment of inertia (min)', 'MMI(min)', 'um^4'),
        ('TOrphi', 'Total orientation (phi)', 'T.Or(phi)', '°'),
        ('Ecc', 'Eccentricity', 'Ecc', ''),
        ('TbThpl', 'Trabecular thickness (plate)', 'Tb.Th(pl)', 'um'),
        ('TbSppl', 'Trabecular separation (plate)', 'Tb.Sp(pl)', 'um'),
        ('TbNpl', 'Trabecular number (plate)', 'Tb.N(pl)', '1/um'),
        ('FD', 'Fractal dimension', 'FD', ''),
        ('iPm', 'Intersection perimeter', 'i.Pm', 'um'),
    ]

    # ---- 完整的3D参数（含 DA/DA_ratio） ----
    params_3d = [
        ('TV', 'Tissue volume', 'TV', 'um^3'),
        ('BV', 'Bone volume', 'BV', 'um^3'),
        ('BVTV', 'Percent bone volume', 'BV/TV', '%'),
        ('TS', 'Tissue surface', 'TS', 'um^2'),
        ('BS', 'Bone surface', 'BS', 'um^2'),
        ('iS', 'Intersection surface', 'i.S', 'um^2'),
        ('BSBV', 'Bone surface/volume', 'BS/BV', '1/um'),
        ('BSTV', 'Bone surface density', 'BS/TV', '1/um'),
        ('TbTh', 'Trabecular thickness', 'Tb.Th', 'um'),
        ('TbSp', 'Trabecular separation', 'Tb.Sp', 'um'),
        ('TbN', 'Trabecular number', 'Tb.N', '1/um'),
        ('TbPf3D', 'Trabecular pattern factor', 'Tb.Pf', '1/um'),
        ('CrdX3D', 'Centroid (x)', 'Crd.X', 'um'),
        ('CrdY3D', 'Centroid (y)', 'Crd.Y', 'um'),
        ('CrdZ3D', 'Centroid (z)', 'Crd.Z', 'um'),
        ('SMI', 'Structure model index', 'SMI', ''),
        ('DA', 'Degree of anisotropy', 'DA', ''),
        ('DA_ratio', 'Degree of anisotropy (ratio)', 'DA', ''),  # csv_column 设为 DA
        ('FD3D', 'Fractal dimension', 'FD', ''),
        ('ObjN3D', 'Number of objects', 'Obj.N', ''),
        ('PoNcl3D', 'Number of closed pores', 'Po.N(cl)', ''),
        ('PoVcl', 'Volume of closed pores', 'Po.V(cl)', 'um^3'),
        ('PoScl', 'Surface of closed pores', 'Po.S(cl)', 'um^2'),
        ('PoVop', 'Volume of open pore space', 'Po.V(op)', 'um^3'),
        ('Po_op3D', 'Open porosity', 'Po(op)', '%'),
        ('PoVtot', 'Total volume of pore space', 'Po.V(tot)', 'um^3'),
        ('Po_cl', 'Closed porosity', 'Po(cl)', '%'),
        ('Po_tot', 'Total porosity', 'Po(tot)', '%'),
        ('EuN3D', 'Euler number', 'Eu.N', ''),
        ('Conn', 'Connectivity', 'Conn', ''),
        ('ConnDn', 'Connectivity density', 'Conn.Dn', '1/um^3'),
        ('SDTbTh', 'SD trabecular thickness', 'SD(Tb.Th)', 'um'),
        ('SDTbSp', 'SD trabecular separation', 'SD(Tb.Sp)', 'um'),
        ('MMIx3D', 'Moment of inertia (x)', 'MMI(x)', 'um^5'),
        ('MMIy3D', 'Moment of inertia (y)', 'MMI(y)', 'um^5'),
        ('MMIz3D', 'Moment of inertia (z)', 'MMI(z)', 'um^5'),
        ('MMIpolar3D', 'Polar moment of inertia', 'MMI(polar)', 'um^5'),
        ('GrRx3D', 'Radius of gyration (x)', 'Gr.R(x)', 'um'),
        ('GrRy3D', 'Radius of gyration (y)', 'Gr.R(y)', 'um'),
        ('GrRz3D', 'Radius of gyration (z)', 'Gr.R(z)', 'um'),
        ('GrRpolar3D', 'Polar radius of gyration', 'Gr.R(polar)', 'um'),
        ('PrInxy3D', 'Product of inertia (xy)', 'Pr.In(xy)', 'um^5'),
        ('PrInxz3D', 'Product of inertia (xz)', 'Pr.In(xz)', 'um^5'),
        ('PrInyz3D', 'Product of inertia (yz)', 'Pr.In(yz)', 'um^5'),
    ]

    # ---- 直方图参数（多种单位） ----
    params_hist = [
        ('BMD', 'BMD', 'BMD', 'g/cm3'),
        ('Index', 'Index', 'Index', ''),
        ('HU', 'HU', 'HU', 'HU'),
        ('Attenuation', 'Attenuation', 'Attenuation', ''),
    ]

    with pd.ExcelWriter(path, engine='openpyxl') as writer:

        # ---- ParamDef ----
        param_def_rows = []
        for pid, name, col, unit in params_2d:
            param_def_rows.append({
                '参数ID': pid,
                '完整名称': name,
                'CSV列名': col,
                '别名': '',
                '单位': unit,
                '数据类型': 'float',
                '来源段': '2D'
            })
        for pid, name, col, unit in params_3d:
            alias = 'Degree of anisotropy (math)' if pid == 'DA_ratio' else ''
            param_def_rows.append({
                '参数ID': pid,
                '完整名称': name,
                'CSV列名': col,
                '别名': alias,
                '单位': unit,
                '数据类型': 'float',
                '来源段': '3D'
            })
        for pid, name, col, unit in params_hist:
            param_def_rows.append({
                '参数ID': pid,
                '完整名称': name,
                'CSV列名': col,
                '别名': '',
                '单位': unit,
                '数据类型': 'float',
                '来源段': 'Histogram'
            })
        pd.DataFrame(param_def_rows).to_excel(writer, sheet_name='ParamDef', index=False)

        # ---- ExtractRules ----
        extract_rows = []

        # 松质骨 3D (_trab_3D)
        for pid, name, col, unit in params_3d:
            extract_rows.append({
                '指令ID': f'{pid}_trab_3D',
                '参数ID': pid,
                '来源段': '3D',
                '单位': unit,
                '数据类型': 'float',
                '提取方式': 'direct',
                '偏移量': 0
            })

        # 皮质骨 3D (_cort_3D)
        for pid, name, col, unit in params_3d:
            extract_rows.append({
                '指令ID': f'{pid}_cort_3D',
                '参数ID': pid,
                '来源段': '3D',
                '单位': unit,
                '数据类型': 'float',
                '提取方式': 'direct',
                '偏移量': 0
            })

        # 皮质骨 2D (_cort_2D)
        for pid, name, col, unit in params_2d:
            extract_rows.append({
                '指令ID': f'{pid}_cort_2D',
                '参数ID': pid,
                '来源段': '2D',
                '单位': unit,
                '数据类型': 'float',
                '提取方式': 'direct',
                '偏移量': 0
            })

        # ---- 直方图参数（松质/皮质各自独立） ----
        for pid, name, col, unit in params_hist:
            extract_rows.append({
                '指令ID': f'{pid}_trab_H',
                '参数ID': pid,
                '来源段': 'Histogram',
                '单位': unit,
                '数据类型': 'float',
                '提取方式': 'direct',
                '偏移量': 0
            })
            extract_rows.append({
                '指令ID': f'{pid}_cort_H',
                '参数ID': pid,
                '来源段': 'Histogram',
                '单位': unit,
                '数据类型': 'float',
                '提取方式': 'direct',
                '偏移量': 0
            })

        pd.DataFrame(extract_rows).to_excel(writer, sheet_name='ExtractRules', index=False)

        # ---- CalcParams ----
        calc_params = pd.DataFrame([
            {'参数ID': 'BAr_calc', '显示名称': 'Bone area (calc)',
             '计算公式': '{TAr_cort_2D} - {BAr_cort_2D}', '单位': 'um^2', '数据类型': 'float'},
            {'参数ID': 'BArRatio_calc', '显示名称': 'Bone area ratio',
             '计算公式': '({BAr_calc} / {TAr_cort_2D}) * 100', '单位': '%', '数据类型': 'float'},
        ])
        calc_params.to_excel(writer, sheet_name='CalcParams', index=False)

        # ---- TemplateDef（标准模板 + 单品模板） ----
        template_def_rows = [
            # 模板1：标准模板（长骨专用，松质+皮质）
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 3},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 4},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 5},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 6},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 7},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 8},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 9},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 10},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_cort_H', '顺序': 11},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV/TV(%)', '提取指令': 'BVTV_cort_3D', '顺序': 12},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_cort_3D', '顺序': 13},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Ct.Th (um)', '提取指令': 'TbTh_cort_3D', '顺序': 14},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_cort_3D', '顺序': 15},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_cort_3D', '顺序': 16},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'T.Ar(um^2)', '提取指令': 'TAr_cort_2D', '顺序': 17},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'B.Ar(um^2)', '提取指令': 'BAr_calc', '顺序': 18},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'M.Ar(um^2)', '提取指令': 'BAr_cort_2D', '顺序': 19},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'B.Ar/T.Ar(%)', '提取指令': 'BArRatio_calc', '顺序': 20},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'T.Pm(um)', '提取指令': 'TPm_cort_2D', '顺序': 21},
            {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'M.Pm(um)', '提取指令': 'BPm_cort_2D', '顺序': 22},
            # 模板2：单品模板（全部3D参数 + 直方图，无2D）
            {'模板名称': '通用模板（直接提取参数）', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1},
            {'模板名称': '通用模板（直接提取参数）', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 3},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 4},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 5},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 6},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 7},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 8},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 9},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 10},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Po.N(cl)', '提取指令': 'PoNcl3D_trab_3D', '顺序': 11},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Po.V(cl)(um3)', '提取指令': 'PoVcl_trab_3D', '顺序': 12},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Po.S(cl)(um2)', '提取指令': 'PoScl_trab_3D', '顺序': 13},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_trab_3D', '顺序': 14},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Po.V(op)(um3)', '提取指令': 'PoVop_trab_3D', '顺序': 15},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Po(op)(%)', '提取指令': 'Po_op3D_trab_3D', '顺序': 16},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Po.V(tot)(um3)', '提取指令': 'PoVtot_trab_3D', '顺序': 17},
            {'模板名称': '通用模板（直接提取参数）', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_trab_3D', '顺序': 18},
        ]

        template_def = pd.DataFrame(template_def_rows)
        template_def.to_excel(writer, sheet_name='TemplateDef', index=False)

        # ---- PathRules ----
        pd.DataFrame([
            {'配置项': 'ID提取方式', '值': 'parent_folder_file_prefix'},
            {'配置项': '日期提取方式', '值': 'csv_header'},
        ]).to_excel(writer, sheet_name='PathRules', index=False)

        # ---- GrayUnitConfig ----
        pd.DataFrame([
            {'配置项': '默认灰度单位', '值': 'BMD'},
        ]).to_excel(writer, sheet_name='GrayUnitConfig', index=False)
