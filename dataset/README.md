# dataset/

本目录只存储 **标注文件（labels）**，图片不上传至 GitHub。

## 数据集说明

| 项目 | 内容 |
|---|---|
| 图片总数 | 194 张（有效标注） |
| 训练集 | 155 张（`labels/train/`） |
| 验证集 | 39 张（`labels/val/`） |
| 标注格式 | YOLO Pose（txt） |
| 关键点 | 1 个（采摘点，kpt_shape=[1,3]） |
| 类别 | 1 个（`ripe`，成熟草莓） |

## 图片来源

- **自采数据**：200 张，使用 Orbbec Gemini 335 拍摄，通过 CVAT 手工标注（原始 XML 见 `docs/annotations.xml`）。
  转换脚本：`vision/tools/cvat_xml2yolo_pose.py`，MARGIN=0.6
- **DatasetNinja 补充数据**：来自公开草莓检测数据集（备用，当前训练集未使用）

## 获取图片

图片需自行准备，放置于以下路径才能运行训练脚本：

```
strawberry_pose_dataset/
├── images/
│   ├── train/    ← 155 张
│   └── val/      ← 39 张
└── labels/
    ├── train/    ← 已在仓库中
    └── val/      ← 已在仓库中
```

> 如需获取原始图片，请联系项目组（谢中凯）。
