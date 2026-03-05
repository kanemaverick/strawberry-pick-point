# pick_images_for_pose.py
# 从 Detection 数据集中按间隔抽取图片，避免视频相邻帧重复
# 运行：conda activate yolov11 → python pick_images_for_pose.py

import os
import shutil
from pathlib import Path

SRC = r"C:\Users\xzKan\Desktop\机械臂草莓\strawberry-dataset-for-object-detection-DatasetNinja\training\img"
DST = r"C:\Users\xzKan\Desktop\机械臂草莓\pose_annotation_images"
N = 200  # 目标图片数量
STRIDE = 3  # 每隔 3 帧取一张（654张 / 3 = 218张，略多于200，够用）

os.makedirs(DST, exist_ok=True)

# 按文件名数字排序（0.jpg, 1.jpg, 2.jpg ... 保持视频帧顺序）
imgs = sorted(
    [f for f in os.listdir(SRC) if f.lower().endswith(".jpg")],
    key=lambda x: int(Path(x).stem) if Path(x).stem.isdigit() else 0,
)

# 按间隔取帧
strided = imgs[::STRIDE]

# 如果间隔取完还不够 N 张，就全用；如果超过 N 张，截取前 N 张
selected = strided[:N]

# 清空目标文件夹（避免和旧文件混在一起）
for f in os.listdir(DST):
    os.remove(os.path.join(DST, f))

for f in selected:
    shutil.copy(os.path.join(SRC, f), os.path.join(DST, f))

print(f"原始图片总数:  {len(imgs)} 张")
print(f"抽帧间隔:      每 {STRIDE} 帧取 1 张")
print(f"抽取结果:      {len(selected)} 张（已复制到 {DST}）")
print(f"相邻图片间隔:  约 {STRIDE} 帧，内容差异明显，不会有重复感")
print(f"\n下一步：上传到 CVAT 标注")
