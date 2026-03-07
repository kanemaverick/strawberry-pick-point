import numpy as np


class StrawberryPickerDecision:
    """
    基于多帧时序融合与空间信息的采摘顺序决策器
    """

    def __init__(self, history_frames=5):
        # 用于记录草莓状态的时序字典: {track_id: {"conf_history": [], "pos_history": []}}
        self.strawberry_tracks = {}
        self.history_frames = history_frames

    def update_tracks(self, tracking_results, current_3d_positions):
        """
        更新每帧的追踪状态
        :param tracking_results: YOLOv11 tracker (BoT-SORT) 返回的带有 track_id 的结果
        :param current_3d_positions: 这一帧计算出的所有草莓的 3D 相机坐标 {track_id: (X, Y, Z)}
        """
        # 获取当前帧检测到的 IDs
        current_ids = set()

        # 假设 tracking_results 包含了 id, conf 等信息 (具体根据 Ultralytics API 提取)
        if tracking_results.boxes.id is not None:
            boxes = tracking_results.boxes.xyxy.cpu().numpy()
            ids = tracking_results.boxes.id.int().cpu().numpy()
            confs = tracking_results.boxes.conf.cpu().numpy()

            for i, track_id in enumerate(ids):
                current_ids.add(track_id)

                # 1. 确保该 ID 的时序容器存在
                if track_id not in self.strawberry_tracks:
                    self.strawberry_tracks[track_id] = {
                        "conf_history": [],
                        "pos_history": [],
                    }

                # 2. 录入本帧置信度 (成熟度置信度)
                self.strawberry_tracks[track_id]["conf_history"].append(confs[i])

                # 3. 录入本帧 3D 坐标
                if track_id in current_3d_positions:
                    self.strawberry_tracks[track_id]["pos_history"].append(
                        current_3d_positions[track_id]
                    )

                # 4. 维护滑动窗口 (只保留最近 history_frames 帧)
                if (
                    len(self.strawberry_tracks[track_id]["conf_history"])
                    > self.history_frames
                ):
                    self.strawberry_tracks[track_id]["conf_history"].pop(0)
                if (
                    len(self.strawberry_tracks[track_id]["pos_history"])
                    > self.history_frames
                ):
                    self.strawberry_tracks[track_id]["pos_history"].pop(0)

        # 5. 可选清理: 如果某些 ID 长时间(比如超过10帧)未出现，可以清理掉以防内存泄露
        # 这里为了演示核心逻辑，暂不实现复杂的超时清理逻辑

    def _calculate_maturity_score(self, track_id):
        """计算成熟度得分: 取最近 N 帧置信度的平滑均值"""
        confs = self.strawberry_tracks[track_id]["conf_history"]
        if not confs:
            return 0.0
        return np.mean(confs)  # 取均值，抵抗单帧光照反光造成的置信度闪烁

    def _calculate_reachability_score(self, track_id):
        """
        计算空间可达性得分 (越近越好抓，得分越高)
        基准准则：
        1. Z轴(深度)优先：距离相机越近，一般越在最外层，不容易被其他草莓挡住
        2. XY平面居中度：越靠近相机视野中心(视野畸变小，机械臂奇异位形概率低)
        """
        pos_list = self.strawberry_tracks[track_id]["pos_history"]
        if not pos_list:
            return 0.0

        # 取最近几帧位置的均值，使得 3D 坐标更稳定
        stable_pos = np.mean(pos_list, axis=0)
        x, y, z = stable_pos

        # 距离基准得分 (假设相机工作距离 0.2m ~ 1.0m)
        # z 越小(越近)，z_score 越大
        z_score = max(0, 1.0 - z)

        # 偏心惩罚 (离中心点 X=0, Y=0 越远惩罚越大)
        center_distance = np.sqrt(x**2 + y**2)
        center_penalty = center_distance * 0.5

        reachability = z_score - center_penalty
        return max(0, reachability)  # 保证不为负

    def decide_next_target(self):
        """
        根据评分矩阵规划下一个抓取目标
        返回: 最佳目标 ID 及其平滑后的 3D 坐标
        """
        best_id = None
        best_score = -1.0
        best_stable_pos = None

        # 权重超参数，可根据实际测试调参
        w_maturity = 0.6  # 成熟度权重 (更倾向于摘最红的)
        w_reachability = 0.4  # 可达性权重 (兼顾好不好抓，防止机械臂死锁)

        for track_id, data in self.strawberry_tracks.items():
            # 条件过滤：只有连续出现过一定帧数(比如至少3帧)的草莓才参与竞选，过滤掉单帧误检
            if len(data["conf_history"]) < 3:
                continue

            maturity = self._calculate_maturity_score(track_id)
            reachability = self._calculate_reachability_score(track_id)

            # 综合评分
            total_score = (w_maturity * maturity) + (w_reachability * reachability)

            if total_score > best_score:
                best_score = total_score
                best_id = track_id
                best_stable_pos = np.mean(data["pos_history"], axis=0)

        return best_id, best_stable_pos
