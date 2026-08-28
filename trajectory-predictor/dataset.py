from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset

from preprocess import (
    load_and_preprocess_csv,
)


class TrajectoryDataset(Dataset):
    """
    車両軌跡からTransformerの学習用サンプルを生成する。

    入力:
        過去 seq_len 点

    出力:
        未来 pred_len 点
    """

    def __init__(
        self,
        data_directory,
        csv_files,
        seq_len=20,
        pred_len=10,
        stride=1,
    ):

        self.seq_len = seq_len
        self.pred_len = pred_len

        self.samples = []

        data_directory = Path(
            data_directory
        )

        for filename in csv_files:

            csv_path = (
                data_directory / filename
            )

            print(
                f"Processing: {csv_path}"
            )

            trajectories = (
                load_and_preprocess_csv(
                    csv_path
                )
            )

            for trajectory in trajectories:

                self._create_samples(
                    trajectory,
                    stride
                )

        print(
            f"Generated samples: "
            f"{len(self.samples)}"
        )

    def _create_samples(
        self,
        trajectory,
        stride,
    ):

        features = trajectory[
            [
                "x",
                "y",
                "speed",
                "heading_sin",
                "heading_cos",
            ]
        ].to_numpy(
            dtype=np.float32
        )

        targets = trajectory[
            [
                "x",
                "y",
            ]
        ].to_numpy(
            dtype=np.float32
        )

        window_size = (
            self.seq_len
            + self.pred_len
        )

        if len(features) < window_size:
            return

        for start in range(
            0,
            len(features) - window_size + 1,
            stride,
        ):

            input_end = (
                start + self.seq_len
            )

            target_end = (
                input_end
                + self.pred_len
            )

            input_sequence = features[
                start:input_end
            ]

            target_sequence = targets[
                input_end:target_end
            ]

            self.samples.append(
                (
                    input_sequence,
                    target_sequence,
                )
            )

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):

        inputs, targets = self.samples[
            index
        ]

        return (
            torch.tensor(
                inputs,
                dtype=torch.float32
            ),
            torch.tensor(
                targets,
                dtype=torch.float32
            ),
        )