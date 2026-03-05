# merge_and_split.py
# 合并两个来源的数据，重新 8:2 划分训练/验证集
#
# 来源1：CVAT 手动标注（草莓采摘点精确标注，194 张）
#   图片：pose_annotation_images/
#   标注：yolo_pose_labels/（由 cvat_xml2yolo_pose.py 生成）
#
# 来源2：DatasetNinja 在线数据集（ripe+peduncle 自动匹配，798 张）
#   图片：datasetninja_images/training/ + datasetninja_images/validation/
#   标注：datasetninja_labels/training/ + datasetninja_labels/validation/
#
# 输出：strawberry_pose_dataset_v2/（与旧数据集同级，不覆盖旧版）
#
# 运行方式（Anaconda Prompt）：
#   conda activate yolov11
#   python "C:\Users\xzKan\Desktop\机械臂草莓\autodl_scripts\merge_and_split.py"

import os
import shutil
import random
from pathlib import Path

# ============================================================
# 路径配置
BASE = r"C:\Users\xzKan\Desktop\机械臂草莓"

# 来源1：CVAT 手动标注
CVAT_IMAGES = os.path.join(BASE, "pose_annotation_images")
CVAT_LABELS = os.path.join(BASE, "yolo_pose_labels")

# 来源2：DatasetNinja 自动转换
DN_IMAGES_TRAIN = os.path.join(BASE, "datasetninja_images", "training")
DN_LABELS_TRAIN = os.path.join(BASE, "datasetninja_labels", "training")
DN_IMAGES_VAL = os.path.join(BASE, "datasetninja_images", "validation")
DN_LABELS_VAL = os.path.join(BASE, "datasetninja_labels", "validation")

# 输出
DST_ROOT = os.path.join(BASE, "strawberry_pose_dataset_v2")
# ============================================================

TRAIN_RATIO = 0.8
random.seed(42)


def collect_pairs(img_dir, lbl_dir, prefix=""):
    """
    收集 (图片路径, 标注路径) 对，只保留两者都存在的。
    prefix：用于区分同名文件（不同来源可能有同名如 0.jpg），
            添加前缀后复制到目标目录以避免冲突。
    返回：[(src_img_path, src_lbl_path, dst_img_name, dst_lbl_name)]
    """
    pairs = []
    for img_file in sorted(Path(img_dir).glob("*")):
        if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        lbl_file = Path(lbl_dir) / (img_file.stem + ".txt")
        if not lbl_file.exists():
            continue
        dst_stem = prefix + img_file.stem if prefix else img_file.stem
        dst_img_name = dst_stem + img_file.suffix.lower()
        dst_lbl_name = dst_stem + ".txt"
        pairs.append((str(img_file), str(lbl_file), dst_img_name, dst_lbl_name))
    return pairs


def main():
    print("=== 合并数据集并重新划分 ===\n")

    # 收集所有样本
    # CVAT 来源加前缀 "cvat_"
    cvat_pairs = collect_pairs(CVAT_IMAGES, CVAT_LABELS, prefix="cvat_")
    print(f"CVAT 手动标注：{len(cvat_pairs)} 张")

    # DatasetNinja 来源加前缀 "dn_"
    dn_train_pairs = collect_pairs(DN_IMAGES_TRAIN, DN_LABELS_TRAIN, prefix="dn_")
    dn_val_pairs = collect_pairs(DN_IMAGES_VAL, DN_LABELS_VAL, prefix="dn_v_")
    dn_all = dn_train_pairs + dn_val_pairs
    print(f"DatasetNinja 在线数据集：{len(dn_all)} 张")

    all_pairs = cvat_pairs + dn_all
    print(f"\n合计：{len(all_pairs)} 张\n")

    # 随机打乱并 8:2 划分
    random.shuffle(all_pairs)
    n_train = int(len(all_pairs) * TRAIN_RATIO)
    split_dict = {
        "train": all_pairs[:n_train],
        "val": all_pairs[n_train:],
    }
    print(f"训练集：{len(split_dict['train'])} 张")
    print(f"验证集：{len(split_dict['val'])} 张\n")

    # 清理旧输出（如存在）并重建目录
    if os.path.exists(DST_ROOT):
        shutil.rmtree(DST_ROOT)
        print(f"已清理旧目录：{DST_ROOT}")

    for split_name, pairs in split_dict.items():
        img_out = os.path.join(DST_ROOT, "images", split_name)
        lbl_out = os.path.join(DST_ROOT, "labels", split_name)
        os.makedirs(img_out, exist_ok=True)
        os.makedirs(lbl_out, exist_ok=True)

        for src_img, src_lbl, dst_img_name, dst_lbl_name in pairs:
            shutil.copy2(src_img, os.path.join(img_out, dst_img_name))
            shutil.copy2(src_lbl, os.path.join(lbl_out, dst_lbl_name))

    print(f"=== 完成 ===")
    print(f"数据集保存在：{DST_ROOT}")
    print(f"目录结构：")
    print(f"  {DST_ROOT}/")
    print(f"  ├── images/train/  ({len(split_dict['train'])} 张)")
    print(f"  ├── images/val/    ({len(split_dict['val'])} 张)")
    print(f"  ├── labels/train/  ({len(split_dict['train'])} 个 .txt)")
    print(f"  └── labels/val/    ({len(split_dict['val'])} 个 .txt)")
    print(
        f"\n下一步：修改 train_pose_local.py 里的 DATASET_YAML 指向新 yaml，然后运行训练"
    )


if __name__ == "__main__":
    main()
