import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import threading

# 尝试导入skimage.metrics.structural_similarity
try:
    from skimage.metrics import structural_similarity as ssim
except ImportError:
    # 如果新版本不存在，尝试从旧版本导入
    try:
        from skimage.measure import compare_ssim as ssim
    except ImportError:
        ssim = None

from utils.helpers import frame_to_time, sort_treeview
from config.constants import LOOPING_VIDEO_DEFAULTS


class LoopingVideoTab:
    def __init__(self, parent):
        self.parent = parent
        self.init_ui()
        
        # 初始化变量
        self.video_path = ""
        self.video_fps = 30
        self.cap = None
        self.processing = False
        self.looping_pairs = []
        self.current_looping_pair = None

    def init_ui(self):
        """初始化无缝循环视频检测标签页"""
        # 创建控制面板
        control_frame = ttk.LabelFrame(self.parent, text="视频设置", padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5), expand=False)

        # 视频选择
        ttk.Label(control_frame, text="选择视频文件:", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self.looping_video_path_var = tk.StringVar()
        video_entry = ttk.Entry(control_frame, textvariable=self.looping_video_path_var, width=30)
        video_entry.pack(fill=tk.X, pady=2)
        ttk.Button(control_frame, text="浏览...", command=self.browse_video).pack(fill=tk.X, pady=2)

        # 参数设置
        ttk.Label(control_frame, text="参数设置:", style="Header.TLabel").pack(anchor=tk.W, pady=(15, 5))

        # SSIM阈值
        ttk.Label(control_frame, text="SSIM阈值 (0-1):").pack(anchor=tk.W, pady=2)
        self.ssim_threshold_var = tk.DoubleVar(value=LOOPING_VIDEO_DEFAULTS["ssim_threshold"])
        ssim_threshold_slider = ttk.Scale(control_frame, from_=LOOPING_VIDEO_DEFAULTS["min_ssim_threshold"], 
                                          to=LOOPING_VIDEO_DEFAULTS["max_ssim_threshold"],
                                          variable=self.ssim_threshold_var, orient=tk.HORIZONTAL)
        ssim_threshold_slider.pack(fill=tk.X, pady=2)
        self.ssim_threshold_label = ttk.Label(control_frame, 
                                              text=f"当前值: {self.ssim_threshold_var.get():.2f}")
        self.ssim_threshold_label.pack(anchor=tk.W, pady=2)

        # 帧采样间隔
        ttk.Label(control_frame, text="帧采样间隔:").pack(anchor=tk.W, pady=2)
        self.looping_frame_skip_var = tk.IntVar(value=LOOPING_VIDEO_DEFAULTS["frame_skip"])
        frame_skip_spinbox = ttk.Spinbox(control_frame, from_=1, to=100,
                                         textvariable=self.looping_frame_skip_var, width=10)
        frame_skip_spinbox.pack(fill=tk.X, pady=2)

        # 搜索范围
        ttk.Label(control_frame, text="搜索范围 (帧数):").pack(anchor=tk.W, pady=2)
        self.search_range_var = tk.IntVar(value=LOOPING_VIDEO_DEFAULTS["search_range"])
        search_range_spinbox = ttk.Spinbox(control_frame, from_=10, to=1000,
                                           textvariable=self.search_range_var, width=10)
        search_range_spinbox.pack(fill=tk.X, pady=2)

        # 操作按钮
        ttk.Label(control_frame, text="操作:", style="Header.TLabel").pack(anchor=tk.W, pady=(15, 5))
        self.looping_process_btn = ttk.Button(control_frame, text="检测循环片段",
                                              command=self.start_processing, state=tk.DISABLED)
        self.looping_process_btn.pack(fill=tk.X, pady=5)

        self.looping_status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(control_frame, textvariable=self.looping_status_var,
                                 wraplength=200, justify=tk.LEFT)
        status_label.pack(fill=tk.X, pady=10)

        # 进度条
        self.looping_progress_var = tk.DoubleVar()
        self.looping_progress_bar = ttk.Progressbar(control_frame, variable=self.looping_progress_var,
                                                    maximum=100, mode="determinate")
        self.looping_progress_bar.pack(fill=tk.X, pady=5)

        # 绑定阈值滑块事件
        self.ssim_threshold_var.trace("w", self.update_ssim_threshold_label)

        # 创建结果面板
        result_frame = ttk.LabelFrame(self.parent, text="检测结果", padding=10)
        result_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 结果列表
        columns = ("start_time", "start_frame", "end_time", "end_frame", "ssim_value")
        self.looping_tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="browse")

        # 定义列
        self.looping_tree.heading("start_time", text="开始时间",
                                  command=lambda: sort_treeview(self.looping_tree, "start_time", False))
        self.looping_tree.heading("start_frame", text="开始帧",
                                  command=lambda: sort_treeview(self.looping_tree, "start_frame", False))
        self.looping_tree.heading("end_time", text="结束时间",
                                  command=lambda: sort_treeview(self.looping_tree, "end_time", False))
        self.looping_tree.heading("end_frame", text="结束帧",
                                  command=lambda: sort_treeview(self.looping_tree, "end_frame", False))
        self.looping_tree.heading("ssim_value", text="SSIM值",
                                  command=lambda: sort_treeview(self.looping_tree, "ssim_value", True))

        # 设置列宽
        self.looping_tree.column("start_time", width=120, anchor=tk.CENTER)
        self.looping_tree.column("start_frame", width=80, anchor=tk.CENTER)
        self.looping_tree.column("end_time", width=120, anchor=tk.CENTER)
        self.looping_tree.column("end_frame", width=80, anchor=tk.CENTER)
        self.looping_tree.column("ssim_value", width=80, anchor=tk.CENTER)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.looping_tree.yview)
        self.looping_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.looping_tree.pack(fill=tk.BOTH, expand=True)

        # 绑定选择事件
        self.looping_tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 状态标签
        self.looping_result_count_var = tk.StringVar(value="找到 0 个循环片段")
        result_count_label = ttk.Label(result_frame, textvariable=self.looping_result_count_var)
        result_count_label.pack(anchor=tk.W, pady=5)

        # 创建图像显示面板
        image_frame = ttk.LabelFrame(self.parent, text="关键帧预览", padding=10)
        image_frame.config(width=400)
        image_frame.pack_propagate(False)
        image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(5, 0))

        # 标题
        ttk.Label(image_frame, text="循环片段预览", style="Header.TLabel").pack(pady=(0, 10))

        # 创建两个图像显示区域
        self.looping_image_frame1 = ttk.Frame(image_frame, height=200)
        self.looping_image_frame1.pack(fill=tk.X, pady=5)
        self.looping_image_frame1.pack_propagate(False)
        self.looping_image_label1 = ttk.Label(self.looping_image_frame1, text="选择结果查看开始帧",
                                              relief=tk.SUNKEN, anchor=tk.CENTER)
        self.looping_image_label1.pack(fill=tk.BOTH, expand=True)

        self.looping_image_frame2 = ttk.Frame(image_frame, height=200)
        self.looping_image_frame2.pack(fill=tk.X, pady=5)
        self.looping_image_frame2.pack_propagate(False)
        self.looping_image_label2 = ttk.Label(self.looping_image_frame2, text="选择结果查看结束帧",
                                              relief=tk.SUNKEN, anchor=tk.CENTER)
        self.looping_image_label2.pack(fill=tk.BOTH, expand=True)

        # 时间信息标签
        self.looping_time_info1 = ttk.Label(image_frame, text="", style="Time.TLabel")
        self.looping_time_info1.pack(anchor=tk.W, pady=2)

        self.looping_time_info2 = ttk.Label(image_frame, text="", style="Time.TLabel")
        self.looping_time_info2.pack(anchor=tk.W, pady=2)

        # 操作按钮
        button_frame = ttk.Frame(image_frame)
        button_frame.pack(fill=tk.X, pady=10)

        self.generate_looping_btn = ttk.Button(button_frame, text="生成循环视频",
                                               command=self.generate_looping_video, state=tk.DISABLED)
        self.generate_looping_btn.pack(fill=tk.X, pady=2)

    def update_ssim_threshold_label(self, *args):
        """更新SSIM阈值显示标签"""
        self.ssim_threshold_label.config(text=f"当前值: {self.ssim_threshold_var.get():.2f}")

    def browse_video(self):
        """浏览视频文件"""
        self.video_path = filedialog.askopenfilename(
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.wmv")]
        )
        if self.video_path:
            self.looping_video_path_var.set(self.video_path)
            self.looping_process_btn.config(state=tk.NORMAL)
            self.looping_status_var.set(f"已选择: {self.video_path.split('/')[-1]}")

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

        # 检查SSIM是否可用
        if ssim is None:
            messagebox.showerror("错误", "需要安装scikit-image库来计算SSIM值:\npip install scikit-image")
            return

        self.processing = True
        self.looping_process_btn.config(state=tk.DISABLED, text="处理中...")
        self.looping_status_var.set("开始分析视频...")
        self.looping_progress_var.set(0)
        self.looping_tree.delete(*self.looping_tree.get_children())

        # 在新线程中处理视频
        threading.Thread(target=self.process_video, daemon=True).start()

    def process_video(self):
        """处理无缝循环视频检测的线程函数"""
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

            self.looping_status_var.set(f"视频帧率: {self.video_fps:.2f} FPS | 总帧数: {total_frames}")
            self.parent.update()

            # 查找循环片段
            self.looping_status_var.set("正在查找循环片段...")
            self.parent.update()

            looping_pairs = []
            frame_skip = self.looping_frame_skip_var.get()
            search_range = self.search_range_var.get()
            ssim_threshold = self.ssim_threshold_var.get()

            cap = cv2.VideoCapture(self.video_path)
            
            frame_count = 0
            processed_frames = 0
            
            # 用于存储帧的缓存
            frame_cache = {}
            cache_limit = 50  # 限制缓存帧的数量
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_skip == 0:
                    # 将当前帧转换为灰度图用于SSIM比较
                    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    # 调整图像大小以提高处理速度并确保一致性
                    h, w = gray_frame.shape[:2]
                    if w > 480:  # 将宽度调整为480像素以提高处理速度
                        scale = 480 / w
                        new_w = 480
                        new_h = int(h * scale)
                        gray_frame_resized = cv2.resize(gray_frame, (new_w, new_h))
                    else:
                        gray_frame_resized = gray_frame
                    
                    # 在搜索范围内查找相似帧
                    start_search = max(0, frame_count - search_range)
                    best_match = None
                    best_ssim = 0
                    
                    # 检查缓存中的帧
                    keys_to_remove = []
                    for prev_frame_num in frame_cache:
                        if prev_frame_num < start_search:
                            # 标记超出搜索范围的帧以便删除
                            keys_to_remove.append(prev_frame_num)
                            continue
                            
                        if prev_frame_num >= frame_count:
                            continue
                        
                        # 获取之前帧
                        prev_gray = frame_cache[prev_frame_num]
                        
                        # 计算SSIM值
                        try:
                            # 确保两个图像尺寸相同
                            if gray_frame_resized.shape != prev_gray.shape:
                                # 调整较小的图像以匹配较大的图像
                                if gray_frame_resized.shape[0] * gray_frame_resized.shape[1] > prev_gray.shape[0] * prev_gray.shape[1]:
                                    prev_gray = cv2.resize(prev_gray, (gray_frame_resized.shape[1], gray_frame_resized.shape[0]))
                                else:
                                    gray_frame_resized = cv2.resize(gray_frame, (prev_gray.shape[1], prev_gray.shape[0]))
                            
                            ssim_value = ssim(prev_gray, gray_frame_resized)
                        except Exception as e:
                            # 如果SSIM计算失败，跳过这一对帧
                            continue
                        
                        if ssim_value >= ssim_threshold and ssim_value > best_ssim:
                            best_ssim = ssim_value
                            best_match = prev_frame_num
                    
                    # 删除超出范围的帧
                    for key in keys_to_remove:
                        del frame_cache[key]
                    
                    # 如果找到匹配
                    if best_match is not None:
                        # 找到一个潜在的循环片段
                        time1 = frame_to_time(best_match, self.video_fps)
                        time2 = frame_to_time(frame_count, self.video_fps)
                        
                        looping_pairs.append((
                            best_match, time1,
                            frame_count, time2,
                            best_ssim
                        ))
                        
                        # 清理缓存中已匹配的帧，但保留一些用于后续比较
                        # 只保留最近的几个帧
                        if len(frame_cache) > cache_limit:
                            # 删除最旧的帧
                            oldest_key = min(frame_cache.keys())
                            del frame_cache[oldest_key]
                    else:
                        # 将当前帧添加到缓存中供后续比较
                        frame_cache[frame_count] = gray_frame_resized
                
                frame_count += 1
                processed_frames += 1

                # 更新进度
                if processed_frames % 10 == 0:
                    progress = (frame_count / total_frames) * 100
                    self.looping_progress_var.set(progress)
                    self.looping_status_var.set(f"处理帧: {frame_count}/{total_frames}...")
                    self.parent.update()

            cap.release()
            
            # 保存结果
            self.looping_pairs = looping_pairs
            self.looping_status_var.set(f"完成! 找到 {len(looping_pairs)} 个循环片段")
            self.looping_result_count_var.set(f"找到 {len(looping_pairs)} 个循环片段")

            # 更新结果列表
            self.parent.after(0, self.update_result_list)

        except Exception as e:
            self.parent.after(0, lambda: messagebox.showerror("处理错误", str(e)))
        finally:
            self.processing = False
            self.parent.after(0, lambda: self.looping_process_btn.config(state=tk.NORMAL, text="检测循环片段"))

    def update_result_list(self):
        """更新结果列表"""
        # 清空现有内容
        for item in self.looping_tree.get_children():
            self.looping_tree.delete(item)

        # 添加新结果，按SSIM值排序
        sorted_pairs = sorted(self.looping_pairs, key=lambda x: x[4], reverse=True)
        
        for pair in sorted_pairs:
            frame1, time1, frame2, time2, ssim_value = pair
            self.looping_tree.insert("", tk.END, values=(
                time1,
                frame1,
                time2,
                frame2,
                f"{ssim_value:.3f}"
            ))
            
    def on_tree_select(self, event):
        """当选中结果时"""
        selected = self.looping_tree.selection()
        if not selected:
            return

        item = self.looping_tree.item(selected[0])
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
                            self.looping_image_label1, self.looping_image_frame1,
                            self.looping_image_label2, self.looping_image_frame2)

        # 更新时间信息
        self.looping_time_info1.config(text=f"开始时间: {values[0]} | 帧号: {frame1}")
        self.looping_time_info2.config(text=f"结束时间: {values[2]} | 帧号: {frame2}")

        # 保存当前选择
        self.current_looping_pair = (frame1, frame2)
        self.generate_looping_btn.config(state=tk.NORMAL)

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

    def generate_looping_video(self):
        """生成循环视频"""
        if not self.current_looping_pair:
            messagebox.showinfo("提示", "请先选择一个循环片段")
            return

        start_frame, end_frame = self.current_looping_pair
        
        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4文件", "*.mp4"), ("AVI文件", "*.avi")]
        )

        if not file_path:
            return

        try:
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

            # 写入循环片段
            total_frames = end_frame - start_frame + 1
            for i in range(start_frame, end_frame + 1):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    out.write(frame)

                # 更新进度
                progress = ((i - start_frame + 1) / total_frames) * 100
                self.looping_progress_var.set(progress)
                self.looping_status_var.set(f"生成视频: {i - start_frame + 1}/{total_frames}...")
                self.parent.update()

            # 释放资源
            cap.release()
            out.release()

            # 完成
            self.looping_status_var.set(f"循环视频已保存至: {file_path}")
            messagebox.showinfo("成功", f"循环视频已成功生成!\n{file_path}")

        except Exception as e:
            messagebox.showerror("生成错误", f"生成循环视频时出错:\n{str(e)}")