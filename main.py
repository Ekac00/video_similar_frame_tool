import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# 添加必要的导入
try:
    from skimage.metrics import structural_similarity as ssim
except ImportError:
    pass

try:
    from skimage.measure import compare_ssim
except ImportError:
    pass

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.similar_frame_tab import SimilarFrameTab
from ui.first_frame_tab import FirstFrameTab
from ui.looping_video_tab import LoopingVideoTab
from config.constants import UI_STYLES


class VideoAnalysisTool:
    def __init__(self, root):
        self.root = root
        self.root.title("视频分析工具")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # 样式设置
        self.style = ttk.Style()
        for style_name, style_config in UI_STYLES.items():
            self.style.configure(style_name, **style_config)

        # 创建主框架
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建标签页
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 创建三个标签页
        self.similar_frame_tab = ttk.Frame(self.notebook)
        self.first_frame_tab = ttk.Frame(self.notebook)
        self.looping_video_tab = ttk.Frame(self.notebook)

        # 添加标签页
        self.notebook.add(self.similar_frame_tab, text="相似帧查找")
        self.notebook.add(self.first_frame_tab, text="首帧比较与片段生成")
        self.notebook.add(self.looping_video_tab, text="无缝循环视频检测")

        # 初始化三个功能模块
        self.similar_frame_module = SimilarFrameTab(self.similar_frame_tab)
        self.first_frame_module = FirstFrameTab(self.first_frame_tab)
        self.looping_video_module = LoopingVideoTab(self.looping_video_tab)


if __name__ == "__main__":
    # 检查必要的依赖
    try:
        import cv2
        import numpy as np
        import imagehash
        from PIL import Image, ImageTk
    except ImportError as e:
        messagebox.showerror("依赖缺失", f"需要安装必要的库:\n{str(e)}")
        exit(1)

    try:
        # 尝试导入skimage.metrics.structural_similarity
        try:
            from skimage.metrics import structural_similarity as ssim
        except ImportError:
            # 如果新版本不存在，尝试从旧版本导入
            try:
                from skimage.measure import compare_ssim as ssim
            except ImportError:
                ssim = None
    except ImportError as e:
        messagebox.showerror("依赖缺失", f"需要安装scikit-image库:\n{str(e)}")
        exit(1)

    root = tk.Tk()
    app = VideoAnalysisTool(root)
    root.mainloop()