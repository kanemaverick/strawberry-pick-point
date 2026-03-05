# simulation/

本模块由 **陆坚其** 负责，负责 MuJoCo 仿真环境搭建、IK 求解与采摘顺序算法。

## 技术选型

仿真平台：**MuJoCo**（已确定）

- SO-101 机械臂有官方 MJCF 模型文件
- 安装：`pip install mujoco`

## 获取 SO-101 MJCF

```
pip install mujoco
python -c "import mujoco; print(mujoco.__version__)"
```

SO-101 官方模型：[github.com/huggingface/lerobot](https://github.com/huggingface/lerobot)（`lerobot/configs/robot/so101.yaml`）

## 接口约定

- **输入**：来自视觉模块的采摘点相机坐标 `(X, Y, Z)` 单位米
- **输出**：各关节角度序列（供硬件控制模块执行）
- 坐标系：相机坐标系 → 机械臂基座坐标系（需标定外参）
