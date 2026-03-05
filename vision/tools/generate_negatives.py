import os
import cv2
import random
import glob
import uuid


def check_intersection(crop_box, gt_boxes):
    """
    检查裁剪框是否与任何真实框(Ground Truth)有重叠
    crop_box: [x1, y1, x2, y2]
    gt_boxes: list of [x1, y1, x2, y2]
    """
    for gt in gt_boxes:
        xA = max(crop_box[0], gt[0])
        yA = max(crop_box[1], gt[1])
        xB = min(crop_box[2], gt[2])
        yB = min(crop_box[3], gt[3])

        interArea = max(0, xB - xA) * max(0, yB - yA)
        # 只要有任何一点点重叠，就认为相交，丢弃这个裁剪框
        if interArea > 0:
            return True
    return False


def get_boxes_from_yolo(txt_path, img_w, img_h):
    """从 YOLO txt 文件中提取边界框"""
    gt_boxes = []
    try:
        with open(txt_path, "r") as f:
            lines = f.readlines()
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    # 将归一化坐标转换为像素坐标 [x1, y1, x2, y2]
                    x_c, y_c, w, h = map(float, parts[1:5])
                    x1 = int((x_c - w / 2) * img_w)
                    y1 = int((y_c - h / 2) * img_h)
                    x2 = int((x_c + w / 2) * img_w)
                    y2 = int((y_c + h / 2) * img_h)
                    gt_boxes.append([x1, y1, x2, y2])
    except Exception as e:
        print(f"解析 {txt_path} 出错: {e}")
    return gt_boxes


def main():
    print("=== 开始生成草莓负样本 (纯背景/绿叶/泥土) ===")

    # 【核心修改】根据您提供的截图，您的 training 文件夹直接放在 /root/autodl-tmp/ 下！
    # 并且图片在 images，YOLO标签在 labels
    images_dir = "/root/autodl-tmp/training/images"
    labels_dir = "/root/autodl-tmp/training/labels"

    if not os.path.exists(images_dir) or not os.path.exists(labels_dir):
        print(f"找不到目录: {images_dir} 或 {labels_dir}")
        print("这说明您的 training 下面可能不是 images 和 labels。")
        print(
            "请检查 /root/autodl-tmp/training 里面到底是 img/ann 还是 images/labels？"
        )
        return

    # 获取所有图片路径
    img_paths = glob.glob(os.path.join(images_dir, "*.jpg")) + glob.glob(
        os.path.join(images_dir, "*.png")
    )
    total_imgs = len(img_paths)
    print(f"共找到 {total_imgs} 张训练图片。")

    if total_imgs == 0:
        return

    # 我们希望生成的负样本数量大约是原数据集的 15%
    target_negatives = int(total_imgs * 0.15)
    print(f"目标生成负样本数量: {target_negatives} 张 (约 15%)")

    # 打乱图片顺序，保证背景的多样性
    random.shuffle(img_paths)

    generated_count = 0

    for img_path in img_paths:
        if generated_count >= target_negatives:
            break

        filename = os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(labels_dir, filename + ".txt")

        if not os.path.exists(label_path):
            continue

        # 读取图像以获取宽高
        img = cv2.imread(img_path)
        if img is None:
            continue
        img_h, img_w = img.shape[:2]

        # 提取标注框
        gt_boxes = get_boxes_from_yolo(label_path, img_w, img_h)

        # 尝试在图片中随机裁剪 20 次，寻找纯净的背景区域
        found_clean_crop = False
        for _ in range(20):
            # 随机决定裁剪框的大小 (最小 256x256，最大不超过原图宽高的 60%)
            crop_w = random.randint(256, int(img_w * 0.6))
            crop_h = random.randint(256, int(img_h * 0.6))

            # 随机决定裁剪框的左上角起点
            crop_x1 = random.randint(0, img_w - crop_w)
            crop_y1 = random.randint(0, img_h - crop_h)
            crop_x2 = crop_x1 + crop_w
            crop_y2 = crop_y1 + crop_h

            crop_box = [crop_x1, crop_y1, crop_x2, crop_y2]

            # 检查这个裁剪框里有没有草莓
            if not check_intersection(crop_box, gt_boxes):
                # 找到了纯净的背景！
                found_clean_crop = True

                # 执行裁剪
                bg_patch = img[crop_y1:crop_y2, crop_x1:crop_x2]

                # 为了保持统一，将裁剪下来的背景图 resize 到 640x640
                bg_patch_resized = cv2.resize(bg_patch, (640, 640))

                # 生成唯一的负样本文件名
                neg_filename = f"neg_bg_{uuid.uuid4().hex[:8]}"
                neg_img_path = os.path.join(images_dir, neg_filename + ".jpg")
                neg_label_path = os.path.join(labels_dir, neg_filename + ".txt")

                # 保存背景图
                cv2.imwrite(neg_img_path, bg_patch_resized)

                # 创建空标签文件！
                with open(neg_label_path, "w") as f:
                    pass  # YOLO 空 txt

                generated_count += 1
                if generated_count % 50 == 0:
                    print(f"已生成 {generated_count} / {target_negatives} 张负样本...")
                break  # 一张原图最多只抠一个背景，保证多样性

    print(f"=== 成功！总共生成了 {generated_count} 张纯背景负样本。 ===")


if __name__ == "__main__":
    main()
