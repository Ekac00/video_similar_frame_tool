# 视频相似帧分析工具

## 项目简介

这是一个用于分析视频中相似帧的Python工具，可以帮助用户快速找到视频中的重复或相似内容。

## 功能特性

- **首帧比较**: 找到与视频第一帧相似的帧
- **无缝循环检测**: 检测视频中可以无缝循环播放的片段
- **视频片段生成**: 从指定帧生成视频片段
- **关键帧导出**: 导出选定的关键帧

## 使用方法

1. 安装依赖包:
```bash
pip install opencv-python pillow imagehash scikit-image
```

2. 运行程序:
```bash
python main.py
```

3. 在GUI界面中选择视频文件并使用相应功能进行分析。

## 技术栈

- Python 3.8+
- OpenCV
- Pillow
- imagehash
- scikit-image

## 贡献

欢迎贡献代码和反馈问题！

## 许可证

MIT许可证