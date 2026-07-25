# -*- coding: utf-8 -*-
"""
GUI界面模块 - 亮色主题
优化：延迟导入、取消自动生成配置、UI先显示再加载配置
版本：v3.2
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime

import ttkbootstrap as tb
from ttkbootstrap.constants import *


class MicroCTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MicroCT 骨参数自动提取工具 v3.2")
        self.root.geometry("1150x820")
        self.root.minsize(1050, 750)

        self.config_path = tk.StringVar()
        self._init_config()

        self.template_name = tk.StringVar(value='标准模板（长骨专用）区分松质骨皮质骨参数')
        self.input_dir = tk.StringVar()
        self.output_file = tk.StringVar()
        self.auto_filename = tk.BooleanVar(value=True)
        self.open_folder = tk.BooleanVar(value=True)
        self.verbose_logging = tk.BooleanVar(value=True)
        self.is_running = False
        # 初始默认模板列表（与内置模板一致）
        self.template_list = [
            '标准模板（长骨专用）区分松质骨皮质骨参数',
            '通用模板（一个样品CSV内多个ROI分析结果）',
            '通用模板（一组样品不同部位、重复同名CSV）'
        ]
        self._current_processor = None
        self._config_loaded = False  # 标记配置是否已加载

        self._build_ui()

        # 延迟加载配置，先让窗口显示
        self.root.after(100, self._load_config)

    def _init_config(self):
        # 仅设置配置文件路径，不自动生成
        config_file = os.path.join(os.getcwd(), 'parameters.xlsx')
        self.config_path.set(config_file)

    def _build_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))

        title_label = ttk.Label(header_frame, text="🦴 MicroCT 骨参数自动提取工具",
                                font=('微软雅黑', 22, 'bold'), foreground='#1a56db')
        title_label.pack(side=tk.LEFT)

        version_label = ttk.Label(header_frame, text="v3.2",
                                   font=('微软雅黑', 12), foreground='#94a3b8')
        version_label.pack(side=tk.LEFT, padx=(10, 0))

        status_frame = ttk.Frame(header_frame)
        status_frame.pack(side=tk.RIGHT)
        self.status_dot = ttk.Label(status_frame, text="●", font=('微软雅黑', 16), foreground='#22c55e')
        self.status_dot.pack(side=tk.LEFT, padx=(0, 6))
        self.status_label = ttk.Label(status_frame, text="就绪", font=('微软雅黑', 12), foreground='#64748b')
        self.status_label.pack(side=tk.LEFT)

        stats_frame = ttk.Frame(main_frame)
        stats_frame.pack(fill=tk.X, pady=(0, 15))

        stats_data = [
            ("📄 总样品", "0", "total", "#3b82f6"),
            ("✅ 成功", "0", "success", "#22c55e"),
            ("⏭ 跳过", "0", "skipped", "#f59e0b"),
            ("⚠️ 警告", "0", "warning", "#f97316"),
            ("❌ 错误", "0", "error", "#ef4444"),
        ]

        self.stats_labels = {}
        for label, value, key, color in stats_data:
            card = ttk.Frame(stats_frame)
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

            val_lbl = ttk.Label(card, text=value, font=('微软雅黑', 28, 'bold'),
                                foreground=color, anchor='center')
            val_lbl.pack(pady=(0, 0))

            name_lbl = ttk.Label(card, text=label, font=('微软雅黑', 11),
                                 foreground='#64748b', anchor='center')
            name_lbl.pack(pady=(0, 5))

            self.stats_labels[key] = val_lbl

        config_frame = ttk.LabelFrame(main_frame, text="⚙️ 配置设置", bootstyle="light", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(config_frame)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="配置文件:", font=('微软雅黑', 11, 'bold'), width=12).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.config_path, font=('微软雅黑', 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(row1, text="📂 浏览", command=self._browse_config, bootstyle="outline-primary", width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row1, text="✨ 创建默认", command=self._create_default_config, bootstyle="outline-primary", width=12).pack(side=tk.LEFT)

        row2 = ttk.Frame(config_frame)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="模板方案:", font=('微软雅黑', 11, 'bold'), width=12).pack(side=tk.LEFT)

        self.template_menu_var = tk.StringVar(value=self.template_name.get())
        self.template_menu = tk.OptionMenu(
            row2,
            self.template_menu_var,
            *self.template_list,
            command=self._on_template_selected
        )
        self.template_menu.config(
            font=('微软雅黑', 10),
            bg='white',
            fg='#0f172a',
            activebackground='#f1f5f9',
            activeforeground='#0f172a',
            relief='flat',
            width=30
        )
        menu = self.template_menu['menu']
        menu.config(
            bg='white',
            fg='#0f172a',
            activebackground='#f1f5f9',
            activeforeground='#0f172a',
            relief='flat',
            bd=0,
            borderwidth=0,
            tearoff=0
        )
        self.template_menu.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))

        ttk.Button(row2, text="🔄 刷新", command=self._refresh_templates, bootstyle="outline-primary", width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row2, text="✏️ 编辑模板", command=self._edit_template, bootstyle="outline-primary", width=12).pack(side=tk.LEFT)

        io_frame = ttk.LabelFrame(main_frame, text="📁 输入输出", bootstyle="light", padding="10")
        io_frame.pack(fill=tk.X, pady=(0, 10))

        row3 = ttk.Frame(io_frame)
        row3.pack(fill=tk.X, pady=5)
        ttk.Label(row3, text="输入目录:", font=('微软雅黑', 11, 'bold'), width=12).pack(side=tk.LEFT)
        ttk.Entry(row3, textvariable=self.input_dir, font=('微软雅黑', 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(row3, text="📂 浏览", command=self._browse_input, bootstyle="outline-primary", width=10).pack(side=tk.LEFT)

        row4 = ttk.Frame(io_frame)
        row4.pack(fill=tk.X, pady=5)
        ttk.Label(row4, text="输出文件:", font=('微软雅黑', 11, 'bold'), width=12).pack(side=tk.LEFT)
        ttk.Entry(row4, textvariable=self.output_file, font=('微软雅黑', 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 8))
        ttk.Button(row4, text="📂 浏览", command=self._browse_output, bootstyle="outline-primary", width=10).pack(side=tk.LEFT)

        row5 = ttk.Frame(io_frame)
        row5.pack(fill=tk.X, pady=8)
        ttk.Checkbutton(row5, text="📅 自动生成文件名（含日期）", variable=self.auto_filename,
                        command=self._toggle_auto_filename).pack(side=tk.LEFT, padx=(0, 30))
        ttk.Checkbutton(row5, text="📂 处理完成后打开文件夹", variable=self.open_folder).pack(side=tk.LEFT, padx=(0, 30))
        ttk.Checkbutton(row5, text="📝 显示详细日志", variable=self.verbose_logging).pack(side=tk.LEFT)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.btn_start = ttk.Button(btn_frame, text="▶ 开始处理", command=self._start_processing,
                                     bootstyle="success", width=18)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_stop = ttk.Button(btn_frame, text="⏹ 停止", command=self._stop_processing,
                                    bootstyle="danger", width=14, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(btn_frame, text="📋 查看配置", command=self._view_config,
                   bootstyle="outline-primary", width=14).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="📤 导出错误日志", command=self._export_errors,
                   bootstyle="outline-primary", width=16).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="❓ 帮助", command=self._show_help,
                   bootstyle="outline-primary", width=12).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="🗑 清空日志", command=self._clear_log,
                   bootstyle="outline-primary", width=12).pack(side=tk.LEFT)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 8))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                             maximum=100, bootstyle="primary-striped")
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = ttk.Label(progress_frame, text="", font=('微软雅黑', 10), foreground='#64748b')
        self.progress_label.pack(anchor=tk.W, pady=(4, 0))

        log_frame = ttk.LabelFrame(main_frame, text="📋 日志输出", bootstyle="light", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=16,
                                                   font=('Consolas', 11), wrap=tk.WORD,
                                                   bg='#f8fafc', fg='#0f172a',
                                                   insertbackground='#0f172a',
                                                   relief='flat', borderwidth=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.log_text.tag_config('info', foreground='#2563eb')
        self.log_text.tag_config('success', foreground='#16a34a')
        self.log_text.tag_config('warning', foreground='#f59e0b')
        self.log_text.tag_config('error', foreground='#dc2626')
        self.log_text.tag_config('detail', foreground='#94a3b8')

        self._log("🚀 欢迎使用 MicroCT 骨参数自动提取工具 v3.2", 'info')
        self._log("💡 正在加载配置，请稍候...", 'info')

    def _on_template_selected(self, value):
        self.template_name.set(value)
        self._load_config()

    def _refresh_templates(self):
        self._load_config()
        menu = self.template_menu['menu']
        menu.delete(0, 'end')
        for item in self.template_list:
            menu.add_command(label=item, command=lambda v=item: self._on_template_selected(v))
        if self.template_menu_var.get() not in self.template_list:
            if self.template_list:
                self.template_menu_var.set(self.template_list[0])
                self.template_name.set(self.template_list[0])

    def _log(self, msg, tag='info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def _update_stats(self, total=0, success=0, skipped=0, warning=0, error=0):
        self.stats_labels['total'].config(text=str(total))
        self.stats_labels['success'].config(text=str(success))
        self.stats_labels['skipped'].config(text=str(skipped))
        self.stats_labels['warning'].config(text=str(warning))
        self.stats_labels['error'].config(text=str(error))

    def _load_config(self):
        # 如果已经加载过则跳过
        if self._config_loaded:
            return
        self._config_loaded = True

        from config_loader import update_config_if_needed
        update_config_if_needed(self.config_path.get())

        if os.path.exists(self.config_path.get()):
            try:
                from config_loader import ConfigLoader
                config = ConfigLoader(self.config_path.get())
                config.load()
                self.template_list = config.template_names if config.template_names else [
                    '标准模板（长骨专用）区分松质骨皮质骨参数',
                    '通用模板（一个样品CSV内多个ROI分析结果）',
                    '通用模板（一组样品不同部位、重复同名CSV）'
                ]
                menu = self.template_menu['menu']
                menu.delete(0, 'end')
                for item in self.template_list:
                    menu.add_command(label=item, command=lambda v=item: self._on_template_selected(v))

                if self.template_name.get() not in self.template_list:
                    if self.template_list:
                        self.template_name.set(self.template_list[0])
                        self.template_menu_var.set(self.template_list[0])
                else:
                    self.template_menu_var.set(self.template_name.get())

                self._log(f"✅ 已加载配置: {self.config_path.get()}", 'success')
                self._log(f"📋 当前模板: {self.template_name.get()}", 'info')
            except Exception as e:
                self._log(f"⚠️ 加载配置失败: {e}，使用内置模板", 'warning')
        else:
            # 配置文件不存在，使用内置模板
            self._log("ℹ️ 配置文件不存在，使用内置默认模板", 'info')
            self.template_list = [
                '标准模板（长骨专用）区分松质骨皮质骨参数',
                '通用模板（一个样品CSV内多个ROI分析结果）',
                '通用模板（一组样品不同部位、重复同名CSV）'
            ]
            menu = self.template_menu['menu']
            menu.delete(0, 'end')
            for item in self.template_list:
                menu.add_command(label=item, command=lambda v=item: self._on_template_selected(v))
            if self.template_name.get() not in self.template_list:
                self.template_name.set(self.template_list[0])
                self.template_menu_var.set(self.template_list[0])

    def _edit_template(self):
        if not os.path.exists(self.config_path.get()):
            messagebox.showerror("错误", "配置文件不存在，请先创建配置文件")
            return
        try:
            from config_loader import ConfigLoader
            from template_editor import TemplateEditor
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
        self._log("✅ 模板已更新", 'success')

    def _browse_config(self):
        path = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        if path:
            self.config_path.set(path)
            self._load_config()

    def _create_default_config(self):
        from config_loader import generate_default_config
        default_path = os.path.join(os.getcwd(), 'parameters.xlsx')
        path = filedialog.asksaveasfilename(
            title="保存配置文件",
            initialfile=os.path.basename(default_path),
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx")]
        )
        if path:
            generate_default_config(path)
            self.config_path.set(path)
            self._log(f"✅ 已创建默认配置文件: {path}", 'success')
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
🦴 MicroCT 骨参数自动提取工具 v3.2

【📖 使用说明】
1. 选择或创建配置文件（.xlsx格式），点击"创建默认"生成
2. 选择模板方案：
   • 标准模板（长骨专用）— 松质+皮质配对
   • 通用模板（一个样品CSV内多个ROI分析结果）— 单文件独立提取，多个3D结果水平展开
   • 通用模板（一组样品不同部位、重复同名CSV）— 同一前缀的CSV在不同文件夹中合并为一行
3. 选择包含CSV文件的顶层输入目录
4. 指定输出Excel文件路径（或勾选自动生成）
5. 点击"开始处理"

【✏️ 模板编辑器】
点击"编辑模板"打开积木式编辑器：
- 左侧：所有可用参数（包括计算参数），支持搜索过滤
- 双击左侧参数 → 添加到右侧
- 右侧：已选参数，拖拽调整顺序
- 双击右侧参数 → 从模板中移除

【📤 错误日志】
处理完成后点击"导出错误日志"可导出所有错误和警告

【📁 文件支持】
支持 .ctan.csv, .batman.csv 等任意 .csv 结果文件
"""
        messagebox.showinfo("帮助", help_text)

    def _clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self._log("🗑 日志已清空", 'info')

    def _export_errors(self):
        if self._current_processor is None:
            messagebox.showinfo("提示", "请先运行处理后再导出错误日志")
            return
        errors = self._current_processor.get_errors()
        warnings = self._current_processor.get_warnings()
        if not errors and not warnings:
            messagebox.showinfo("提示", "✅ 没有错误或警告可导出")
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
        self.status_label.config(text="处理中...")
        self.status_dot.config(foreground='#f59e0b')
        self._current_processor = None

        self.processing_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.processing_thread.start()

    def _process_worker(self):
        try:
            from config_loader import ConfigLoader
            from data_processor import SampleProcessor

            self._log("🚀 开始处理...", 'info')
            self._log(f"📁 配置文件: {self.config_path.get()}", 'info')
            self._log(f"📁 输入目录: {self.input_dir.get()}", 'info')
            self._log(f"📋 模板方案: {self.template_name.get()}", 'info')
            self._log(f"📝 详细日志: {'开启' if self.verbose_logging.get() else '关闭'}", 'info')

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
            self._current_processor = processor

            processor.scan_files()

            if processor._stop_flag:
                self._log("⏹ 处理已停止", 'warning')
                return

            processor.process_all()

            if processor._stop_flag:
                self._log("⏹ 处理已停止", 'warning')
                return

            success = processor.export_to_excel(self.output_file.get())

            if success:
                stats = processor.get_stats()
                errors = processor.get_errors()
                warnings = processor.get_warnings()

                self._update_stats(
                    total=stats['total'],
                    success=stats['success'],
                    skipped=stats['skipped'],
                    warning=stats['warning'],
                    error=stats['error']
                )

                self._log("✅ 处理完成！", 'success')
                self._log(f"   📊 总样品: {stats['total']}", 'info')
                self._log(f"   ✅ 成功: {stats['success']}", 'success')
                self._log(f"   ⏭ 跳过: {stats['skipped']}", 'warning')
                self._log(f"   ⚠️ 警告: {stats['warning']}", 'warning')
                self._log(f"   ❌ 错误: {stats['error']}", 'error')

                if errors:
                    self._log(f"   ⚠️ 共有 {len(errors)} 个错误，点击【导出错误日志】查看详情", 'error')
                if warnings:
                    self._log(f"   ⚠️ 共有 {len(warnings)} 个警告，点击【导出错误日志】查看详情", 'warning')

                self.status_label.config(text="完成 ✅")
                self.status_dot.config(foreground='#22c55e')
                self.progress_var.set(100)
                self.progress_label.config(text="处理完成！")

                if self.open_folder.get():
                    os.startfile(os.path.dirname(self.output_file.get()))
            else:
                self._log("❌ 导出失败", 'error')
                self.status_label.config(text="失败 ❌")
                self.status_dot.config(foreground='#ef4444')

        except Exception as e:
            self._log(f"❌ 处理出错: {e}", 'error')
            import traceback
            self._log(traceback.format_exc(), 'error')
            self.status_label.config(text="错误 ❌")
            self.status_dot.config(foreground='#ef4444')
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
            self._log("⏹ 正在停止...", 'warning')
            self.status_label.config(text="停止中...")
            self.status_dot.config(foreground='#f59e0b')
            if self._current_processor:
                self._current_processor.stop()


def main():
    root = tb.Window(themename="litera")
    app = MicroCTApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()