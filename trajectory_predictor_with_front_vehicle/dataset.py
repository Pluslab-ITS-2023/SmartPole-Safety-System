from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from preprocess import FEATURE_COLUMNS, load_and_preprocess_scene_csv


class TrajectoryDataset(Dataset):
    """過去の自車両と前方車両情報から未来位置のサンプルを作る。"""

    def __init__(
        self,
        data_directory,
        csv_files,
        seq_len=20,
        pred_len=10,
        stride=1,
        lane_width=4.0,
        max_distance=80.0,
        max_cross_distance=40.0,
        direction_similarity=0.5,
    ):
        self.seq_len = seq_len
        self.pred_len = pred_len
        self.samples = []

        data_directory = Path(data_directory)
        for filename in csv_files:
            csv_path = data_directory / filename
            print(f"Processing: {csv_path}")
            trajectories = load_and_preprocess_scene_csv(
                csv_path,
                lane_width=lane_width,
                max_distance=max_distance,
                max_cross_distance=max_cross_distance,
                direction_similarity=direction_similarity,
            )
            for trajectory in trajectories:
                self._create_samples(trajectory, stride)
        print(f"Generated samples: {len(self.samples)}")

    def _create_samples(self, trajectory, stride):
        features = trajectory[FEATURE_COLUMNS].to_numpy(dtype=np.float32)
        targets = trajectory[["x", "y"]].to_numpy(dtype=np.float32)
        window_size = self.seq_len + self.pred_len
        if len(features) < window_size:
            return

        for start in range(0, len(features) - window_size + 1, stride):
            input_end = start + self.seq_len
            target_end = input_end + self.pred_len
            self.samples.append(
                (
                    features[start:input_end],
                    targets[input_end:target_end],
                )
            )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        inputs, targets = self.samples[index]
        return (
            torch.tensor(inputs, dtype=torch.float32),
            torch.tensor(targets, dtype=torch.float32),
        )