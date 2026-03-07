# 基于 YOLOv11 以草莓采摘为场景的机械臂采摘点研究

同济大学 SITP 项目 · 2025–2026

## 项目简介

本项目以草莓采摘为应用场景，研究机械臂自主采摘中的视觉感知与运动控制问题。
核心任务：利用 YOLOv11-Pose 检测成熟草莓并定位采摘点（果梗附近），将像素坐标反投影为相机 3D 坐标，供机械臂运动规划使用。

**当前视觉模型指标（v14）：**
- Box mAP50: **0.927**
- Pose mAP50: **0.803**
- Pose mAP50-95: **0.774**

**🏆 英特尔杯边缘部署架构（Target: Intel Core Ultra 5 225U）：**
本项目实现了基于 OpenVINO 的异构加速部署（CPU/iGPU/NPU），核心管线包括：
- **YOLOv11-Pose (INT8)**: 经 NNCF 静态量化，模型从 5.4MB 压缩至 3.5MB，在 CPU 上实现 ~9.2ms 极速推理。
- **FastSAM-s (FP16)**: 用于高密度遮挡场景下的精细化实例分割，已导出 OpenVINO FP16 格式。
- **Depth Anything V2 Small (FP16)**: 作为深度相机盲区或失效时的单目深度估计 fallback 方案。
- **时序决策融合 (BoT-SORT)**: 基于成熟度（0.6）与可达性（0.4）评分的多帧目标跟踪与决策去重算法。

## 📁 项目结构

```
.
├── vision/                      # 视觉模块（核心）
│   ├── train.py                 # 训练脚本
│   ├── inference.py             # 推理脚本（Orbbec Gemini 335 + YOLOv11-Pose）
│   ├── evaluate.py              # 评估脚本
│   ├── utils/                   # 算法与工具类
│   │   └── decision_maker.py    # 基于 BoT-SORT 的多帧时序采摘决策算法
│   ├── configs/                 # 配置文件
│   ├── tools/                   # 数据转换工具脚本
│   └── weights/                 # 训练好的权重（Git LFS）
│
├── dataset/                     # 主要数据集（已整合）
│   ├── images/                  # 训练和验证图像
│   ├── labels/                  # YOLO 格式标注
│   └── README.md                # 数据集说明
│
├── strawberry_pose_dataset_v2/  # 姿态估计数据集（最新版本）
│   ├── images/                  # 带关键点标注的图像
│   └── labels/                  # YOLO 姿态格式标注
│
├── strawberry-dataset-for-object-detection-DatasetNinja/
│   ├── training/                # 原始 DatasetNinja 数据
│   └── validation/
│
├── pretrained/                  # 预训练权重（Git LFS）
│   ├── README.md
│   └── yolo/                    # YOLO 模型权重
│       ├── yolo11n-pose.pt      # YOLOv11 姿态估计
│       └── yolo26n.pt           # YOLOv8 检测
│
├── runs_pose/                   # 姿态估计训练结果
│   ├── strawberry_pose_v1...v14/  # 不同版本迭代
│   └── env_test_coco/             # COCO 格式测试
│
├── runs/                        # 目标检测训练结果
│   └── strawberry_detect7/
│
├── outputs/                     # 推理和分析输出
│   ├── detect/                  # 检测结果
│   ├── strawberry_detect_advanced2/3/
│   └── Three_Phases_Evolution_Report.md
│
├── autodl_scripts/              # 数据处理脚本集
│   ├── datasetninja2yolo_pose.py    # 格式转换
│   ├── cvat_xml2yolo_pose.py        # 标注转换
│   ├── evaluate_model.py
│   ├── generate_negatives.py
│   ├── inference_windows.py
│   └── ...其他辅助脚本
│
├── pose_annotation/             # 手工标注数据
│   └── annotations.xml          # CVAT 标注文件
│
├── pose_annotation_images/      # 姿态标注图像
├── yolo_pose_labels/            # YOLO 姿态标签
│
├── simulation/                  # 仿真模块
│   └── README.md
│
├── hardware/                    # 硬件/电控模块
│   └── README.md
│
├── reports/                     # 技术报告
│   ├── Detection_Technical_Report.md
│   ├── Detection_Technical_Report_V2.md
│   ├── YOLOv11_Pose_Training_Guide.md
│   ├── Three_Phases_Evolution_Report.md
│   └── Project_Task_Planning.md
│
├── docs/                        # 项目文档
│   ├── 草莓采摘机器人.pdf           # 项目总体设计
│   ├── SITP项目申报书*.pdf        # 项目申报材料
│   ├── 项目任务分工_v2.docx       # 最新任务分工
│   ├── 项目任务分工_v3.docx
│   ├── 答辩PPT文稿*.md             # 答辩演讲稿
│   ├── tech_route.txt            # 技术路线
│   ├── annotations.xml           # 标注元数据
│   ├── assets/                   # 文档资源
│   └── 生成分工文档.py
│
├── recordings/                  # 媒体资源
│   └── training_demo.mp4        # 训练演示视频
│
├── root/                        # 旧版本备份
├── export_ov.py                 # YOLOv11-Pose OpenVINO INT8 导出脚本
├── export_sam_ov.py             # FastSAM OpenVINO FP16 导出脚本
├── export_depth_anything.py     # Depth Anything V2 OpenVINO FP16 导出脚本
├── .gitattributes               # Git LFS 配置（*.pt）
├── .gitignore
└── README.md                    # 本文件
```

