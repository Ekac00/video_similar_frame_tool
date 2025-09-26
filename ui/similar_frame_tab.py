import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import threading

from utils.helpers import frame_to_time, calculate_frame_hash, sort_treeview
from config.constants import SIMILAR_FRAME_DEFAULTS


class SimilarFrameTab:
    def __init__(self, parent):
        self.parent = parent
        self.init_ui()
        
        # 初始化变量
        self.video_path = ""
        self.video_fps = 30
        self.cap = None
        self.processing = False
        self.similar_pairs = []
        self.current_similar_frame_index = -1
        self.original_similar_pairs = []

    def init_ui(self):
        """初始化相似帧查找标签页"""
        # 创建控制面板
        control_frame = ttk.LabelFrame(self.parent, text="视频设置", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), expand=False)

        # 视频选择
        ttk.Label(control_frame, text="选择视频文件:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self.similar_video_path_var = tk.StringVar()
        video_entry = ttk.Entry(control_frame, textvariable=self.similar_video_path_var, width=30)
        video_entry.pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="浏览...", command=self.browse_video).pack(fill=tk.X, pady=2)

        # 参数设置
        ttk.Label(control_frame, text="参数设置:", style="Header.TLabel").pack(anchor=tk.W, pady=(15, 5))

        # 相似度阈值
        ttk.Label(control_frame, text="相似度阈值 (0-1):").pack(anchor=tk.W, pady=2)
        self.similar_threshold_var = tk.DoubleVar(value=SIMILAR_FRAME_DEFAULTS["threshold"])
        threshold_slider = ttk.Scale(control_frame, from_=SIMILAR_FRAME_DEFAULTS["min_threshold"], 
                                     to=SIMILAR_FRAME_DEFAULTS["max_threshold"],
                                     variable=self.similar_threshold_var, orient=tk.HORIZONTAL)
        threshold_slider.pack(fill=tk.X, pady=2)
        self.similar_threshold_label = ttk.Label(control_frame, 
                                                 text=f"当前值: {self.similar_threshold_var.get():.2f}")
        self.similar_threshold_label.pack(anchor=tk.W, pady=2)

        # 帧采样间隔
        ttk.Label(control_frame, text="帧采样间隔:").pack(anchor=tk.W, pady=2)
        self.similar_frame_skip_var = tk.IntVar(value=SIMILAR_FRAME_DEFAULTS["frame_skip"])
        frame_skip_spinbox = ttk.Spinbox(control_frame, from_=1, to=100,
                                         textvariable=self.similar_frame_skip_var, width=10)
        frame_skip_spinbox.pack(fill=tk.X, pady=2)

        # 操作按钮
        ttk.Label(control_frame, text="操作:", style="Header.TLabel").pack(anchor=tk.W, pady=(15, 5))
        self.similar_process_btn = ttk.Button(control_frame, text="查找相似帧",
                                              command=self.start_processing, state=tk.DISABLED)
        self.similar_process_btn.pack(fill=tk.X, pady=5)

        self.similar_status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(control_frame, textvariable=self.similar_status_var,
                                 wraplength=200, justify=tk.LEFT)
        status_label.pack(fill=tk.X, pady=10)

        # 进度条
        self.similar_progress_var = tk.DoubleVar()
        self.similar_progress_bar = ttk.Progressbar(control_frame, variable=self.similar_progress_var,
                                                    maximum=100, mode="determinate")
        self.similar_progress_bar.pack(fill=tk.X, pady=5)

        # 绑定阈值滑块事件
        self.similar_threshold_var.trace("w", self.update_threshold_label)

        # 创建结果面板
        result_frame = ttk.LabelFrame(self.parent, text="相似帧结果", padding=10)
        result_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 创建搜索框
        search_frame = ttk.Frame(result_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.similar_search_var = tk.StringVar()
        # 先创建变量，但不要立即绑定事件
        search_entry = ttk.Entry(search_frame, textvariable=self.similar_search_var, width=25)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.insert(0, "输入时间或帧号...")

        # 结果列表
        columns = ("time1", "frame1", "time2", "frame2", "similarity")
        self.similar_tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="browse")

        # 定义列
        self.similar_tree.heading("time1", text="时间位置 1",
                                  command=lambda: sort_treeview(self.similar_tree, "time1", False))
        self.similar_tree.heading("frame1", text="帧号 1",
                                  command=lambda: sort_treeview(self.similar_tree, "frame1", False))
        self.similar_tree.heading("time2", text="时间位置 2",
                                  command=lambda: sort_treeview(self.similar_tree, "time2", False))
        self.similar_tree.heading("frame2", text="帧号 2",
                                  command=lambda: sort_treeview(self.similar_tree, "frame2", False))
        self.similar_tree.heading("similarity", text="相似度",
                                  command=lambda: sort_treeview(self.similar_tree, "similarity", True))

        # 设置列宽
        self.similar_tree.column("time1", width=120, anchor=tk.CENTER)
        self.similar_tree.column("frame1", width=80, anchor=tk.CENTER)
        self.similar_tree.column("time2", width=120, anchor=tk.CENTER)
        self.similar_tree.column("frame2", width=80, anchor=tk.CENTER)
        self.similar_tree.column("similarity", width=80, anchor=tk.CENTER)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.similar_tree.yview)
        self.similar_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.similar_tree.pack(fill=tk.BOTH, expand=True)

        # 绑定选择事件
        self.similar_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 状态标签
        self.similar_result_count_var = tk.StringVar(value="找到 0 组相似帧")
        result_count_label = ttk.Label(result_frame, textvariable=self.similar_result_count_var)
        result_count_label.pack(anchor=tk.W, pady=5)

        # 创建图像显示面板
        image_frame = ttk.LabelFrame(self.parent, text="关键帧预览", padding=10)
        image_frame.config(width=400)
        image_frame.pack_propagate(False)
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(5, 0))

        # 标题
        ttk.Label(image_frame, text="相似帧预览", style="Header.TLabel").pack(pady=(0, 10))

        # 创建两个图像显示区域
        self.similar_image_frame1 = ttk.Frame(image_frame, height=200)
        self.similar_image_frame1.pack(fill=tk.X, pady=5)
        self.similar_image_frame1.pack_propagate(False)
        self.similar_image_label1 = ttk.Label(self.similar_image_frame1, text="选择结果查看帧",
                                              relief=tk.SUNKEN, anchor=tk.CENTER)
        self.similar_image_label1.pack(fill=tk.BOTH, expand=True)

        self.similar_image_frame2 = ttk.Frame(image_frame, height=200)
        self.similar_image_frame2.pack(fill=tk.X, pady=5)
        self.similar_image_frame2.pack_propagate(False)
        self.similar_image_label2 = ttk.Label(self.similar_image_frame2, text="选择结果查看帧",
                                              relief=tk.SUNKEN, anchor=tk.CENTER)
        self.similar_image_label2.pack(fill=tk.BOTH, expand=True)

        # 时间信息标签
        self.similar_time_info1 = ttk.Label(image_frame, text="", style="Time.TLabel")
        self.similar_time_info1.pack(anchor=tk.W, pady=2)

        self.similar_time_info2 = ttk.Label(image_frame, text="", style="Time.TLabel")
        self.similar_time_info2.pack(anchor=tk.W, pady=2)

        # 操作按钮
        button_frame = ttk.Frame(image_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="导出当前帧",
                   command=self.export_current_frame).pack(fill=tk.X, pady=2)
        ttk.Button(button_frame, text="打开视频位置",
                   command=self.open_video_at_current_frame).pack(fill=tk.X, pady=2)

        # 现在Treeview已创建，再绑定搜索事件
        self.similar_search_var.trace("w", self.filter_results)
        # 清除默认文本（如果需要）
        self.similar_search_var.set("")

    def update_threshold_label(self, *args):
        """更新阈值显示标签"""
        self.similar_threshold_label.config(text=f"当前值: {self.similar_threshold_var.get():.2f}")

    def browse_video(self):
        """浏览视频文件"""
        self.video_path = filedialog.askopenfilename(
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.wmv")]
        )
        if self.video_path:
            self.similar_video_path_var.set(self.video_path)
            self.similar_process_btn.config(state=tk.NORMAL)
            self.similar_status_var.set(f"已选择: {self.video_path.split('/')[-1]}")

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
        self.similar_process_btn.config(state=tk.DISABLED, text="处理中...")
        self.similar_status_var.set("开始分析视频...")
        self.similar_progress_var.set(0)
        self.similar_tree.delete(*self.similar_tree.get_children())

        # 在新线程中处理视频
        threading.Thread(target=self.process_frames, daemon=True).start()

    def process_frames(self):
        """处理视频的线程函数"""
        try:
            # 获取视频帧率
            self.cap = cv2.VideoCapture(self.video_path)
            if not self.cap.isOpened():
                raise Exception("无法打开视频文件")

            self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
            if self.video_fps <= 0:
                self.video_fps = 30  # 默认帧率

            total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.cap.release()

            self.similar_status_var.set(f"视频帧率: {self.video_fps:.2f} FPS | 总帧数: {total_frames}")
            self.parent.update()

            # 提取帧
            self.similar_status_var.set("正在提取视频帧...")
            self.parent.update()

            frames = []
            cap = cv2.VideoCapture(self.video_path)
            frame_count = 0
            extracted_count = 0
            frame_skip = self.similar_frame_skip_var.get()

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_skip == 0:
                    frames.append((frame_count, frame))
                    extracted_count += 1

                frame_count += 1

                # 更新进度
                if frame_count % 50 == 0:
                    progress = min(30, (frame_count / total_frames) * 30)
                    self.similar_progress_var.set(progress)
                    self.similar_status_var.set(f"提取帧: {frame_count}/{total_frames}...")
                    self.parent.update()

            cap.release()
            self.similar_status_var.set(f"已提取 {extracted_count} 帧 (采样间隔: {frame_skip})")
            self.parent.update()

            # 查找相似帧
            self.similar_status_var.set("正在查找相似帧...")
            self.parent.update()

            similar_pairs = []
            total_frames = len(frames)

            for i in range(total_frames):
                for j in range(i + 1, total_frames):
                    # 计算哈希
                    frame1_hash = calculate_frame_hash(frames[i][1])
                    frame2_hash = calculate_frame_hash(frames[j][1])

                    # 计算相似度
                    distance = frame1_hash - frame2_hash
                    max_distance = len(frame1_hash)
                    similarity = 1 - (distance / max_distance)

                    threshold = self.similar_threshold_var.get()
                    if similarity > (1 - threshold):
                        # 计算时间位置
                        time1 = frame_to_time(frames[i][0], self.video_fps)
                        time2 = frame_to_time(frames[j][0], self.video_fps)

                        similar_pairs.append((
                            frames[i][0], time1,
                            frames[j][0], time2,
                            similarity
                        ))

                # 更新进度
                if i % 5 == 0:
                    progress = 30 + (i / total_frames) * 70
                    self.similar_progress_var.set(progress)
                    self.similar_status_var.set(f"查找相似帧: {i + 1}/{total_frames}...")
                    self.parent.update()

            # 保存结果
            self.similar_pairs = similar_pairs
            self.similar_status_var.set(f"完成! 找到 {len(similar_pairs)} 组相似帧")
            self.similar_result_count_var.set(f"找到 {len(similar_pairs)} 组相似帧")

            # 更新结果列表
            self.parent.after(0, self.update_result_list)

        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("处理错误", str(e)))
        finally:
            self.processing = False
            self.parent.after(0, lambda: self.similar_process_btn.config(state=tk.NORMAL, text="查找相似帧"))

    def update_result_list(self):
        """更新结果列表"""
        # 清空现有内容
        for item in self.similar_tree.get_children():
            self.similar_tree.delete(item)

        # 添加新结果
        for pair in self.similar_pairs:
            frame1, time1, frame2, time2, similarity = pair
            self.similar_tree.insert("", tk.END, values=(
                time1,
                frame1,
                time2,
                frame2,
                f"{similarity:.2f}"
            ))

        # 重置搜索
        self.similar_search_var.set("")

    def filter_results(self, *args):
        """过滤结果列表"""
        # 检查组件是否已初始化
        if not hasattr(self, 'similar_tree') or not hasattr(self, 'similar_pairs'):
            return

        search_term = self.similar_search_var.get().lower()
        if not search_term:
            self.update_result_list()
            return

        # 保存原始结果
        if not hasattr(self, 'original_similar_pairs'):
            self.original_similar_pairs = self.similar_pairs.copy()

        # 过滤结果
        filtered_pairs = []
        for pair in self.original_similar_pairs:
            frame1, time1, frame2, time2, similarity = pair
            if (search_term in time1.lower() or
                    search_term in time2.lower() or
                    search_term in str(frame1) or
                    search_term in str(frame2)):
                filtered_pairs.append(pair)

        # 更新列表
        self.similar_pairs = filtered_pairs
        self.update_result_list()
        self.similar_result_count_var.set(f"找到 {len(filtered_pairs)} 组匹配结果")

    def on_tree_select(self, event):
        """当选择结果项时"""
        selected = self.similar_tree.selection()
        if not selected:
            return

        item = self.similar_tree.item(selected[0])
        values = item['values']

        if not values or len(values) < 4:
            return

        # 获取帧号
        try:
            frame1 = int(values[1])
            frame2 = int(values[3])
        except (ValueError, IndexError):
            return

        # 显示图像
        self.display_frames(frame1, frame2,
                            self.similar_image_label1, self.similar_image_frame1,
                            self.similar_image_label2, self.similar_image_frame2)

        # 更新时间信息
        self.similar_time_info1.config(text=f"时间位置: {values[0]} | 帧号: {frame1}")
        self.similar_time_info2.config(text=f"时间位置: {values[2]} | 帧号: {frame2}")

        # 保存当前选择
        self.current_similar_frame_index = frame1

    def display_frames(self, frame1, frame2, label1, frame1_container, label2, frame2_container):
        """显示两个帧的图像"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return

        # 获取第一帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame1)
        ret, img1 = cap.read()
        if ret:
            self.display_image(img1, label1, frame1_container)

        # 获取第二帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame2)
        ret, img2 = cap.read()
        if ret:
            self.display_image(img2, label2, frame2_container)

        cap.release()

    def display_image(self, cv_img, label, container):
        """在标签中显示OpenCV图像"""
        # 转换为RGB
        cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)

        # 调整大小以适应容器
        h, w = cv_img.shape[:2]
        container_width = max(1, container.winfo_width())
        container_height = max(1, container.winfo_height())

        # 确保容器有有效尺寸
        if container_width < 10 or container_height < 10:
            container_width = 300
            container_height = 200

        scale = min(container_width / w, container_height / h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        cv_img = cv2.resize(cv_img, (new_w, new_h))

        # 转换为Tkinter图像
        img = Image.fromarray(cv_img)
        img_tk = ImageTk.PhotoImage(img)

        # 更新标签
        label.config(image=img_tk)
        label.image = img_tk  # 保持引用

    def export_current_frame(self):
        """导出当前显示的帧"""
        if self.current_similar_frame_index < 0:
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
        cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_similar_frame_index)
        ret, frame = cap.read()
        cap.release()

        if ret:
            cv2.imwrite(file_path, frame)
            messagebox.showinfo("成功", f"帧已保存至:\n{file_path}")
        else:
            messagebox.showerror("错误", "无法获取当前帧")

    def open_video_at_current_frame(self):
        """在视频播放器中打开当前帧位置"""
        if self.current_similar_frame_index < 0:
            messagebox.showinfo("提示", "请先选择一个结果")
            return

        # 计算时间位置
        seconds = self.current_similar_frame_index / self.video_fps
        time_str = frame_to_time(self.current_similar_frame_index, self.video_fps)

        # 显示消息
        messagebox.showinfo("操作提示",
                            f"在视频播放器中打开此视频\n跳转到时间位置: {time_str}")