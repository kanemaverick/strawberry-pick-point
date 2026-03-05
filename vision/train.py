# vision/train.py
# YOLOv11-Pose 草莓采摘点检测训练脚本
# 本地 Windows + RTX 4070 Super (12GB VRAM) 版本
#
# 运行方式（Anaconda Prompt，在仓库根目录下执行）：
#   conda activate yolov11
#   python vision/train.py

import os
from pathlib import Path
from ultralytics import YOLO

# ============================================================
# 路径配置（使用相对路径，从仓库根目录运行）
_HERE = Path(__file__).parent  # vision/
YAML_PATH = str(_HERE / "configs" / "strawberry_pose.yaml")
SAVE_DIR = str(_HERE.parent / "runs_pose")
# ============================================================


def main():
    print("=== 加载 YOLOv11n-Pose 预训练模型 ===")
    print("（首次运行会自动下载 yolo11n-pose.pt，约 5.5MB）")

    model = YOLO(str(_HERE.parent / "pretrained" / "yolo11n-pose.pt"))

    print("=== 开始训练 Pose 模型（RTX 4070 Super 本地版）===")
    results = model.train(
        data=YAML_PATH,
        # --- 基础参数 ---
        epochs=150,
        imgsz=640,
        # RTX 4070 12GB：batch=16 安全，batch=24 可能刚好够
        # 如果报 CUDA out of memory，改成 batch=8
        batch=16,
        device=0,  # 使用 GPU 0（RTX 4070 Super）
        # --- 保存路径 ---
        project=SAVE_DIR,
        name="strawberry_pose_v14",
        # --- 优化器 ---
        optimizer="AdamW",
        lr0=0.005,
        patience=50,
        # --- 数据增强 ---
        copy_paste=0.3,
        mixup=0.1,
        mosaic=1.0,
        degrees=15.0,
        hsv_s=0.8,
        erasing=0.4,
        # --- Pose 专用损失权重 ---
        pose=14.0,
        # --- 其他 ---
        verbose=True,
        save=True,
        save_period=10,
        # Windows 下 DataLoader 多进程有时会卡，设为 0 用主进程加载
        workers=4,
    )

    print("\n=== 训练完成！===")
    print(f"最优权重：{SAVE_DIR}\\strawberry_pose_v14\\weights\\best.pt")
    print(f"训练曲线：{SAVE_DIR}\\strawberry_pose_v14\\results.png")
    print(f"验证预览：{SAVE_DIR}\\strawberry_pose_v14\\val_batch0_pred.jpg")


if __name__ == "__main__":
    main()
