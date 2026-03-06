# simulation/

本模块由 **陆坚其** 和 **刘炳尧** 负责，负责 MuJoCo 仿真环境搭建、IK 求解与采摘顺序算法。

## 分工

| 姓名 | 负责方向 |
|---|---|
| 陆坚其 | MuJoCo 仿真 · IK 求解 · 采摘顺序算法 |
| 刘炳尧 | 机械臂结构学习 · 仿真协作 · 联调测试 |

## 技术选型

仿真平台：**MuJoCo**（已确定）

- SO-101 机械臂有官方 MJCF 模型文件
- 安装：`pip install mujoco`

## 获取 SO-101 MJCF

```bash
pip install mujoco
python -c "import mujoco; print(mujoco.__version__)"
```

SO-101 官方模型：[github.com/huggingface/lerobot](https://github.com/huggingface/lerobot)（`lerobot/configs/robot/so101.yaml`）

## 接口约定

- **输入**：来自视觉模块的采摘点相机坐标 `(X, Y, Z)` 单位米
- **输出**：各关节角度序列 `[j1, j2, j3, j4, j5, j6]`，单位°（供硬件控制模块执行）
- 坐标系：相机坐标系 → 机械臂基座坐标系（需标定外参）
