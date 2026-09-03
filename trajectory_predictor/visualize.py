import argparse

import matplotlib.pyplot as plt
import torch

from preprocess import (
    load_and_preprocess_csv,
)
from model import (
    TrajectoryTransformer,
)


def visualize(
    args
):

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    # --------------------------------------------------
    # CSV
    # --------------------------------------------------

    trajectories = (
        load_and_preprocess_csv(
            args.csv
        )
    )

    if not trajectories:
        raise RuntimeError(
            "利用可能な車両軌跡がありません。"
        )

    # vehicleid指定
    trajectory = None

    for candidate in trajectories:

        if (
            int(candidate["vehicleid"].iloc[0])
            == args.vehicle_id
        ):
            trajectory = candidate
            break

    if trajectory is None:
        raise ValueError(
            f"vehicleid={args.vehicle_id} "
            f"が見つかりません。"
        )

    # --------------------------------------------------
    # Model
    # --------------------------------------------------

    model = TrajectoryTransformer(
        input_dim=5,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
        pred_len=args.pred_len,
    ).to(device)

    checkpoint = torch.load(
        args.model,
        map_location=device
    )

    model.load_state_dict(
        checkpoint[
            "model_state_dict"
        ]
    )

    model.eval()

    # --------------------------------------------------
    # 入力
    # --------------------------------------------------

    features = trajectory[
        [
            "x",
            "y",
            "speed",
            "heading_sin",
            "heading_cos",
        ]
    ].to_numpy()

    if len(features) < (
        args.seq_len
        + args.pred_len
    ):
        raise ValueError(
            "軌跡の長さが不足しています。"
        )

    input_data = features[
        :args.seq_len
    ]

    target = trajectory[
        [
            "x",
            "y",
        ]
    ].to_numpy()

    target = target[
        args.seq_len:
        args.seq_len + args.pred_len
    ]

    inputs = torch.tensor(
        input_data,
        dtype=torch.float32
    ).unsqueeze(0)

    inputs = inputs.to(device)

    # --------------------------------------------------
    # Prediction
    # --------------------------------------------------

    with torch.no_grad():

        prediction = model(
            inputs
        )

    prediction = (
        prediction
        .squeeze(0)
        .cpu()
        .numpy()
    )

    # --------------------------------------------------
    # Plot
    # --------------------------------------------------

    plt.figure(
        figsize=(8, 8)
    )

    # 過去軌跡
    plt.plot(
        input_data[:, 0],
        input_data[:, 1],
        marker="o",
        label="Observed"
    )

    # 正解未来軌跡
    plt.plot(
        target[:, 0],
        target[:, 1],
        marker="o",
        label="Ground Truth"
    )

    # 予測未来軌跡
    plt.plot(
        prediction[:, 0],
        prediction[:, 1],
        marker="x",
        linestyle="--",
        label="Prediction"
    )

    # 観測最後の位置
    plt.scatter(
        input_data[-1, 0],
        input_data[-1, 1],
        s=100,
        label="Prediction Start"
    )

    plt.xlabel(
        "X [m]"
    )

    plt.ylabel(
        "Y [m]"
    )

    plt.title(
        f"Vehicle {args.vehicle_id}"
    )

    plt.axis(
        "equal"
    )

    plt.grid()

    plt.legend()

    plt.tight_layout()

    output_file = "trajectory_prediction.png"

    plt.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    print(
        f"グラフを保存しました: {output_file}"
    )

    plt.close()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--csv",
        required=True,
    )

    parser.add_argument(
        "--vehicle-id",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--model",
        default="trajectory_transformer.pt",
    )

    parser.add_argument(
        "--seq-len",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--pred-len",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--d-model",
        type=int,
        default=128,
    )

    parser.add_argument(
        "--nhead",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--num-layers",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--dim-feedforward",
        type=int,
        default=256,
    )

    parser.add_argument(
        "--dropout",
        type=float,
        default=0.1,
    )

    args = parser.parse_args()

    visualize(args)


if __name__ == "__main__":
    main()
