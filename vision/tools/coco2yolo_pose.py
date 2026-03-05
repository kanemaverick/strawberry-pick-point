# coco2yolo_pose.py
# 将 CVAT 导出的 COCO Keypoints 格式转换为 YOLO Pose 格式
#
# 支持两种标注情况：
#   情况A：ripe BBox 内嵌了关键点（CVAT Skeleton 方式）
#   情况B：ripe BBox 和 grasp_point 是两个独立 Label（推荐方式）
#           - 有 grasp_point 的 ripe → kp_v=2（可见）
#           - 没有 grasp_point 的 ripe（看不清采摘点）→ kp_v=0（不可见，坐标填0）
#             YOLO 训练时 kp_v=0 的关键点会被跳过，不计入 pose loss，
#             但 BBox 仍然参与 box loss，不会浪费这些标注
#
# 本地 Windows 运行：python coco2yolo_pose.py

import json
import os
from pathlib import Path
from collections import defaultdict

# ============================================================
# ★ 修改这两个路径 ★
COCO_JSON_PATH = r"C:\path\to\exported\annotations\instances_default.json"
OUTPUT_LABELS_DIR = r"C:\path\to\yolo_pose_labels"

# CVAT 里两个 Label 的名称（如果你改过名字，这里同步修改）
BBOX_LABEL_NAME = "ripe"  # 画矩形框用的 Label
POINT_LABEL_NAME = "grasp_point"  # 标采摘点用的 Label
# ============================================================


def point_in_box(px, py, bx, by, bw, bh, margin=0.2):
    """判断点 (px,py) 是否在 BBox 附近（允许向外扩展 margin 比例）"""
    mx = bw * margin
    my = bh * margin
    return (bx - mx <= px <= bx + bw + mx) and (by - my <= py <= by + bh + my)


def convert():
    print(f"读取 COCO 标注文件：{COCO_JSON_PATH}")
    with open(COCO_JSON_PATH, "r", encoding="utf-8") as f:
        coco = json.load(f)

    id2img = {img["id"]: img for img in coco["images"]}
    print(f"图片总数：{len(id2img)}")

    # 解析类别，找到 ripe 和 grasp_point 对应的 category_id
    print("\n检测到的类别：")
    bbox_cat_id = None
    point_cat_id = None
    for cat in coco["categories"]:
        print(f"  {cat['id']}: {cat['name']}")
        if cat["name"] == BBOX_LABEL_NAME:
            bbox_cat_id = cat["id"]
        if cat["name"] == POINT_LABEL_NAME:
            point_cat_id = cat["id"]

    if bbox_cat_id is None:
        print(f"\n错误：没找到名为 '{BBOX_LABEL_NAME}' 的类别，请检查 CVAT Label 名称")
        return
    if point_cat_id is None:
        print(f"\n警告：没找到名为 '{POINT_LABEL_NAME}' 的类别")
        print("  → 将按情况A处理（关键点内嵌在 ripe annotation 里）")

    os.makedirs(OUTPUT_LABELS_DIR, exist_ok=True)

    # 按 image_id 分组
    img2anns = defaultdict(list)
    for ann in coco["annotations"]:
        img2anns[ann["image_id"]].append(ann)

    count_img = 0
    count_with_kp = 0  # 有采摘点的草莓
    count_without_kp = 0  # 没有采摘点的草莓（看不清，kp_v=0 保留）
    count_skip = 0  # 真正跳过的（BBox 越界等）

    for img_id, img_info in id2img.items():
        W = img_info["width"]
        H = img_info["height"]
        file_stem = Path(img_info["file_name"]).stem
        label_path = os.path.join(OUTPUT_LABELS_DIR, file_stem + ".txt")

        anns = img2anns[img_id]

        # 分离 ripe BBox 和 grasp_point
        ripe_anns = [a for a in anns if a["category_id"] == bbox_cat_id]
        point_anns = (
            [a for a in anns if a["category_id"] == point_cat_id]
            if point_cat_id
            else []
        )

        lines = []
        for ann in ripe_anns:
            bx, by, bw, bh = ann["bbox"]
            xc = (bx + bw / 2) / W
            yc = (by + bh / 2) / H
            nw = bw / W
            nh = bh / H

            # BBox 边界检查
            if not (0 < xc < 1 and 0 < yc < 1 and 0 < nw <= 1 and 0 < nh <= 1):
                print(f"  警告：{file_stem} BBox 超出范围，已跳过")
                count_skip += 1
                continue

            # --- 寻找对应的采摘点 ---
            kp_x, kp_y, kp_v = 0.0, 0.0, 0  # 默认：不可见

            if point_cat_id is not None:
                # 情况B：grasp_point 是独立 Label
                # 找空间上位于此 BBox 内（或附近）的 grasp_point
                matched = None
                for pa in point_anns:
                    # COCO Points 的坐标在 bbox 字段里（宽高为0）或 keypoints 字段
                    if pa.get("keypoints"):
                        px, py = pa["keypoints"][0], pa["keypoints"][1]
                    else:
                        px = pa["bbox"][0]
                        py = pa["bbox"][1]
                    if point_in_box(px, py, bx, by, bw, bh):
                        matched = (px, py)
                        break

                if matched:
                    kp_x = matched[0] / W
                    kp_y = matched[1] / H
                    kp_v = 2  # 完全可见
                    count_with_kp += 1
                else:
                    # 没找到对应点 → 看不清采摘点，kp_v=0
                    kp_x, kp_y, kp_v = 0.0, 0.0, 0
                    count_without_kp += 1

            else:
                # 情况A：关键点内嵌在 ripe annotation 的 keypoints 字段里
                keypoints = ann.get("keypoints", [])
                if len(keypoints) >= 3 and keypoints[2] > 0:
                    kp_x = keypoints[0] / W
                    kp_y = keypoints[1] / H
                    kp_v = keypoints[2]
                    count_with_kp += 1
                else:
                    kp_x, kp_y, kp_v = 0.0, 0.0, 0
                    count_without_kp += 1

            # YOLO Pose 格式：class xc yc w h kp_x kp_y kp_v
            # kp_v=0 时 kp_x/kp_y 填 0，YOLO 训练会自动忽略这个关键点的 loss
            line = f"0 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f} {kp_x:.6f} {kp_y:.6f} {kp_v}"
            lines.append(line)

        if lines:
            with open(label_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            count_img += 1

    print(f"\n=== 转换完成 ===")
    print(f"处理图片：        {count_img} 张")
    print(f"有采摘点的草莓：  {count_with_kp} 个  (kp_v=2，参与 pose loss)")
    print(f"无采摘点的草莓：  {count_without_kp} 个  (kp_v=0，只参与 box loss，不浪费)")
    print(f"跳过（BBox越界）：{count_skip} 个")
    print(f"输出目录：{OUTPUT_LABELS_DIR}")
    print(f"\n格式：class xc yc w h kp_x kp_y kp_v")
    print(f"示例（有点）：0 0.512 0.423 0.234 0.345 0.523 0.378 2")
    print(f"示例（无点）：0 0.512 0.423 0.234 0.345 0.000 0.000 0")


if __name__ == "__main__":
    convert()
