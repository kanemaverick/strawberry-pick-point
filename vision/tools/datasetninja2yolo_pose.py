# datasetninja2yolo_pose.py
# 将 DatasetNinja/Supervisely 格式的草莓数据集转换为 YOLO Pose 格式
#
# 数据集类别：
#   ripe      → 成熟草莓 BBox（对应我们的 class 0）
#   peduncle  → 果梗 BBox（中心点作为 grasp_point 关键点）
#   unripe    → 忽略
#   其他      → 忽略
#
# 匹配策略：
#   对每个 ripe BBox，找空间上最近且与其有一定关联的 peduncle BBox
#   关联判定：peduncle 中心到 ripe BBox 的距离 ≤ max(ripe_w, ripe_h) * SEARCH_RADIUS
#   多对一时取最近的；无匹配时 kp_v=0（只参与 box loss）
#
# 输出格式（每行）：
#   0 xc yc w h kp_x kp_y kp_v
#
# 运行方式（Anaconda Prompt）：
#   conda activate yolov11
#   python "C:\Users\xzKan\Desktop\机械臂草莓\autodl_scripts\datasetninja2yolo_pose.py"

import json
import os
import shutil
from pathlib import Path

# ============================================================
# 路径配置
DATASET_ROOT = r"C:\Users\xzKan\Desktop\机械臂草莓\strawberry-dataset-for-object-detection-DatasetNinja"
OUTPUT_IMAGES = r"C:\Users\xzKan\Desktop\机械臂草莓\datasetninja_images"
OUTPUT_LABELS = r"C:\Users\xzKan\Desktop\机械臂草莓\datasetninja_labels"
# ============================================================

# peduncle 中心到 ripe BBox 的搜索半径（相对于 ripe BBox 最大边长的倍数）
# peduncle 通常紧贴在草莓上方或与草莓相交，1.2 倍覆盖大多数情况
SEARCH_RADIUS = 1.2

SPLITS = ["training", "validation"]


def box_center(pts):
    """从 Supervisely exterior [[x1,y1],[x2,y2]] 获取中心坐标和尺寸"""
    x1, y1 = pts[0]
    x2, y2 = pts[1]
    # 确保 x1<x2, y1<y2
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    w = x2 - x1
    h = y2 - y1
    return cx, cy, w, h, x1, y1, x2, y2


def point_to_box_dist(px, py, bx1, by1, bx2, by2):
    """点到 BBox 的最短距离（点在 BBox 内时返回 0）"""
    dx = max(bx1 - px, 0, px - bx2)
    dy = max(by1 - py, 0, py - by2)
    return (dx**2 + dy**2) ** 0.5


