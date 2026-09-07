# -*- coding: UTF-8 -*-

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


class TrajectoryDataset(Dataset):
    """
    軌跡予測用Dataset

    自車：
        x
        y
        speed
        heading_sin
        heading_cos

    周辺車両：
        relative_forward
        relative_lateral
        speed
        heading_sin
        heading_cos
        vehicle_type

    を使用する。
    """

    def __init__(
        self,
        data_directory: str,
        csv_files: list[Path],
        seq_len: int = 30,
        pred_len: int = 50,
        stride: int = 1,
        max_neighbors: int = 8,
        neighbor_distance: float = 50.0,
        front_angle: float = 45.0
    ) -> None:
        self.data_directory = Path(
            data_directory
        )

        self.seq_len = seq_len
        self.pred_len = pred_len
        self.max_neighbors = max_neighbors
        self.neighbor_distance = neighbor_distance
        self.front_angle = front_angle

        self.samples = []

        # CSVを読み込む
        for csv_file in csv_files:

            df = pd.read_csv(csv_file)

            required_columns = [
                "vehicleid",
                "time",
                "x",
                "y",
                "speed",
                "heading",
                "vehiclesizeclassification"
            ]

            missing_columns = [
                column
                for column in required_columns
                if column not in df.columns
            ]

            if missing_columns:
                raise ValueError(
                    f"{csv_file} に必要なカラムがありません: "
                    f"{missing_columns}"
                )

            df["time"] = pd.to_datetime(
                df["time"],
                format="mixed"
            )

            df = df.sort_values(
                [
                    "vehicleid",
                    "time"
                ]
            )

            # ------------------------------------------
            # 車両ごとにサンプルを作成
            # ------------------------------------------

            for vehicle_id, vehicle_df in df.groupby(
                "vehicleid"
            ):

                vehicle_df = vehicle_df.reset_index(
                    drop=True
                )

                required_length = (
                    seq_len + pred_len
                )

                if len(vehicle_df) < required_length:
                    continue

                # --------------------------------------
                # window
                # --------------------------------------

                for start in range(
                    0,
                    len(vehicle_df) - required_length + 1,
                    stride
                ):

                    end_history = (
                        start + seq_len
                    )

                    end_future = (
                        end_history + pred_len
                    )

                    history = vehicle_df.iloc[
                        start:end_history
                    ]

                    future = vehicle_df.iloc[
                        end_history:end_future
                    ]

                    # NaNがあるサンプルは除外
                    if (
                        history[
                            ["x", "y", "speed", "heading"]
                        ].isna().any().any()
                        or
                        future[
                            ["x", "y"]
                        ].isna().any().any()
                    ):
                        continue

                    self.samples.append(
                        {
                            "file": csv_file,
                            "data": df,
                            "vehicle_id": vehicle_id,
                            "start": start
                        }
                    )

    def __len__(self) -> int:
        return len(self.samples)

    def _heading_to_vector(
        self,
        heading: float
    ) -> tuple[float, float]:
        """
        headingから進行方向ベクトルを作る。

        heading:
            北=0°
            時計回り
        """

        radians = np.deg2rad(
            heading
        )

        forward_x = np.sin(
            radians
        )

        forward_y = np.cos(
            radians
        )

        return forward_x, forward_y

    def _get_neighbors(
        self,
        ego_row: pd.Series,
        same_time: pd.DataFrame
    ) -> tuple[np.ndarray, np.ndarray]:

        ego_x = ego_row["x"]
        ego_y = ego_row["y"]
        ego_heading = ego_row["heading"]

        # 自車の進行方向
        forward_x, forward_y = (
            self._heading_to_vector(
                ego_heading
            )
        )

        # 自車に対して右方向のベクトル
        right_x = forward_y
        right_y = -forward_x

        candidates = []

        for _, row in same_time.iterrows():

            # 自車自身を除外
            if row["vehicleid"] == ego_row["vehicleid"]:
                continue

            if (
                pd.isna(row["x"])
                or pd.isna(row["y"])
                or pd.isna(row["speed"])
                or pd.isna(row["heading"])
            ):
                continue

            dx = row["x"] - ego_x
            dy = row["y"] - ego_y

            distance = np.sqrt(
                dx ** 2 + dy ** 2
            )

            # ------------------------------------------
            # 50m以上離れている車両を除外
            # ------------------------------------------

            if distance > self.neighbor_distance:
                continue

            # ------------------------------------------
            # 自車から見た前後方向
            # ------------------------------------------

            relative_forward = (
                dx * forward_x
                + dy * forward_y
            )

            # ------------------------------------------
            # 自車から見た左右方向
            # ------------------------------------------

            relative_lateral = (
                dx * right_x
                + dy * right_y
            )

            # ------------------------------------------
            # 前方角度
            # ------------------------------------------

            angle = np.degrees(
                np.arctan2(
                    abs(relative_lateral),
                    relative_forward
                )
            )

            is_front = (
                relative_forward > 0
                and angle <= self.front_angle
            )

            # headingのsin/cos
            heading_rad = np.deg2rad(
                row["heading"]
            )

            heading_sin = np.sin(
                heading_rad
            )

            heading_cos = np.cos(
                heading_rad
            )

            candidates.append(
                {
                    "distance": distance,
                    "relative_forward": relative_forward,
                    "relative_lateral": relative_lateral,
                    "speed": row["speed"],
                    "heading_sin": heading_sin,
                    "heading_cos": heading_cos,
                    "vehicle_type": row[
                        "vehiclesizeclassification"
                    ],
                    "is_front": is_front
                }
            )

        # ----------------------------------------------
        # 前方車両を優先
        # ----------------------------------------------

        candidates.sort(
            key=lambda x: (
                not x["is_front"],
                x["distance"]
            )
        )

        # 最大K台
        candidates = candidates[
            :self.max_neighbors
        ]

        neighbors = np.zeros(
            (
                self.max_neighbors,
                6
            ),
            dtype=np.float32
        )

        front_mask = np.zeros(
            self.max_neighbors,
            dtype=bool
        )

        for index, candidate in enumerate(
            candidates
        ):

            neighbors[index] = [
                candidate["relative_forward"],
                candidate["relative_lateral"],
                candidate["speed"],
                candidate["heading_sin"],
                candidate["heading_cos"],
                candidate["vehicle_type"]
            ]

            front_mask[index] = (
                candidate["is_front"]
            )

        neighbor_mask = np.zeros(
            self.max_neighbors,
            dtype=bool
        )

        neighbor_mask[
            :len(candidates)
        ] = True

        return (
            neighbors,
            front_mask,
            neighbor_mask
        )

    def __getitem__(
        self,
        index: int
    ) -> dict[str, torch.Tensor]:

        sample = self.samples[index]

        df = sample["data"]

        vehicle_id = sample["vehicle_id"]

        start = sample["start"]

        # ----------------------------------------------
        # 自車
        # ----------------------------------------------

        vehicle_df = df[
            df["vehicleid"] == vehicle_id
        ].sort_values("time")

        vehicle_df = vehicle_df.reset_index(
            drop=True
        )

        history = vehicle_df.iloc[
            start:start + self.seq_len
        ]

        future = vehicle_df.iloc[
            start + self.seq_len:
            start + self.seq_len + self.pred_len
        ]

        # ----------------------------------------------
        # 自車入力
        # ----------------------------------------------

        ego_features = []

        for _, row in history.iterrows():

            heading_rad = np.deg2rad(
                row["heading"]
            )

            ego_features.append(
                [
                    row["x"],
                    row["y"],
                    row["speed"],
                    np.sin(heading_rad),
                    np.cos(heading_rad)
                ]
            )

        ego_features = np.asarray(
            ego_features,
            dtype=np.float32
        )

        # ----------------------------------------------
        # 周辺車両
        # ----------------------------------------------

        neighbor_features = []

        front_masks = []

        neighbor_masks = []

        for _, ego_row in history.iterrows():

            same_time = df[
                df["time"] == ego_row["time"]
            ]

            neighbors, front_mask, neighbor_mask = (
                self._get_neighbors(
                    ego_row,
                    same_time
                )
            )

            neighbor_features.append(
                neighbors
            )

            front_masks.append(
                front_mask
            )

            neighbor_masks.append(
                neighbor_mask
            )

        neighbor_features = np.asarray(
            neighbor_features,
            dtype=np.float32
        )

        front_masks = np.asarray(
            front_masks,
            dtype=bool
        )

        neighbor_masks = np.asarray(
            neighbor_masks,
            dtype=bool
        )

        # ----------------------------------------------
        # 予測対象
        # ----------------------------------------------

        last_x = history.iloc[-1]["x"]
        last_y = history.iloc[-1]["y"]

        targets = future[
            ["x", "y"]
        ].to_numpy(
            dtype=np.float32
        )

        # 最後の観測位置からの相対座標にする
        targets[:, 0] -= last_x
        targets[:, 1] -= last_y

        return {
            "ego": torch.from_numpy(
                ego_features
            ),
            "neighbors": torch.from_numpy(
                neighbor_features
            ),
            "front_mask": torch.from_numpy(
                front_masks
            ),
            "neighbor_mask": torch.from_numpy(
                neighbor_masks
            ),
            "target": torch.from_numpy(
                targets
            )
        }
        