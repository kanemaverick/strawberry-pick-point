# 基于 YOLOv11 以草莓采摘为场景的机械臂采摘点研究

同济大学 SITP 项目 · 2025–2026

## 项目简介

本项目以草莓采摘为应用场景，研究机械臂自主采摘中的视觉感知与运动控制问题。
核心任务：利用 YOLOv11-Pose 检测成熟草莓并定位采摘点（果梗附近），将像素坐标反投影为相机 3D 坐标，供机械臂运动规划使用。

**当前视觉模型指标（v14）：**
- Box mAP50: **0.927**
- Pose mAP50: **0.803**
- Pose mAP50-95: **0.774**

## 目录结构

```
.
├── vision/                  # 视觉模块（谢中凯 · 王政鈞 · 喻士煊）
│   ├── train.py             # 训练脚本
│   ├── inference.py         # 推理脚本（Orbbec Gemini 335 + YOLOv11-Pose）
│   ├── evaluate.py          # 评估脚本
│   ├── configs/
│   │   └── strawberry_pose.yaml  # 训练配置
│   ├── tools/               # 数据转换工具脚本
│   └── weights/             # 训练好的权重（Git LFS）
│       └── strawberry_pose_v14_best.pt
├── simulation/              # 仿真模块（陆坚其 · 刘炳尧）
├── hardware/                # 硬件/电控模块（喻士煊）
├── dataset/                 # 仅存 labels，图片不在仓库中
│   ├── labels/train/        # 155 个标注文件
│   └── labels/val/          # 39 个标注文件
├── pretrained/              # 预训练权重（Git LFS）
│   ├── yolo11n-pose.pt
│   └── yolo26n.pt
├── docs/                    # 项目文档
│   ├── 项目任务分工_v2.docx
│   ├── tech_route.txt
│   └── annotations.xml      # CVAT 原始标注文件
├── .gitattributes           # Git LFS 配置（*.pt）
└── .gitignore
```

## 快速开始

**环境要求：**

```
Python 3.10
PyTorch 2.2.1+cu121
ultralytics 8.4.19
pyorbbecsdk2==2.0.18（推理时需要）
GPU: RTX 4070 Super 12GB（或同等 CUDA 设备）
```

**安装：**

```bash
conda activate yolov11
pip install ultralytics pyorbbecsdk2
```

**运行推理（接 Orbbec 相机）：**

```bash
conda activate yolov11
python vision/inference.py
```

**重新训练：**

> 训练前需准备图片数据集（见 `dataset/README.md`）

```bash
conda activate yolov11
python vision/train.py
```

## 数据集

- 194 张草莓图片（自采 + CVAT 手工标注），仅上传 labels
- 关键点：1 个采摘点（果梗附近），`kpt_shape=[1,3]`
- 详见 [`dataset/README.md`](dataset/README.md)

## 模型权重

权重文件通过 **Git LFS** 存储，克隆后执行：

```bash
git lfs pull
```

| 文件 | 说明 |
|---|---|
| `vision/weights/strawberry_pose_v14_best.pt` | 当前最优模型（推荐使用） |
| `pretrained/yolo11n-pose.pt` | Ultralytics 官方预训练权重 |

## 团队分工

| 姓名 | 负责方向 |
|---|---|
| 谢中凯 | 项目统筹 · 文献调研 · 视觉训练 |
| 陆坚其 | MuJoCo 仿真 · IK 求解 · 采摘顺序算法 |
| 王政鈞 | 视觉模型优化（遮挡场景）· 数据扩充 |
| 刘炳尧 | 机械臂结构学习 · 仿真协作 |
| 喻士煊 | 嵌入式部署 · 电控硬件 |

详细分工见 [`docs/项目任务分工_v2.docx`](docs/项目任务分工_v2.docx)
