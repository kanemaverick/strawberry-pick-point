# cvat_xml2yolo_pose.py
# 将 CVAT for images 1.1 格式的 XML 转换为 YOLO Pose 格式
#
# 标注规则：
#   <box label="ripe">         → BBox
#   <points label="grasp_point"> → 采摘点（空间上匹配最近的 ripe BBox）
#
# 输出格式（每行一个目标）：
#   0 xc yc w h kp_x kp_y kp_v
#   kp_v=2：有采摘点（完全可见）
#   kp_v=0：没找到对应采摘点（只参与 box loss，不浪费）
#
# 运行方式（Anaconda Prompt）：
#   conda activate yolov11
#   python "C:\Users\xzKan\Desktop\机械臂草莓\autodl_scripts\cvat_xml2yolo_pose.py"

import xml.etree.ElementTree as ET
import os
from pathlib import Path

# ============================================================
# 路径配置（已设置好，无需修改）
XML_PATH = r"C:\Users\xzKan\Desktop\机械臂草莓\pose_annotation\annotations.xml"
SRC_IMAGES_DIR = r"C:\Users\xzKan\Desktop\机械臂草莓\pose_annotation_images"
OUTPUT_LABELS = r"C:\Users\xzKan\Desktop\机械臂草莓\yolo_pose_labels"
# ============================================================

BBOX_LABEL = "ripe"
POINT_LABEL = "grasp_point"
# grasp_point 匹配时允许向 BBox 外扩展的比例
# 采摘点是果梗位置，经常在草莓 BBox 上边缘之外，需要较大 margin
# 诊断数据：115个未匹配点中101个在BBox上方，109个超出比例<0.5
MARGIN = 0.6


def point_in_box(px, py, xtl, ytl, xbr, ybr):
    bw = xbr - xtl
    bh = ybr - ytl
    mx = bw * MARGIN
    my = bh * MARGIN
    return (xtl - mx <= px <= xbr + mx) and (ytl - my <= py <= ybr + my)


def convert():
    print(f"读取 XML：{XML_PATH}")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    os.makedirs(OUTPUT_LABELS, exist_ok=True)

    count_img = 0
    count_with_kp = 0
    count_without_kp = 0
    count_skip = 0
    unmatched_points = 0  # 没有对应 BBox 的 grasp_point（可能标错位置）

    for img_elem in root.iter("image"):
        fname = img_elem.get("name")  # e.g. "1.jpg" or "100.jpg"
        W = float(img_elem.get("width"))
        H = float(img_elem.get("height"))
        stem = Path(fname).stem

        # 验证图片文件存在
        img_path = os.path.join(SRC_IMAGES_DIR, fname)
        if not os.path.exists(img_path):
            print(f"  警告：图片不存在，跳过 → {img_path}")
            count_skip += 1
            continue

        # 收集该图片内所有 BBox 和采摘点
        boxes = []  # [(xtl, ytl, xbr, ybr)]
        points = []  # [(px, py)]

        for child in img_elem:
            label = child.get("label", "")
            if label == BBOX_LABEL and child.tag == "box":
                xtl = float(child.get("xtl"))
                ytl = float(child.get("ytl"))
                xbr = float(child.get("xbr"))
                ybr = float(child.get("ybr"))
                boxes.append((xtl, ytl, xbr, ybr))
            elif label == POINT_LABEL and child.tag == "points":
                # CVAT points 格式："x1,y1;x2,y2;..."，这里每个 annotation 只有一个点
                raw = child.get("points", "")
                for pt in raw.split(";"):
                    pt = pt.strip()
                    if pt:
                        px, py = map(float, pt.split(","))
                        points.append((px, py))

        if not boxes:
            # 该图片没有 ripe 标注，跳过（不生成 label 文件）
            continue

        # 为每个采摘点找最近的 BBox
        # 先尝试空间包含，再按圆心距离兜底匹配
        point_matched = {}  # point index → box index（一个点最多匹配一个 box）
        box_matched = {}  # box index → point index（一个 box 最多匹配一个点）

        for pi, (px, py) in enumerate(points):
            best_box = None
            best_dist = float("inf")
            for bi, (xtl, ytl, xbr, ybr) in enumerate(boxes):
                if bi in box_matched:
                    continue  # 这个 box 已经匹配过了
                if point_in_box(px, py, xtl, ytl, xbr, ybr):
                    cx = (xtl + xbr) / 2
                    cy = (ytl + ybr) / 2
                    dist = (px - cx) ** 2 + (py - cy) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best_box = bi
            if best_box is not None:
                point_matched[pi] = best_box
                box_matched[best_box] = pi
            else:
                unmatched_points += 1

        # 生成 YOLO Pose label
        lines = []
        for bi, (xtl, ytl, xbr, ybr) in enumerate(boxes):
            bw = xbr - xtl
            bh = ybr - ytl
            xc = (xtl + bw / 2) / W
            yc = (ytl + bh / 2) / H
            nw = bw / W
            nh = bh / H

            # BBox 合法性检查（clamp 到 [0,1]，允许极小的越界误差）
            xc = max(0.0, min(1.0, xc))
            yc = max(0.0, min(1.0, yc))
            nw = max(0.001, min(1.0, nw))
            nh = max(0.001, min(1.0, nh))

            if bi in box_matched:
                pi = box_matched[bi]
                px, py = points[pi]
                kp_x = max(0.0, min(1.0, px / W))
                kp_y = max(0.0, min(1.0, py / H))
                kp_v = 2
                count_with_kp += 1
            else:
                kp_x, kp_y, kp_v = 0.0, 0.0, 0
                count_without_kp += 1

            lines.append(
                f"0 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f} {kp_x:.6f} {kp_y:.6f} {kp_v}"
            )

        label_path = os.path.join(OUTPUT_LABELS, stem + ".txt")
        with open(label_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        count_img += 1

    print(f"\n=== 转换完成 ===")
    print(f"处理图片：          {count_img} 张")
    print(f"有采摘点的草莓：    {count_with_kp} 个  (kp_v=2，参与 pose loss)")
    print(f"无采摘点的草莓：    {count_without_kp} 个  (kp_v=0，只参与 box loss)")
    print(f"跳过（图片不存在）：{count_skip} 张")
    if unmatched_points > 0:
        print(
            f"未匹配的采摘点：    {unmatched_points} 个  (超出所有 BBox 范围，已忽略)"
        )
    print(f"\n输出目录：{OUTPUT_LABELS}")
    print(f"格式示例：")
    print(f"  有点：0 0.512 0.423 0.234 0.345 0.523 0.378 2")
    print(f"  无点：0 0.512 0.423 0.234 0.345 0.000 0.000 0")
    print(f"\n下一步：运行 split_dataset.py 划分训练/验证集")


if __name__ == "__main__":
    convert()
