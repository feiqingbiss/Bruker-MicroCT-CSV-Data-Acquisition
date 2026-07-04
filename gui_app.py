# -*- coding: utf-8 -*-
"""
GUI界面模块
提供图形用户界面
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

from config_loader import ConfigLoader, generate_default_config
from data_processor import SampleProcessor
from template_editor import TemplateEditor


class MicroCTApp:
    """主应用程序"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("MicroCT 骨参数自动提取工具 v1.0")
        self.root.geometry("1050x780")
        self.root.minsize(950, 700)
        
        style = ttk.Style()
        style.configure('Header.TLabel', font=('微软雅黑', 14, 'bold'))
        style.configure('Status.TLabel', font=('微软雅黑', 10))
        
        self.config_path = tk.StringVar(value='parameters.xlsx')
        self.template_name = tk.StringVar(value='标准模板')
        self.input_dir = tk.StringVar()
        self.output_file = tk.StringVar()
        self.auto_filename = tk.BooleanVar(value=True)
        self.open_folder = tk.BooleanVar(value=True)
        self.verbose_logging = tk.BooleanVar(value=True)
        self.is_running = False
        self.template_list = ['标准模板']
        self._current_processor = None  # 保存处理器引用，用于导出错误日志
        
        self._build_ui()
        self._load_config()
    
    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title_label = ttk.Label(main_frame, text="MicroCT 骨参数自动提取工具", style='Header.TLabel')
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        config_frame = ttk.LabelFrame(main_frame, text="配置设置", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        row1 = ttk.Frame(config_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="配置文件:", width=10).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.config_path, width=55).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1, text="浏览...", command=self._browse_config).pack(side=tk.LEFT)
        ttk.Button(row1, text="创建默认", command=self._create_default_config).pack(side=tk.LEFT, padx=5)
        
        row2 = ttk.Frame(config_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="模板方案:", width=10).pack(side=tk.LEFT)
        self.template_combo = ttk.Combobox(row2, textvariable=self.template_name,
                                           values=self.template_list, width=35)
        self.template_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="刷新模板", command=self._refresh_templates).pack(side=tk.LEFT)
        ttk.Button(row2, text="📝 编辑模板", command=self._edit_template).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        io_frame = ttk.LabelFrame(main_frame, text="输入输出", padding="10")
        io_frame.pack(fill=tk.X, pady=(0, 10))
        
        row3 = ttk.Frame(io_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="输入目录:", width=10).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.input_dir, width=55).pack(side=tk.LEFT, padx=5)
        ttk.Button(row3, text="浏览...", command=self._browse_input).pack(side=tk.LEFT)
        
        row4 = ttk.Frame(io_frame)
        row4.pack(fill=tk.X, pady=2)
        ttk.Label(row4, text="输出文件:", width=10).pack(side=tk.LEFT)
        ttk.Entry(row4, textvariable=self.output_file, width=55).pack(side=tk.LEFT, padx=5)
        ttk.Button(row4, text="浏览...", command=self._browse_output).pack(side=tk.LEFT)
        
        row5 = ttk.Frame(io_frame)
        row5.pack(fill=tk.X, pady=5)
        ttk.Checkbutton(row5, text="自动生成文件名（含日期）", variable=self.auto_filename,
                        command=self._toggle_auto_filename).pack(side=tk.LEFT, padx=5)
        ttk.Checkbutton(row5, text="处理完成后打开文件夹", variable=self.open_folder).pack(side=tk.LEFT, padx=20)
        ttk.Checkbutton(row5, text="显示详细日志", variable=self.verbose_logging).pack(side=tk.LEFT, padx=20)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.btn_start = ttk.Button(btn_frame, text="▶ 开始处理", command=self._start_processing, width=15)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(btn_frame, text="⏹ 停止", command=self._stop_processing,
                                   width=12, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📋 查看配置", command=self._view_config, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📤 导出错误日志", command=self._export_errors, width=14).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❓ 帮助", command=self._show_help, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空日志", command=self._clear_log, width=10).pack(side=tk.LEFT, padx=5)
        
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.status_label = ttk.Label(status_frame, text="状态: 就绪", style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT)
        
        self.stats_label = ttk.Label(status_frame, text="", style='Status.TLabel')
        self.stats_label.pack(side=tk.RIGHT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_label = ttk.Label(main_frame, text="", style='Status.TLabel')
        self.progress_label.pack(anchor=tk.W)
        
        log_frame = ttk.LabelFrame(main_frame, text="日志输出", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=14,
                                                   font=('Consolas', 9), wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        self.log_text.tag_config('info', foreground='#0066CC')
        self.log_text.tag_config('success', foreground='#008000')
        self.log_text.tag_config('warning', foreground='#FF8C00')
        self.log_text.tag_config('error', foreground='#CC0000')
        self.log_text.tag_config('detail', foreground='#666666')
        
        self._log("就绪，请设置输入目录并点击开始处理", 'info')
    
    def _log(self, msg, tag='info'):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def _load_config(self):
        try:
            config = ConfigLoader(self.config_path.get())
            config.load()
            self.template_list = config.template_names if config.template_names else ['标准模板']
            self.template_combo['values'] = self.template_list
            if self.template_name.get() not in self.template_list:
                self.template_name.set(self.template_list[0])
            self._log(f"已加载配置: {self.config_path.get()}", 'info')
            self._log(f"模板列表: {', '.join(self.template_list)}", 'info')
        except Exception as e:
            self._log(f"加载配置失败: {e}", 'error')
    
    def _refresh_templates(self):
        self._load_config()
    
    def _edit_template(self):
        if not os.path.exists(self.config_path.get()):
            messagebox.showerror("错误", "配置文件不存在，请先创建配置文件")
            return
        try:
            config = ConfigLoader(self.config_path.get())
            config.load()
            editor = TemplateEditor(
                self.root,
                self.config_path.get(),
                config,
                self.template_name.get(),
                callback=self._on_template_saved
            )
        except Exception as e:
            messagebox.showerror("错误", f"打开编辑器失败: {e}")
    
    def _on_template_saved(self):
        self._load_config()
        self._log("模板已更新", 'success')
    
    def _browse_config(self):
        path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        if path:
            self.config_path.set(path)
            self._load_config()
    
    def _create_default_config(self):
        path = filedialog.asksaveasfilename(
            title="保存配置文件",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx")]
        )
        if path:
            generate_default_config(path)
            self.config_path.set(path)
            self._log(f"已创建默认配置文件: {path}", 'success')
            self._load_config()
    
    def _browse_input(self):
        path = filedialog.askdirectory(title="选择输入目录")
        if path:
            self.input_dir.set(path)
            self._update_output_filename()
    
    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="保存输出文件",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx")]
        )
        if path:
            self.output_file.set(path)
    
    def _toggle_auto_filename(self):
        if self.auto_filename.get():
            self._update_output_filename()
    
    def _update_output_filename(self):
        if self.auto_filename.get() and self.input_dir.get():
            base_name = os.path.basename(self.input_dir.get())
            if not base_name:
                base_name = "结果"
            date_str = datetime.now().strftime('%Y%m%d')
            output_path = os.path.join(self.input_dir.get(), f"{base_name}_汇总_{date_str}.xlsx")
            self.output_file.set(output_path)
    
    def _view_config(self):
        if os.path.exists(self.config_path.get()):
            os.startfile(self.config_path.get())
        else:
            messagebox.showerror("错误", "配置文件不存在")
    
    def _show_help(self):
        help_text = """
MicroCT 骨参数自动提取工具 v1.0

【使用说明】
1. 选择配置文件（.xlsx格式），或点击"创建默认"生成
2. 选择模板方案（从配置文件中读取）
3. 选择包含CSV文件的顶层输入目录
4. 指定输出Excel文件路径
5. 点击"开始处理"

【模板编辑器】
点击"编辑模板"打开积木式编辑器：
- 左侧：所有可用参数，支持搜索过滤
- 双击左侧参数 → 添加到右侧
- 右侧：已选参数，拖拽可调整顺序
- 双击右侧参数 → 从模板中移除
- 保存后立即生效

【错误日志】
处理完成后点击"导出错误日志"可导出所有错误和警告
- 错误：提取失败、计算失败等
- 警告：依赖缺失、单侧数据缺失等

【配置文件说明】
- ParamDef: 定义CSV中参数的列名映射
- ExtractRules: 定义提取指令（参数+来源后缀）
- CalcParams: 定义计算参数（公式）
- TemplateDef: 定义输出模板（列顺序）
- PathRules: 定义样品ID提取规则
- GrayUnitConfig: 定义灰度单位

【参数后缀约定】
- _trab_3D: 松质骨3D提取
- _cort_3D: 皮质骨3D提取
- _cort_2D: 皮质骨2D提取
- _trab_H: 松质骨直方图提取
- _cort_H: 皮质骨直方图提取
- _META: 元数据
        """
        messagebox.showinfo("帮助", help_text)
    
    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self._log("日志已清空", 'info')
    
    def _export_errors(self):
        """导出错误日志"""
        if self._current_processor is None:
            messagebox.showinfo("提示", "请先运行处理后再导出错误日志")
            return
        
        errors = self._current_processor.get_errors()
        warnings = self._current_processor.get_warnings()
        if not errors and not warnings:
            messagebox.showinfo("提示", "没有错误或警告可导出")
            return
        
        path = filedialog.asksaveasfilename(
            title="保存错误日志",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        if path:
            self._current_processor.export_errors(path)
    
    def _start_processing(self):
        if self.is_running:
            return
        
        if not self.input_dir.get():
            messagebox.showerror("错误", "请选择输入目录")
            return
        if not os.path.exists(self.input_dir.get()):
            messagebox.showerror("错误", "输入目录不存在")
            return
        
        if not self.config_path.get():
            messagebox.showerror("错误", "请选择配置文件")
            return
        if not os.path.exists(self.config_path.get()):
            messagebox.showerror("错误", "配置文件不存在")
            return
        
        if not self.output_file.get():
            messagebox.showerror("错误", "请指定输出文件路径")
            return
        
        self.is_running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_label.config(text="状态: 处理中...")
        self.stats_label.config(text="")
        self._current_processor = None  # 重置处理器引用
        
        self.processing_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.processing_thread.start()
    
    def _process_worker(self):
        try:
            self._log("开始处理...", 'info')
            self._log(f"配置文件: {self.config_path.get()}", 'info')
            self._log(f"输入目录: {self.input_dir.get()}", 'info')
            self._log(f"模板方案: {self.template_name.get()}", 'info')
            self._log(f"详细日志: {'开启' if self.verbose_logging.get() else '关闭'}", 'info')
            
            config = ConfigLoader(self.config_path.get())
            config.load()
            
            verbose = self.verbose_logging.get()
            processor = SampleProcessor(
                config,
                self.input_dir.get(),
                self.template_name.get(),
                log_callback=self._log,
                progress_callback=self._update_progress,
                verbose=verbose
            )
            self._current_processor = processor  # 保存引用
            
            processor.scan_files()
            
            if processor._stop_flag:
                self._log("处理已停止", 'warning')
                return
            
            processor.process_all()
            
            if processor._stop_flag:
                self._log("处理已停止", 'warning')
                return
            
            success = processor.export_to_excel(self.output_file.get())
            
            if success:
                stats = processor.get_stats()
                errors = processor.get_errors()
                warnings = processor.get_warnings()
                self._log(f"✅ 处理完成！", 'success')
                self._log(f"   总样品: {stats['total']}", 'info')
                self._log(f"   成功: {stats['success']}", 'success')
                self._log(f"   跳过: {stats['skipped']}", 'warning')
                self._log(f"   警告: {stats['warning']}", 'warning')
                self._log(f"   错误: {stats['error']}", 'error')
                
                if errors:
                    self._log(f"   ⚠ 共有 {len(errors)} 个错误，点击【导出错误日志】查看详情", 'error')
                if warnings:
                    self._log(f"   ⚠ 共有 {len(warnings)} 个警告，点击【导出错误日志】查看详情", 'warning')
                
                self.stats_label.config(
                    text=f"成功: {stats['success']}  |  跳过: {stats['skipped']}  |  警告: {stats['warning']}  |  错误: {stats['error']}"
                )
                self.status_label.config(text="状态: 完成 ✅")
                self.progress_var.set(100)
                self.progress_label.config(text="处理完成！")
                
                if self.open_folder.get():
                    os.startfile(os.path.dirname(self.output_file.get()))
            else:
                self._log("导出失败", 'error')
                self.status_label.config(text="状态: 失败 ❌")
                
        except Exception as e:
            self._log(f"处理出错: {e}", 'error')
            import traceback
            self._log(traceback.format_exc(), 'error')
            self.status_label.config(text="状态: 错误 ❌")
        finally:
            self.is_running = False
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
    
    def _update_progress(self, current, total, msg=''):
        if total > 0:
            pct = (current / total) * 100
            self.progress_var.set(pct)
            self.progress_label.config(text=f"进度: {current}/{total}  {msg}")
        self.root.update_idletasks()
    
    def _stop_processing(self):
        if self.is_running:
            self._log("正在停止...", 'warning')
            self.status_label.config(text="状态: 停止中...")
            if self._current_processor:
                self._current_processor.stop()


def main():
    root = tk.Tk()
    app = MicroCTApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
