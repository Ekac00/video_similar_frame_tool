import cv2
import imagehash
from PIL import Image
from datetime import timedelta


def frame_to_time(frame_num, fps):
    """将帧号转换为时间字符串 (HH:MM:SS)"""
    seconds = frame_num / fps
    return str(timedelta(seconds=seconds)).split('.')[0]


def calculate_frame_hash(frame):
    """计算帧的哈希值"""
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    return imagehash.average_hash(img)


def sort_treeview(tree, col, reverse):
    """排序结果列表"""
    # 检查tree是否有效
    if not tree or not hasattr(tree, 'get_children'):
        return

    data = []
    for child in tree.get_children():
        values = tree.item(child, 'values')
        if col == "similarity" and values and len(values) > tree["columns"].index(col):
            try:
                data.append((float(values[tree["columns"].index(col)]), child))
            except (ValueError, IndexError):
                data.append((0.0, child))
        elif values and len(values) > tree["columns"].index(col):
            data.append((values[tree["columns"].index(col)], child))

    data.sort(reverse=reverse)

    for idx, (val, child) in enumerate(data):
        tree.move(child, '', idx)

    # 切换排序方向
    tree.heading(col, command=lambda: sort_treeview(tree, col, not reverse))