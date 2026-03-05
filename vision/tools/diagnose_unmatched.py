# diagnose_unmatched.py
# 诊断未匹配的 grasp_point，输出它们距离最近 BBox 的超出距离
# 帮助决定 MARGIN 应该设多大

import xml.etree.ElementTree as ET
from pathlib import Path

XML_PATH = r"C:\Users\xzKan\Desktop\机械臂草莓\pose_annotation\annotations.xml"

tree = ET.parse(XML_PATH)
root = tree.getroot()

unmatched = []  # (fname, px, py, nearest_box_info, overshoot_y)

for img_elem in root.iter("image"):
    fname = img_elem.get("name")
    W = float(img_elem.get("width"))
    H = float(img_elem.get("height"))

    boxes = []
    points = []

    for child in img_elem:
        label = child.get("label", "")
        if label == "ripe" and child.tag == "box":
            boxes.append(
                (
                    float(child.get("xtl")),
                    float(child.get("ytl")),
                    float(child.get("xbr")),
                    float(child.get("ybr")),
                )
            )
        elif label == "grasp_point" and child.tag == "points":
            raw = child.get("points", "")
            for pt in raw.split(";"):
                pt = pt.strip()
                if pt:
                    px, py = map(float, pt.split(","))
                    points.append((px, py))

    for px, py in points:
        # 检查是否在任意 BBox 内（MARGIN=0.15）
        matched = False
        best_info = None
        best_dist = float("inf")
        for xtl, ytl, xbr, ybr in boxes:
            bw = xbr - xtl
            bh = ybr - ytl
            mx = bw * 0.15
            my = bh * 0.15
            if (xtl - mx <= px <= xbr + mx) and (ytl - my <= py <= ybr + my):
                matched = True
                break
            # 计算到最近 BBox 的超出量（归一化到 BBox 尺寸）
            overshoot_x = max(0, xtl - px, px - xbr) / bw
            overshoot_y = max(0, ytl - py, py - ybr) / bh
            dist = overshoot_x + overshoot_y
            if dist < best_dist:
                best_dist = dist
                best_info = (xtl, ytl, xbr, ybr, overshoot_x, overshoot_y, bw, bh)

        if not matched and best_info:
            xtl, ytl, xbr, ybr, ox, oy, bw, bh = best_info
            unmatched.append(
                {
                    "file": fname,
                    "px": px,
                    "py": py,
                    "xtl": xtl,
                    "ytl": ytl,
                    "xbr": xbr,
                    "ybr": ybr,
                    "overshoot_x_ratio": ox,
                    "overshoot_y_ratio": oy,
                }
            )

print(f"未匹配点总数：{len(unmatched)}")
print()

# 按超出比例排序
unmatched.sort(key=lambda x: x["overshoot_y_ratio"] + x["overshoot_x_ratio"])

# 统计超出方向
above = sum(1 for u in unmatched if u["py"] < u["ytl"])  # 点在 BBox 上方
below = sum(1 for u in unmatched if u["py"] > u["ybr"])
left = sum(1 for u in unmatched if u["px"] < u["xtl"])
right = sum(1 for u in unmatched if u["px"] > u["xbr"])
print(f"超出方向统计（一个点可能多方向超出）：")
print(f"  上方（点在 BBox 上边缘之外）：{above}")
print(f"  下方：{below}")
print(f"  左侧：{left}")
print(f"  右侧：{right}")
print()

# 统计超出比例分布
import statistics

ratios = [u["overshoot_x_ratio"] + u["overshoot_y_ratio"] for u in unmatched]
print(f"超出比例（点距最近 BBox 边缘 / BBox 尺寸）：")
print(f"  最小：{min(ratios):.3f}")
print(f"  中位：{statistics.median(ratios):.3f}")
print(f"  最大：{max(ratios):.3f}")
print(f"  超出比例 < 0.3 的点：{sum(1 for r in ratios if r < 0.3)}")
print(f"  超出比例 < 0.5 的点：{sum(1 for r in ratios if r < 0.5)}")
print(f"  超出比例 < 1.0 的点：{sum(1 for r in ratios if r < 1.0)}")
print()

# 打印前 20 个（最容易修复的）
print("前 20 个未匹配点（超出最少的）：")
print(f"{'文件':<12} {'点坐标':>18} {'BBox':>32} {'超出X':>8} {'超出Y':>8}")
for u in unmatched[:20]:
    print(
        f"{u['file']:<12} ({u['px']:6.0f},{u['py']:6.0f})  "
        f"({u['xtl']:5.0f},{u['ytl']:5.0f})-({u['xbr']:5.0f},{u['ybr']:5.0f})  "
        f"{u['overshoot_x_ratio']:7.3f}  {u['overshoot_y_ratio']:7.3f}"
    )