def convert_split(split):
    ann_dir = Path(DATASET_ROOT) / split / "ann"
    img_dir = Path(DATASET_ROOT) / split / "img"

    out_img_dir = Path(OUTPUT_IMAGES) / split
    out_lbl_dir = Path(OUTPUT_LABELS) / split
    out_img_dir.mkdir(parents=True, exist_ok=True)
    out_lbl_dir.mkdir(parents=True, exist_ok=True)

    count_img = 0
    count_with_kp = 0
    count_without_kp = 0
    count_skip = 0
    count_no_ripe = 0

    for ann_file in sorted(ann_dir.glob("*.json")):
        img_name = ann_file.stem  # e.g. "0.jpg"
        img_path = img_dir / img_name
        if not img_path.exists():
            print(f"  警告：图片不存在，跳过 → {img_path}")
            count_skip += 1
            continue

        data = json.loads(ann_file.read_text(encoding="utf-8"))
        W = data["size"]["width"]
        H = data["size"]["height"]

        ripes = []
        peduncles = []
        for obj in data["objects"]:
            if obj["geometryType"] != "rectangle":
                continue
            pts = obj["points"]["exterior"]
            if len(pts) < 2:
                continue
            cx, cy, w, h, x1, y1, x2, y2 = box_center(pts)
            if obj["classTitle"] == "ripe":
                ripes.append((cx, cy, w, h, x1, y1, x2, y2))
            elif obj["classTitle"] == "peduncle":
                peduncles.append((cx, cy, w, h, x1, y1, x2, y2))

        if not ripes:
            count_no_ripe += 1
            continue

        # 匹配：每个 ripe 找最近的 peduncle（在搜索半径内）
        # peduncle 可以被多个 ripe 共享（实际场景中一般1对1）
        used_peduncles = set()
        matched = {}  # ripe_idx → peduncle_idx

        for ri, (rcx, rcy, rw, rh, rx1, ry1, rx2, ry2) in enumerate(ripes):
            radius = max(rw, rh) * SEARCH_RADIUS
            best_pi = None
            best_dist = float("inf")
            for pi, (pcx, pcy, pw, ph, px1, py1, px2, py2) in enumerate(peduncles):
                if pi in used_peduncles:
                    continue
                dist = point_to_box_dist(pcx, pcy, rx1, ry1, rx2, ry2)
                if dist <= radius and dist < best_dist:
                    best_dist = dist
                    best_pi = pi
            if best_pi is not None:
                matched[ri] = best_pi
                used_peduncles.add(best_pi)

        # 生成 YOLO Pose label
        lines = []
        for ri, (rcx, rcy, rw, rh, rx1, ry1, rx2, ry2) in enumerate(ripes):
            xc_n = max(0.0, min(1.0, rcx / W))
            yc_n = max(0.0, min(1.0, rcy / H))
            w_n = max(0.001, min(1.0, rw / W))
            h_n = max(0.001, min(1.0, rh / H))

            if ri in matched:
                pi = matched[ri]
                pcx, pcy = peduncles[pi][0], peduncles[pi][1]
                kp_x = max(0.0, min(1.0, pcx / W))
                kp_y = max(0.0, min(1.0, pcy / H))
                kp_v = 2
                count_with_kp += 1
            else:
                kp_x, kp_y, kp_v = 0.0, 0.0, 0
                count_without_kp += 1

            lines.append(
                f"0 {xc_n:.6f} {yc_n:.6f} {w_n:.6f} {h_n:.6f} {kp_x:.6f} {kp_y:.6f} {kp_v}"
            )

        stem = Path(img_name).stem
        lbl_path = out_lbl_dir / (stem + ".txt")
        lbl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # 复制图片
        shutil.copy2(img_path, out_img_dir / img_name)
        count_img += 1

    print(f"\n  [{split}] 处理完成")
    print(f"    图片数：       {count_img}")
    print(f"    无 ripe 跳过：  {count_no_ripe}")
    print(f"    图片不存在：    {count_skip}")
    print(f"    有采摘点草莓：  {count_with_kp}（kp_v=2）")
    print(f"    无采摘点草莓：  {count_without_kp}（kp_v=0）")
    return count_img, count_with_kp


def main():
    print("=== DatasetNinja → YOLO Pose 转换 ===")
    print(f"输入：{DATASET_ROOT}")
    print(f"输出图片：{OUTPUT_IMAGES}")
    print(f"输出标注：{OUTPUT_LABELS}")
    print(f"搜索半径：{SEARCH_RADIUS}x max(ripe_w, ripe_h)\n")

    total_img = 0
    total_kp = 0
    for split in SPLITS:
        n, k = convert_split(split)
        total_img += n
        total_kp += k

    print(f"\n=== 总计 ===")
    print(f"  图片：{total_img} 张")
    print(f"  有采摘点草莓：{total_kp} 个")
    print(f"\n输出目录结构：")
    print(f"  {OUTPUT_IMAGES}/training/   ← 图片")
    print(f"  {OUTPUT_IMAGES}/validation/ ← 图片")
    print(f"  {OUTPUT_LABELS}/training/   ← YOLO Pose .txt")
    print(f"  {OUTPUT_LABELS}/validation/ ← YOLO Pose .txt")
    print(f"\n下一步：运行 merge_and_split.py 合并两个数据集并重新划分训练/验证集")


if __name__ == "__main__":
    main()
