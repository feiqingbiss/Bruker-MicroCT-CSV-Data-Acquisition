# -*- coding: utf-8 -*-
"""
配置加载模块 v3.2
内置三个默认模板，可从 Excel 加载自定义模板（合并覆盖内置同名模板）
支持版本校验，自动更新配置
"""

import os
import pandas as pd
import numpy as np

# 当前软件配置文件版本号
CONFIG_VERSION = "3.2"


def get_default_config_data():
    """返回默认配置的字典，包含所有工作表数据"""
    # 2D参数（37个）
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

    # 3D参数
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
        ('DA_ratio', 'Degree of anisotropy (ratio)', 'DA', ''),
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

    # 直方图参数
    params_hist = [
        ('BMD', 'BMD', 'BMD', 'g/cm3'),
        ('Index', 'Index', 'Index', ''),
        ('HU', 'HU', 'HU', 'HU'),
        ('Attenuation', 'Attenuation', 'Attenuation', ''),
    ]

    # 构建各工作表
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
    df_param_def = pd.DataFrame(param_def_rows)

    extract_rows = []
    for pid, name, col, unit in params_3d:
        extract_rows.append({'指令ID': f'{pid}_trab_3D', '参数ID': pid, '来源段': '3D', '单位': unit, '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})
        extract_rows.append({'指令ID': f'{pid}_cort_3D', '参数ID': pid, '来源段': '3D', '单位': unit, '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})
    for pid, name, col, unit in params_2d:
        extract_rows.append({'指令ID': f'{pid}_cort_2D', '参数ID': pid, '来源段': '2D', '单位': unit, '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})
    for pid, name, col, unit in params_hist:
        extract_rows.append({'指令ID': f'{pid}_trab_H', '参数ID': pid, '来源段': 'Histogram', '单位': unit, '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})
        extract_rows.append({'指令ID': f'{pid}_cort_H', '参数ID': pid, '来源段': 'Histogram', '单位': unit, '数据类型': 'float', '提取方式': 'direct', '偏移量': 0})
    df_extract_rules = pd.DataFrame(extract_rows)

    df_calc_params = pd.DataFrame([
        {'参数ID': 'BAr_calc', '显示名称': 'Bone area (calc)', '计算公式': '{TAr_cort_2D} - {BAr_cort_2D}', '单位': 'um^2', '数据类型': 'float'},
        {'参数ID': 'BArRatio_calc', '显示名称': 'Bone area ratio', '计算公式': '({BAr_calc} / {TAr_cort_2D}) * 100', '单位': '%', '数据类型': 'float'},
    ])

    template_def_rows = [
        # 标准模板（长骨专用）
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 3, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 4, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 5, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 6, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 7, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 8, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 9, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 10, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_cort_H', '顺序': 11, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV/TV(%)', '提取指令': 'BVTV_cort_3D', '顺序': 12, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_cort_3D', '顺序': 13, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Ct.Th (um)', '提取指令': 'TbTh_cort_3D', '顺序': 14, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_cort_3D', '顺序': 15, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_cort_3D', '顺序': 16, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'T.Ar(um^2)', '提取指令': 'TAr_cort_2D', '顺序': 17, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'B.Ar(um^2)', '提取指令': 'BAr_calc', '顺序': 18, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'M.Ar(um^2)', '提取指令': 'BAr_cort_2D', '顺序': 19, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'B.Ar/T.Ar(%)', '提取指令': 'BArRatio_calc', '顺序': 20, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'T.Pm(um)', '提取指令': 'TPm_cort_2D', '顺序': 21, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'M.Pm(um)', '提取指令': 'BPm_cort_2D', '顺序': 22, '样品ID规则': ''},
        # 通用模板（一个样品CSV内多个ROI分析结果）
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 3, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 4, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 5, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 6, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 7, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 8, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 9, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 10, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.N(cl)', '提取指令': 'PoNcl3D_trab_3D', '顺序': 11, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.V(cl)(um3)', '提取指令': 'PoVcl_trab_3D', '顺序': 12, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.S(cl)(um2)', '提取指令': 'PoScl_trab_3D', '顺序': 13, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_trab_3D', '顺序': 14, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.V(op)(um3)', '提取指令': 'PoVop_trab_3D', '顺序': 15, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po(op)(%)', '提取指令': 'Po_op3D_trab_3D', '顺序': 16, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.V(tot)(um3)', '提取指令': 'PoVtot_trab_3D', '顺序': 17, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_trab_3D', '顺序': 18, '样品ID规则': ''},
        # 通用模板（一组样品不同部位、重复同名CSV）
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1, '样品ID规则': '{file_prefix}'},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 3, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 4, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 5, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 6, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 7, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 8, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 9, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 10, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.N(cl)', '提取指令': 'PoNcl3D_trab_3D', '顺序': 11, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.V(cl)(um3)', '提取指令': 'PoVcl_trab_3D', '顺序': 12, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.S(cl)(um2)', '提取指令': 'PoScl_trab_3D', '顺序': 13, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_trab_3D', '顺序': 14, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.V(op)(um3)', '提取指令': 'PoVop_trab_3D', '顺序': 15, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po(op)(%)', '提取指令': 'Po_op3D_trab_3D', '顺序': 16, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.V(tot)(um3)', '提取指令': 'PoVtot_trab_3D', '顺序': 17, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_trab_3D', '顺序': 18, '样品ID规则': ''},
    ]
    df_template_def = pd.DataFrame(template_def_rows)

    df_path_rules = pd.DataFrame([
        {'配置项': 'ID提取方式', '值': 'parent_folder_file_prefix'},
        {'配置项': '样品ID规则', '值': '{parent}_{file_prefix}'},
        {'配置项': '日期提取方式', '值': 'csv_header'},
    ])

    df_gray_unit_config = pd.DataFrame([
        {'配置项': '默认灰度单位', '值': 'BMD'},
    ])

    df_version = pd.DataFrame([{'版本': CONFIG_VERSION}])

    return {
        'ParamDef': df_param_def,
        'ExtractRules': df_extract_rules,
        'CalcParams': df_calc_params,
        'TemplateDef': df_template_def,
        'PathRules': df_path_rules,
        'GrayUnitConfig': df_gray_unit_config,
        'Version': df_version,
    }


def generate_default_config(path):
    """生成默认配置文件"""
    data = get_default_config_data()
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for sheet_name, df in data.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)


def update_config_if_needed(config_path):
    """
    检查配置文件版本，若不存在或版本不匹配则更新
    保留用户自定义模板（非内置）和 CalcParams
    """
    if not os.path.exists(config_path):
        generate_default_config(config_path)
        return True

    try:
        # 读取版本号
        version_df = pd.read_excel(config_path, sheet_name='Version')
        if version_df is not None and not version_df.empty:
            current_version = str(version_df.iloc[0, 0]).strip()
        else:
            current_version = ''

        if current_version != CONFIG_VERSION:
            # 备份用户自定义数据
            custom_templates = []
            calc_params_df = None
            try:
                template_df = pd.read_excel(config_path, sheet_name='TemplateDef')
                # 提取自定义模板（名称不在 BUILTIN_NAMES 中）
                builtin_names = ConfigLoader.BUILTIN_NAMES
                custom_templates = template_df[~template_df['模板名称'].isin(builtin_names)].to_dict('records')
            except Exception:
                pass
            try:
                calc_params_df = pd.read_excel(config_path, sheet_name='CalcParams')
            except Exception:
                pass

            # 生成新默认配置
            default_data = get_default_config_data()
            # 合并自定义模板
            if custom_templates:
                default_template_df = default_data['TemplateDef']
                custom_df = pd.DataFrame(custom_templates)
                default_template_df = pd.concat([default_template_df, custom_df], ignore_index=True)
                default_data['TemplateDef'] = default_template_df
            # 合并 CalcParams
            if calc_params_df is not None and not calc_params_df.empty:
                default_data['CalcParams'] = calc_params_df

            # 写入文件
            with pd.ExcelWriter(config_path, engine='openpyxl') as writer:
                for sheet_name, df in default_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            return True
    except Exception as e:
        # 如果读取失败，重新生成
        generate_default_config(config_path)
        return True
    return False


class ConfigLoader:
    # 内置三个默认模板定义（硬编码）
    BUILTIN_TEMPLATES = [
        # 标准模板（长骨专用）
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 3, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 4, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 5, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 6, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 7, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 8, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 9, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 10, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_cort_H', '顺序': 11, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BV/TV(%)', '提取指令': 'BVTV_cort_3D', '顺序': 12, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_cort_3D', '顺序': 13, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Ct.Th (um)', '提取指令': 'TbTh_cort_3D', '顺序': 14, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_cort_3D', '顺序': 15, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_cort_3D', '顺序': 16, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'T.Ar(um^2)', '提取指令': 'TAr_cort_2D', '顺序': 17, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'B.Ar(um^2)', '提取指令': 'BAr_calc', '顺序': 18, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'M.Ar(um^2)', '提取指令': 'BAr_cort_2D', '顺序': 19, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'B.Ar/T.Ar(%)', '提取指令': 'BArRatio_calc', '顺序': 20, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'T.Pm(um)', '提取指令': 'TPm_cort_2D', '顺序': 21, '样品ID规则': ''},
        {'模板名称': '标准模板（长骨专用）区分松质骨皮质骨参数', '列名': 'M.Pm(um)', '提取指令': 'BPm_cort_2D', '顺序': 22, '样品ID规则': ''},
        # 通用模板（一个样品CSV内多个ROI分析结果）
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 3, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 4, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 5, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 6, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 7, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 8, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 9, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 10, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.N(cl)', '提取指令': 'PoNcl3D_trab_3D', '顺序': 11, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.V(cl)(um3)', '提取指令': 'PoVcl_trab_3D', '顺序': 12, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.S(cl)(um2)', '提取指令': 'PoScl_trab_3D', '顺序': 13, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_trab_3D', '顺序': 14, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.V(op)(um3)', '提取指令': 'PoVop_trab_3D', '顺序': 15, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po(op)(%)', '提取指令': 'Po_op3D_trab_3D', '顺序': 16, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po.V(tot)(um3)', '提取指令': 'PoVtot_trab_3D', '顺序': 17, '样品ID规则': ''},
        {'模板名称': '通用模板（一个样品CSV内多个ROI分析结果）', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_trab_3D', '顺序': 18, '样品ID规则': ''},
        # 通用模板（一组样品不同部位、重复同名CSV）
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': '日期', '提取指令': 'DATE_META', '顺序': 1, '样品ID规则': '{file_prefix}'},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': '样品ID', '提取指令': 'SAMPLE_ID_META', '顺序': 2, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'BMD (g/cm3)', '提取指令': 'BMD_trab_H', '顺序': 3, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'TV(um3)', '提取指令': 'TV_trab_3D', '顺序': 4, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'BV(um3)', '提取指令': 'BV_trab_3D', '顺序': 5, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'BV/TV(%)', '提取指令': 'BVTV_trab_3D', '顺序': 6, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'BS/BV (1/um)', '提取指令': 'BSBV_trab_3D', '顺序': 7, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Tb.Th (um)', '提取指令': 'TbTh_trab_3D', '顺序': 8, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Tb.Sp (um)', '提取指令': 'TbSp_trab_3D', '顺序': 9, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Tb.N (1/um)', '提取指令': 'TbN_trab_3D', '顺序': 10, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.N(cl)', '提取指令': 'PoNcl3D_trab_3D', '顺序': 11, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.V(cl)(um3)', '提取指令': 'PoVcl_trab_3D', '顺序': 12, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.S(cl)(um2)', '提取指令': 'PoScl_trab_3D', '顺序': 13, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po(cl)(%)', '提取指令': 'Po_cl_trab_3D', '顺序': 14, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.V(op)(um3)', '提取指令': 'PoVop_trab_3D', '顺序': 15, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po(op)(%)', '提取指令': 'Po_op3D_trab_3D', '顺序': 16, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po.V(tot)(um3)', '提取指令': 'PoVtot_trab_3D', '顺序': 17, '样品ID规则': ''},
        {'模板名称': '通用模板（一组样品不同部位、重复同名CSV）', '列名': 'Po(tot)(%)', '提取指令': 'Po_tot_trab_3D', '顺序': 18, '样品ID规则': ''},
    ]

    BUILTIN_NAMES = set(row['模板名称'] for row in BUILTIN_TEMPLATES)

    def __init__(self, config_path=None):
        self.config_path = config_path
        self.param_defs = {}
        self.extract_rules = {}
        self.calc_params = {}
        self.template_def = []
        self.template_names = []
        self.path_rules = {}
        self.gray_unit_config = {}
        self.template_id_rules = {}
        self._loaded = False

    def load(self, config_path=None):
        if config_path:
            self.config_path = config_path

        # 1. 初始化内置模板
        self._load_builtin_templates()

        # 2. 如果配置文件存在，加载并合并
        if self.config_path and os.path.exists(self.config_path):
            try:
                xl = pd.ExcelFile(self.config_path)
                sheet_loaders = {
                    'ParamDef': self._load_param_def,
                    'ExtractRules': self._load_extract_rules,
                    'CalcParams': self._load_calc_params,
                    'TemplateDef': self._load_template_def_merge,
                    'PathRules': self._load_path_rules,
                    'GrayUnitConfig': self._load_gray_unit_config,
                }
                for sheet, loader in sheet_loaders.items():
                    if sheet in xl.sheet_names:
                        try:
                            loader(xl)
                        except Exception as e:
                            raise Exception(f"加载 {sheet} 工作表失败: {e}")
                self._loaded = True
            except Exception as e:
                # 如果加载失败，仍保留内置模板，记录日志
                print(f"警告: 加载配置文件失败，使用内置模板: {e}")
                self._loaded = False
        else:
            self._loaded = False

        return True

    def _load_builtin_templates(self):
        """加载内置默认模板"""
        self.template_def = []
        self.template_names = []
        self.template_id_rules = {}
        for row in self.BUILTIN_TEMPLATES:
            template = row['模板名称']
            self.template_def.append({
                'column_name': row['列名'],
                'extract_id': row['提取指令'],
                'order': row['顺序'],
                'template': template,
            })
            if template not in self.template_names:
                self.template_names.append(template)
            id_rule = row.get('样品ID规则', '').strip()
            if id_rule and id_rule.lower() != 'nan':
                self.template_id_rules[template] = id_rule

    def _load_template_def_merge(self, xl):
        """加载 Excel 中的 TemplateDef，合并到内置模板（覆盖同名）"""
        df = pd.read_excel(xl, sheet_name='TemplateDef')
        if '样品ID规则' not in df.columns:
            df['样品ID规则'] = ''
        df = df.sort_values(['模板名称', '顺序'])

        self._load_builtin_templates()  # 重置为内置

        excel_templates = {}
        for _, row in df.iterrows():
            template = str(row.get('模板名称', '')).strip()
            if not template:
                continue
            if template not in excel_templates:
                excel_templates[template] = []
            excel_templates[template].append({
                'column_name': str(row['列名']).strip(),
                'extract_id': str(row['提取指令']).strip(),
                'order': int(row['顺序']),
                'template': template,
            })
            id_rule = str(row.get('样品ID规则', '')).strip()
            if id_rule and id_rule.lower() != 'nan':
                self.template_id_rules[template] = id_rule

        for tname, cols in excel_templates.items():
            if tname in self.BUILTIN_NAMES:
                self.template_def = [col for col in self.template_def if col['template'] != tname]
                self.template_def.extend(cols)
                if tname not in self.template_names:
                    self.template_names.append(tname)
            else:
                self.template_def.extend(cols)
                if tname not in self.template_names:
                    self.template_names.append(tname)

    # 其余加载方法（ParamDef, ExtractRules, CalcParams, PathRules, GrayUnitConfig）保持不变
    def _load_param_def(self, xl):
        df = pd.read_excel(xl, sheet_name='ParamDef')
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

    def _load_extract_rules(self, xl):
        df = pd.read_excel(xl, sheet_name='ExtractRules')
        self.extract_rules = {}
        for _, row in df.iterrows():
            rid = str(row['指令ID']).strip()
            if rid:
                self.extract_rules[rid] = {
                    'param_id': str(row['参数ID']).strip(),
                    'source': str(row['来源段']).strip(),
                    'unit': str(row.get('单位', '')).strip(),
                    'data_type': str(row.get('数据类型', 'float')).strip(),
                    'extract_type': str(row.get('提取方式', 'direct')).strip(),
                    'offset': int(row.get('偏移量', 0)) if pd.notna(row.get('偏移量', 0)) else 0,
                }

    def _load_calc_params(self, xl):
        df = pd.read_excel(xl, sheet_name='CalcParams')
        self.calc_params = {}
        for _, row in df.iterrows():
            cid = str(row['参数ID']).strip()
            self.calc_params[cid] = {
                'display_name': str(row.get('显示名称', '')).strip(),
                'formula': str(row.get('计算公式', '')).strip(),
                'unit': str(row.get('单位', '')).strip(),
                'data_type': str(row.get('数据类型', 'float')).strip(),
            }

    def _load_path_rules(self, xl):
        df = pd.read_excel(xl, sheet_name='PathRules')
        self.path_rules = {}
        for _, row in df.iterrows():
            key = str(row['配置项']).strip()
            val = row['值']
            if pd.isna(val) or val is None:
                val = ''
            else:
                val = str(val).strip()
            self.path_rules[key] = val

    def _load_gray_unit_config(self, xl):
        df = pd.read_excel(xl, sheet_name='GrayUnitConfig')
        self.gray_unit_config = {}
        for _, row in df.iterrows():
            self.gray_unit_config[str(row['配置项']).strip()] = str(row['值']).strip()

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

    def get_sample_id_rule(self, template_name):
        if template_name in self.template_id_rules:
            return self.template_id_rules[template_name]
        rule = self.path_rules.get('样品ID规则', '')
        if rule is None or rule == '' or str(rule).lower() == 'nan':
            rule = '{parent}_{file_prefix}'
        return rule