import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import threading

from utils.helpers import frame_to_time, calculate_frame_hash, sort_treeview
from config.constants import FIRST_FRAME_DEFAULTS


class FirstFrameTab:
    def __init__(self, parent):
        self.parent = parent
        self.init_ui()
        
        # 初始化变量
        self.video_path = ""
        self.video_fps = 30
        self.cap = None
        self.processing = False
        self.first_frame_pairs = []
        self.current_selected_frame_index = -1
        self.first_frame_image = None
        self.original_first_frame_pairs = []
        self.first_frame = None
        self.first_frame_hash = None

    def init_ui(self):
        """初始化首帧比较标签页"""
        # 创建控制面板
        control_frame = ttk.LabelFrame(self.parent, text="视频设置", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), expand=False)

        # 视频选择
        ttk.Label(control_frame, text="选择视频文件:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self.first_frame_video_path_var = tk.StringVar()
        video_entry = ttk.Entry(control_frame, textvariable=self.first_frame_video_path_var, width=30)
        video_entry.pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="浏览...", command=self.browse_video).pack(fill=tk.X, pady=2)

        # 参数设置
        ttk.Label(control_frame, text="参数设置:", style="Header.TLabel").pack(anchor=tk.W, pady=(15, 5))

        # 相似度阈值
        ttk.Label(control_frame, text="相似度阈值 (0-1):").pack(anchor=tk.W, pady=2)
        self.first_frame_threshold_var = tk.DoubleVar(value=FIRST_FRAME_DEFAULTS["threshold"])
        threshold_slider = ttk.Scale(control_frame, from_=FIRST_FRAME_DEFAULTS["min_threshold"], 
                                     to=FIRST_FRAME_DEFAULTS["max_threshold"],
                                     variable=self.first_frame_threshold_var, orient=tk.HORIZONTAL)
        threshold_slider.pack(fill=tk.X, pady=2)
        self.first_frame_threshold_label = ttk.Label(control_frame,
                                                     text=f"当前值: {self.first_frame_threshold_var.get():.2f}")
        self.first_frame_threshold_label.pack(anchor=tk.W, pady=2)

        # 帧采样间隔
        ttk.Label(control_frame, text="帧采样间隔:").pack(anchor=tk.W, pady=2)
        self.first_frame_skip_var = tk.IntVar(value=FIRST_FRAME_DEFAULTS["frame_skip"])
        frame_skip_spinbox = ttk.Spinbox(control_frame, from_=1, to=50,
                                         textvariable=self.first_frame_skip_var, width=10)
        frame_skip_spinbox.pack(fill=tk.X, pady=2)

        # 操作按钮
        ttk.Label(control_frame, text="操作:", style="Header.TLabel").pack(anchor=tk.W, pady=(15, 5))
        self.first_frame_process_btn = ttk.Button(control_frame, text="分析首帧相似度",
                                                  command=self.start_processing, state=tk.DISABLED)
        self.first_frame_process_btn.pack(fill=tk.X, pady=5)

        self.first_frame_status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(control_frame, textvariable=self.first_frame_status_var,
                                 wraplength=200, justify=tk.LEFT)
        status_label.pack(fill=tk.X, pady=10)

        # 进度条
        self.first_frame_progress_var = tk.DoubleVar()
        self.first_frame_progress_bar = ttk.Progressbar(control_frame, variable=self.first_frame_progress_var,
                                                        maximum=100, mode="determinate")
        self.first_frame_progress_bar.pack(fill=tk.X, pady=5)

        # 绑定阈值滑块事件
        self.first_frame_threshold_var.trace("w", self.update_threshold_label)

        # 创建结果面板
        result_frame = ttk.LabelFrame(self.parent, text="首帧相似度分析", padding=10)
        result_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 首帧预览
        ttk.Label(result_frame, text="基准帧 (第0帧):", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self.first_frame_preview_frame = ttk.Frame(result_frame, height=150)
        self.first_frame_preview_frame.pack(fill=tk.X, pady=5)
        self.first_frame_preview_frame.pack_propagate(False)
        self.first_frame_preview_label = ttk.Label(self.first_frame_preview_frame, text="加载视频后显示",
                                                   relief=tk.SUNKEN, anchor=tk.CENTER)
        self.first_frame_preview_label.pack(fill=tk.BOTH, expand=True)

        # 结果列表
        ttk.Label(result_frame, text="相似帧列表:", style="Header.TLabel").pack(anchor=tk.W, pady=(10, 5))
        columns = ("time", "frame", "similarity")
        self.first_frame_tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="browse")

        # 定义列
        self.first_frame_tree.heading("time", text="时间位置",
                                      command=lambda: sort_treeview(self.first_frame_tree, "time", False))
        self.first_frame_tree.heading("frame", text="帧号",
                                      command=lambda: sort_treeview(self.first_frame_tree, "frame", False))
        self.first_frame_tree.heading("similarity", text="相似度",
                                      command=lambda: sort_treeview(self.first_frame_tree, "similarity", True))

        # 设置列宽
        self.first_frame_tree.column("time", width=120, anchor=tk.CENTER)
        self.first_frame_tree.column("frame", width=80, anchor=tk.CENTER)
        self.first_frame_tree.column("similarity", width=80, anchor=tk.CENTER)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.first_frame_tree.yview)
        self.first_frame_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.first_frame_tree.pack(fill=tk.BOTH, expand=True)

        # 绑定选择事件
        self.first_frame_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 状态标签
        self.first_frame_result_count_var = tk.StringVar(value="找到 0 个相似帧")
        result_count_label = ttk.Label(result_frame, textvariable=self.first_frame_result_count_var)
        result_count_label.pack(anchor=tk.W, pady=5)

        # 创建图像显示面板
        image_frame = ttk.LabelFrame(self.parent, text="关键帧预览", padding=10)
        image_frame.config(width=400)
        image_frame.pack_propagate(False)
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(5, 0))

        # 标题
        ttk.Label(image_frame, text="选定帧预览", style="Header.TLabel").pack(pady=(0, 10))

        # 图像显示区域
        self.selected_frame_preview_frame = ttk.Frame(image_frame, height=300)
        self.selected_frame_preview_frame.pack(fill=tk.X, pady=5)
        self.selected_frame_preview_frame.pack_propagate(False)
        self.selected_frame_preview_label = ttk.Label(self.selected_frame_preview_frame, text="选择结果查看帧",
                                                      relief=tk.SUNKEN, anchor=tk.CENTER)
        self.selected_frame_preview_label.pack(fill=tk.BOTH, expand=True)

        # 时间信息标签
        self.selected_frame_time_info = ttk.Label(image_frame, text="", style="Time.TLabel")
        self.selected_frame_time_info.pack(anchor=tk.W, pady=2)

        # 操作按钮
        button_frame = ttk.Frame(image_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="导出选定帧",
                   command=self.export_selected_frame).pack(fill=tk.X, pady=2)

        self.generate_video_btn = ttk.Button(button_frame, text="生成视频片段",
                                             command=self.generate_video_segment, state=tk.DISABLED)
        self.generate_video_btn.pack(fill=tk.X, pady=2)

        # 创建搜索框
        search_frame = ttk.Frame(result_frame)
        search_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.first_frame_search_var = tk.StringVar()
        # 先创建变量，但不要立即绑定事件
        search_entry = ttk.Entry(search_frame, textvariable=self.first_frame_search_var, width=25)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.insert(0, "输入时间或帧号...")

        # 现在Treeview已创建，再绑定搜索事件
        self.first_frame_search_var.trace("w", self.filter_results)
        # 清除默认文本
        self.first_frame_search_var.set("")

    def update_threshold_label(self, *args):
        """更新阈值显示标签"""
        self.first_frame_threshold_label.config(text=f"当前值: {self.first_frame_threshold_var.get():.2f}")

    def browse_video(self):
        """浏览视频文件"""
        self.video_path = filedialog.askopenfilename(
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.wmv")]
        )
        if self.video_path:
            self.first_frame_video_path_var.set(self.video_path)
            self.first_frame_process_btn.config(state=tk.NORMAL)
            self.first_frame_status_var.set(f"已选择: {self.video_path.split('/')[-1]}")

            # 尝试获取视频信息
            self.cap = cv2.VideoCapture(self.video_path)
            if self.cap.isOpened():
                self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
                if self.video_fps <= 0:
                    self.video_fps = 30
                self.cap.release()

    def start_processing(self):
        """开始处理视频"""
        if not self.video_path:
            messagebox.showerror("错误", "请先选择视频文件")
            return

        if self.processing:
            return

        self.processing = True
        self.first_frame_process_btn.config(state=tk.DISABLED, text="处理中...")
        self.first_frame_status_var.set("开始分析视频...")
        self.first_frame_progress_var.set(0)
        self.first_frame_tree.delete(*self.first_frame_tree.get_children())

        # 在新线程中处理视频
        threading.Thread(target=self.process_comparison, daemon=True).start()

    def process_comparison(self):
        """处理首帧比较的线程函数"""
        try:
            # 获取视频帧率
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                raise Exception("无法打开视频文件")

            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if self.video_fps <= 0:
                self.video_fps = 30  # 默认帧率

            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.first_frame_status_var.set(f"视频帧率: {self.video_fps:.2f} FPS | 总帧数: {total_frames}")
            self.parent.update()

            # 提取第一帧作为基准
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, self.first_frame = self.cap.read()
            if not ret or self.first_frame is None:
                raise Exception("无法读取第一帧")

            # 显示第一帧
            self.parent.after(0, self.display_first_frame)

            # 计算第一帧的哈希
            self.first_frame_hash = calculate_frame_hash(self.first_frame)
            self.first_frame_status_var.set("已获取第一帧，开始比较...")
            self.parent.update()

            # 比较其他帧
            self.first_frame_pairs = []
            frame_skip = self.first_frame_skip_var.get()
            threshold = self.first_frame_threshold_var.get()

            # 从第1帧开始比较
            current_frame = 1
            while current_frame < total_frames:
                # 跳过一些帧以提高效率
                if current_frame % frame_skip != 0:
                    current_frame += 1
                    continue

                # 获取帧
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
                ret, frame = self.cap.read()
                if not ret:
                    current_frame += 1
                    continue

                # 计算哈希和相似度
                frame_hash = calculate_frame_hash(frame)
                distance = self.first_frame_hash - frame_hash
                max_distance = len(self.first_frame_hash)
                similarity = 1 - (distance / max_distance)

                # 检查是否超过阈值
                if similarity > (1 - threshold):
                    # 计算时间位置
                    time_pos = frame_to_time(current_frame, self.video_fps)

                    self.first_frame_pairs.append((
                        current_frame, time_pos, similarity
                    ))

                # 更新进度
                progress = (current_frame / total_frames) * 100
                self.first_frame_progress_var.set(progress)

                if current_frame % 50 == 0:
                    self.first_frame_status_var.set(f"比较帧: {current_frame}/{total_frames}")
                    self.parent.update()

                current_frame += 1

            # 完成
            self.first_frame_status_var.set(f"完成! 找到 {len(self.first_frame_pairs)} 个相似帧")
            self.first_frame_result_count_var.set(f"找到 {len(self.first_frame_pairs)} 个相似帧")

            # 更新结果列表
            self.parent.after(0, self.update_result_list)

        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("处理错误", str(e)))
        finally:
            self.processing = False
            if self.cap:
                self.cap.release()
            self.parent.after(0, lambda: self.first_frame_process_btn.config(state=tk.NORMAL, text="分析首帧相似度"))

    def display_first_frame(self):
        """显示第一帧预览"""
        if self.first_frame is not None:
            # 转换为RGB
            img = cv2.cvtColor(self.first_frame, cv2.COLOR_BGR2RGB)

            # 调整大小
            h, w = img.shape[:2]
            container_width = max(1, self.first_frame_preview_frame.winfo_width())
            container_height = max(1, self.first_frame_preview_frame.winfo_height())

            # 确保容器有有效尺寸
            if container_width < 10 or container_height < 10:
                container_width = 300
                container_height = 150

            scale = min(container_width / w, container_height / h)
            new_w = int(w * scale)
            new_h = int(h * scale)

            img = cv2.resize(img, (new_w, new_h))

            # 转换为Tkinter图像
            img = Image.fromarray(img)
            img_tk = ImageTk.PhotoImage(img)

            # 更新标签
            self.first_frame_preview_label.config(image=img_tk)
            self.first_frame_preview_label.image = img_tk
            self.first_frame_image = img_tk

    def update_result_list(self):
        """更新结果列表"""
        # 清空现有内容
        for item in self.first_frame_tree.get_children():
            self.first_frame_tree.delete(item)

        # 添加新结果
        for pair in self.first_frame_pairs:
            frame, time_pos, similarity = pair
            self.first_frame_tree.insert("", tk.END, values=(
                time_pos,
                frame,
                f"{similarity:.2f}"
            ))

    def filter_results(self, *args):
        """过滤结果列表"""
        # 检查组件是否已初始化
        if not hasattr(self, 'first_frame_tree') or not hasattr(self, 'first_frame_pairs'):
            return

        search_term = self.first_frame_search_var.get().lower()
        if not search_term:
            self.update_result_list()
            return

        # 保存原始结果
        if not hasattr(self, 'original_first_frame_pairs'):
            self.original_first_frame_pairs = self.first_frame_pairs.copy()

        # 过滤结果
        filtered_pairs = []
        for pair in self.original_first_frame_pairs:
            frame, time_pos, similarity = pair
            if (search_term in time_pos.lower() or
                    search_term in str(frame)):
                filtered_pairs.append(pair)

        # 更新列表
        self.first_frame_pairs = filtered_pairs
        self.update_result_list()
        self.first_frame_result_count_var.set(f"找到 {len(filtered_pairs)} 个匹配结果")

    def on_tree_select(self, event):
        """当选择结果项时"""
        selected = self.first_frame_tree.selection()
        if not selected:
            return

        item = self.first_frame_tree.item(selected[0])
        values = item['values']

        if not values or len(values) < 2:
            return

        # 获取帧号
        try:
            frame = int(values[1])
        except (ValueError, IndexError):
            return

        # 显示图像
        self.display_selected_frame(frame)

        # 更新时间信息
        self.selected_frame_time_info.config(text=f"时间位置: {values[0]} | 帧号: {frame}")

        # 保存当前选择
        self.current_selected_frame_index = frame
        self.generate_video_btn.config(state=tk.NORMAL)

    def display_selected_frame(self, frame_num):
        """显示选定的帧"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return

        # 获取帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, img = cap.read()
        cap.release()

        if ret:
            # 转换为RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 调整大小
            h, w = img.shape[:2]
            container_width = max(1, self.selected_frame_preview_frame.winfo_width())
            container_height = max(1, self.selected_frame_preview_frame.winfo_height())

            # 确保容器有有效尺寸
            if container_width < 10 or container_height < 10:
                container_width = 300
                container_height = 250

            scale = min(container_width / w, container_height / h)
            new_w = int(w * scale)
            new_h = int(h * scale)

            img = cv2.resize(img, (new_w, new_h))

            # 转换为Tkinter图像
            img = Image.fromarray(img)
            img_tk = ImageTk.PhotoImage(img)

            # 更新标签
            self.selected_frame_preview_label.config(image=img_tk)
            self.selected_frame_preview_label.image = img_tk

    def export_selected_frame(self):
        """导出选定的帧"""
        if self.current_selected_frame_index < 0:
            messagebox.showinfo("提示", "请先选择一个结果")
            return

        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG文件", "*.jpg"), ("PNG文件", "*.png")]
        )

        if not file_path:
            return

        # 获取帧
        cap = cv2.VideoCapture(self.video_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_selected_frame_index)
        ret, frame = cap.read()
        cap.release()

        if ret:
            cv2.imwrite(file_path, frame)
            messagebox.showinfo("成功", f"帧已保存至:\n{file_path}")
        else:
            messagebox.showerror("错误", "无法获取选定帧")

    def generate_video_segment(self):
        """生成从第一帧到选定帧的视频片段"""
        if self.current_selected_frame_index < 0:
            messagebox.showinfo("提示", "请先选择一个结果")
            return

        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4文件", "*.mp4"), ("AVI文件", "*.avi")]
        )

        if not file_path:
            return

        try:
            # 创建输出目录（如果不存在）
            output_dir = file_path.rsplit('/', 1)[0] if '/' in file_path else '.'
            if not output_dir:
                output_dir = '.'
                
            import os
            if not os.path.exists(output_dir) and output_dir != '.':
                os.makedirs(output_dir)

            # 获取视频信息
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise Exception("无法打开源视频")

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.video_fps

            # 创建视频写入对象
            if file_path.lower().endswith('.mp4'):
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            else:  # .avi
                fourcc = cv2.VideoWriter_fourcc(*'XVID')

            out = cv2.VideoWriter(file_path, fourcc, fps, (width, height))

            if not out.isOpened():
                raise Exception("无法创建输出视频文件")

            # 写入从第一帧到选定帧
            total_frames = self.current_selected_frame_index + 1
            for i in range(total_frames):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    out.write(frame)

                # 更新进度
                progress = (i / total_frames) * 100
                self.first_frame_progress_var.set(progress)
                self.first_frame_status_var.set(f"生成片段: {i + 1}/{total_frames}...")
                self.parent.update()

            # 释放资源
            cap.release()
            out.release()

            # 完成
            self.first_frame_status_var.set(f"视频片段已保存至: {file_path}")
            messagebox.showinfo("成功", f"视频片段已成功生成!\n{file_path}")

        except Exception as e:
            messagebox.showerror("生成错误", f"生成视频片段时出错:\n{str(e)}")