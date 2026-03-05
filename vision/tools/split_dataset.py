# split_dataset.py
# 将标注好的图片和 label 按 8:2 划分为训练集和验证集
# 本地 Windows 运行：python split_dataset.py
# 不需要安装额外库

import os
import shutil
import random
from pathlib import Path

# ============================================================
# ★ 修改这三个路径 ★
SRC_IMAGES = r"C:\Users\xzKan\Desktop\机械臂草莓\pose_annotation_images"  # 待标注图片（本地原图）
SRC_LABELS = (
    r"C:\Users\xzKan\Desktop\机械臂草莓\yolo_pose_labels"  # cvat_xml2yolo_pose.py 输出
)
DST_ROOT = (
    r"C:\Users\xzKan\Desktop\机械臂草莓\strawberry_pose_dataset"  # 最终训练数据集
)
# ============================================================

TRAIN_RATIO = 0.8  # 80% 训练集，20% 验证集
random.seed(42)  # 固定随机种子，保证可复现


def split():
    # 找所有图片
    imgs = sorted(
        [
            f
            for f in os.listdir(SRC_IMAGES)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]
    )
    print(f"找到图片总数：{len(imgs)}")

    # 只保留有对应 label 的图片（排除没有标注的图片）
    valid_imgs = []
    for fname in imgs:
        stem = Path(fname).stem
        if os.path.exists(os.path.join(SRC_LABELS, stem + ".txt")):
            valid_imgs.append(fname)
        else:
            print(f"  跳过（无标注）：{fname}")

    print(f"有标注的图片：{len(valid_imgs)} 张")

    # 随机打乱并划分
    random.shuffle(valid_imgs)
    n_train = int(len(valid_imgs) * TRAIN_RATIO)
    splits = {"train": valid_imgs[:n_train], "val": valid_imgs[n_train:]}
    print(f"训练集：{len(splits['train'])} 张")
    print(f"验证集：{len(splits['val'])} 张")

    # 创建目录并复制文件
    for split_name, files in splits.items():
        img_dir = os.path.join(DST_ROOT, "images", split_name)
        lbl_dir = os.path.join(DST_ROOT, "labels", split_name)
        os.makedirs(img_dir, exist_ok=True)
        os.makedirs(lbl_dir, exist_ok=True)

        for fname in files:
            stem = Path(fname).stem
            shutil.copy(os.path.join(SRC_IMAGES, fname), os.path.join(img_dir, fname))
            shutil.copy(
                os.path.join(SRC_LABELS, stem + ".txt"),
                os.path.join(lbl_dir, stem + ".txt"),
            )

    print(f"\n=== 划分完成 ===")
    print(f"数据集保存在：{DST_ROOT}")
    print(f"目录结构：")
    print(f"  {DST_ROOT}/")
    print(f"  ├── images/train/  ({len(splits['train'])} 张图片)")
    print(f"  ├── images/val/    ({len(splits['val'])} 张图片)")
    print(f"  ├── labels/train/  ({len(splits['train'])} 个 .txt)")
    print(f"  └── labels/val/    ({len(splits['val'])} 个 .txt)")
    print(f"\n下一步：运行 train_pose_local.py 开始训练")


if __name__ == "__main__":
    split()
