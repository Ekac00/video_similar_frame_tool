# 🎉 视频相似帧工具

一个使用hash和SSIM算法的简易视频相似帧小工（shi）具（shan）

## 功能特性

- **首帧比较**: 找到与视频第一帧相似的帧
- **无缝循环检测**: 检测视频中可以无缝循环播放的片段
- **视频片段生成**: 从指定帧生成视频片段
- **关键帧导出**: 导出选定的关键帧

## 使用方法

在[Releases](https://github.com/Ekac00/video_similar_frame_tool/releases)下载打包过的程序或使用源码运行

1. 下载项目源码


2. 安装依赖包:
```bash
pip install opencv-python pillow imagehash scikit-image
```

3. 运行程序:
```bash
python main.py
```

4. 在GUI界面中选择视频文件并使用相应功能进行分析。

## 技术栈

- Python 3.8+
- OpenCV
- Pillow
- imagehash
- scikit-image

## 贡献

欢迎贡献代码和反馈问题！