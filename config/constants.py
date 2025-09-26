"""常量配置模块"""


# 默认视频参数
DEFAULT_FPS = 30
DEFAULT_FRAME_SKIP = 10

# UI样式配置
UI_STYLES = {
    "TFrame": {"background": "#f0f0f0"},
    "TButton": {"font": ("Arial", 10), "padding": 5},
    "TLabel": {"background": "#f0f0f0", "font": ("Arial", 10)},
    "Header.TLabel": {"font": ("Arial", 12, "bold"), "foreground": "#1a5fb4"},
    "Result.TLabel": {"font": ("Arial", 10)},
    "Time.TLabel": {"font": ("Arial", 10, "bold"), "foreground": "#d9534f"},
    "TNotebook.Tab": {"font": ("Arial", 10)}
}

# 相似帧查找默认参数
SIMILAR_FRAME_DEFAULTS = {
    "threshold": 0.15,
    "min_threshold": 0.05,
    "max_threshold": 0.3,
    "frame_skip": 10
}

# 首帧比较默认参数
FIRST_FRAME_DEFAULTS = {
    "threshold": 0.2,
    "min_threshold": 0.05,
    "max_threshold": 0.5,
    "frame_skip": 5
}

# 循环视频检测默认参数
LOOPING_VIDEO_DEFAULTS = {
    "ssim_threshold": 0.85,
    "min_ssim_threshold": 0.5,
    "max_ssim_threshold": 0.99,
    "frame_skip": 30,
    "search_range": 300
}