## 🚀 快速开始

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

## 📊 数据集

- 194 张草莓图片（自采 + CVAT 手工标注）
- 关键点：1 个采摘点（果梗附近），`kpt_shape=[1,3]`
- 详见 [`dataset/README.md`](dataset/README.md)

## 🧠 模型权重

权重文件通过 **Git LFS** 存储，克隆后执行：

```bash
git lfs pull
```

| 文件 | 说明 |
|---|---|
| `vision/weights/strawberry_pose_v14_best.pt` | 当前最优模型（推荐使用） |
| `pretrained/yolo/yolo11n-pose.pt` | Ultralytics 官方预训练权重 |
| `pretrained/yolo/yolo26n.pt` | YOLOv8 检测权重 |

## 👥 团队分工

| 姓名 | 负责方向 |
|---|---|
| 谢中凯 | 项目统筹 · 文献调研 · 视觉训练 |
| 陆坚其 | MuJoCo 仿真 · IK 求解 · 采摘顺序算法 |
| 王政鈞 | 视觉模型优化（遮挡场景）· 数据扩充 |
| 刘炳尧 | 机械臂结构学习 · 仿真协作 |
| 喻士煊 | 嵌入式部署 · 电控硬件 |

详细分工见 [`docs/项目任务分工_v2.docx`](docs/项目任务分工_v2.docx)

## 📝 项目整理记录

**2026年3月8日 英特尔杯初选部署**
- ✅ 完成 YOLOv11-Pose 向 OpenVINO INT8 的量化导出（NNCF），大幅降低推理延迟
- ✅ 完成 FastSAM-s 与 Depth Anything V2 的 OpenVINO FP16 导出
- ✅ 新增多帧时序采摘决策算法 `vision/utils/decision_maker.py`
- ✅ 更新答辩 PPT，强化具身智能与异构计算架构（Intel Core Ultra 5 225U）相关的技术叙述

**2026年3月7日 数据清理**
- ✅ 删除重复的压缩文件 (outputs.zip)
- ✅ 合并 datasetninja_images 和 datasetninja_labels 到 dataset/
- ✅ 删除重复的旧版本数据集 (strawberry_pose_dataset)
- ✅ 统一整理文档到 docs/ 目录
- ✅ 整理模型权重到 pretrained/ 目录
- ✅ 删除临时文件和日志文件
- ✅ 移除根目录杂乱文件到相应文件夹

**整理后的根目录**（仅保留核心文件）：
```
.
├── README.md                                    # 本文件
├── 项目任务分工_v2.docx                        # 最新任务分工表
├── yolo11n-pose.pt                             # YOLOv11 模型权重
├── yolo26n.pt                                  # YOLOv8 模型权重
├── tech_route.txt                              # 技术路线
├── runs_detect_predict.zip                     # 检测训练结果备份
└── strawberry-dataset-for-object-detection-DatasetNinja.zip  # 原始数据集备份
```
