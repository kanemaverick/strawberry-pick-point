# 🍓 机械臂仿真团队协作指南 (基于 Docker + ROS + MuJoCo)

考虑到本项目后续将引入 ROS（机器人操作系统）进行机械臂的高级运动规划，为了彻底解决团队成员之间操作系统版本不同、依赖冲突（"在我电脑上明明能跑"）的问题，仿真端统一采用 **Docker 容器化** 方案进行开发与同步。

---

## 1. 核心协作理念：代码与环境分离

在 Docker 协作模式下，我们必须区分**“环境”**和**“代码”**：

- **环境（Image/容器）**：包含 Ubuntu 系统、ROS、MuJoCo、Python 库等。这部分通过 `Dockerfile` 定义，只在环境依赖更新时才需要重新构建（Build）。
- **代码与资产（Host/宿主机）**：所有的 Python 脚本、C++ 源码、XML 模型、STL 文件都存放在**你的本地电脑**上，由 Git 进行版本控制。
- **结合方式（Volume 映射）**：运行 Docker 容器时，我们会把本地的 `simulation/` 文件夹**实时映射**到容器内部。你在本地用 VSCode 修改了代码，容器里会立刻生效，直接运行即可，**不需要重新打包镜像**。

---

## 2. 需要提交到 GitHub 的核心文件

为了让大家能一键启动环境，负责配置环境的同学（如陆坚其）需要向 GitHub 提交以下三个文件（建议放在 `simulation/docker/` 目录下）：

1. **`Dockerfile`**：定义如何一步步安装 ROS 和 MuJoCo。
2. **`docker-compose.yml`**：定义如何启动容器，包含 GPU 加速和图形界面（GUI）转发配置（因为 MuJoCo 和 Rviz 需要弹窗显示）。
3. **`requirements.txt`**：Python 依赖清单。

### 参考模板：`docker-compose.yml` (支持显示 MuJoCo 图形界面)

```yaml
version: '3.8'
services:
  strawberry_sim:
    build: 
      context: ..
      dockerfile: docker/Dockerfile
    image: strawberry_sim_env:v1
    container_name: mujoco_ros_sim
    # 挂载本地项目根目录到容器内部的 /workspace
    volumes:
      - ../../:/workspace
      - /tmp/.X11-unix:/tmp/.X11-unix:rw # 用于图形界面转发
    environment:
      - DISPLAY=$DISPLAY
      - QT_X11_NO_MITSHM=1
    # 启用 NVIDIA GPU 渲染（重要！）
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu, compute, video, utility]
    network_mode: host
    command: /bin/bash
    tty: true
```

---

## 3. 团队成员日常开发工作流

假设小明要开始开发仿真模块，他只需要遵循以下步骤：

### 初始准备（仅一次）
1. 在本地电脑安装 **Docker** 和 **NVIDIA Container Toolkit**（用于 GPU 渲染）。
2. `git clone` 拉取项目代码。

### 步骤 1：启动环境与开发
打开终端，进入项目的 `simulation/docker/` 目录：

```bash
# 允许 Docker 容器访问本地的 X11 图形界面（Linux/WSL 必备）
xhost +local:root

# 一键编译并启动容器（后台运行）
docker-compose up -d

# 进入容器的交互式终端
docker exec -it mujoco_ros_sim /bin/bash
```
此时你已经进入了配置好 ROS 和 MuJoCo 的干净环境。由于目录已映射，你可以直接在容器里运行：
`python3 /workspace/simulation/main_sim.py`

### 步骤 2：在本地写代码
**不要用容器里的 vim 写代码！** 
在你的宿主机（Windows/Ubuntu）上，直接用 VSCode 打开 `机械臂草莓` 项目。
当你修改了 `main_sim.py` 并按下 `Ctrl+S` 时，由于目录映射，容器内运行的代码会立刻应用最新的修改。

### 步骤 3：Git 同步代码
完全像普通项目一样，在**本地宿主机**使用 Git 提交代码：
```bash
git add simulation/main_sim.py
git commit -m "feat: 更新 MuJoCo 抓取逻辑"
git push
```
其他团队成员拉取代码后，只要执行 `docker exec` 进入他们自己电脑上的容器，运行的就是你最新提交的代码。

---

## 4. 环境更新了怎么办？

如果某天发现需要安装一个新的 ROS 包或者 Python 库（比如 `pip install opencv-python`）：
1. 负责环境的同学修改 `Dockerfile` 或 `requirements.txt`。
2. 提交到 GitHub 并通知大家：“环境更新了！”。
3. 其他同学拉取代码后，只需要重新构建镜像即可：
   ```bash
   docker-compose build
   docker-compose up -d
   ```

## 5. 补充：VSCode Dev Containers（推荐进阶玩法）

如果团队成员都使用 VSCode，可以安装 **Dev Containers** 插件。
只需在项目根目录添加一个 `.devcontainer/devcontainer.json` 文件。大家在 VSCode 打开项目时，右下角会弹窗提示“是否在容器中重新打开”。点击确认，VSCode 会自动完成 Docker 镜像构建、目录映射、并把终端自动切换到容器内部。体验如丝般顺滑，完全感觉不到 Docker 的存在。