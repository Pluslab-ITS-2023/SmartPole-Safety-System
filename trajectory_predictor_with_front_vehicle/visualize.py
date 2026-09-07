import argparse

import matplotlib.pyplot as plt
import torch

from model import TrajectoryTransformer
from preprocess import FEATURE_COLUMNS, load_and_preprocess_scene_csv


def visualize(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    trajectories = load_and_preprocess_scene_csv(
        args.csv,
        lane_width=args.lane_width,
        max_distance=args.max_distance,
        max_cross_distance=args.max_cross_distance,
        direction_similarity=args.direction_similarity,
    )
    trajectory = next(
        (
            candidate
            for candidate in trajectories
            if str(candidate["vehicleid"].iloc[0]) == str(args.vehicle_id)
        ),
        None,
    )
    if trajectory is None:
        raise ValueError(f"vehicleid={args.vehicle_id} が見つかりません。")

    if len(trajectory) < args.seq_len + args.pred_len:
        raise ValueError("軌跡の長さが不足しています。")

    model = TrajectoryTransformer(
        input_dim=17,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
        pred_len=args.pred_len,
    ).to(device)
    checkpoint = torch.load(args.model, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    input_data = trajectory[FEATURE_COLUMNS].to_numpy(dtype="float32")[
        :args.seq_len
    ]
    target = trajectory[["x", "y"]].to_numpy(dtype="float32")[
        args.seq_len:args.seq_len + args.pred_len
    ]
    inputs = torch.tensor(input_data).unsqueeze(0).to(device)
    with torch.no_grad():
        prediction = model(inputs).squeeze(0).cpu().numpy()

    plt.figure(figsize=(8, 8))
    plt.plot(input_data[:, 0], input_data[:, 1], marker="o", label="Observed")
    plt.plot(target[:, 0], target[:, 1], marker="o", label="Ground Truth")
    plt.plot(
        prediction[:, 0],
        prediction[:, 1],
        marker="x",
        linestyle="--",
        label="Prediction",
    )
    plt.scatter(
        input_data[-1, 0],
        input_data[-1, 1],
        s=100,
        label="Prediction Start",
    )
    plt.xlabel("X [m]")
    plt.ylabel("Y [m]")
    plt.title(f"Vehicle {args.vehicle_id} with Front Vehicle Features")
    plt.axis("equal")
    plt.grid()
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.output, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"グラフを保存しました: {args.output}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--vehicle-id", required=True)
    parser.add_argument("--model", default="trajectory_transformer_front_vehicle.pt")
    parser.add_argument("--output", default="trajectory_prediction_front_vehicle.png")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--pred-len", type=int, default=10)
    parser.add_argument("--d-model", type=int, default=128)
    parser.add_argument("--nhead", type=int, default=8)
    parser.add_argument("--num-layers", type=int, default=4)
    parser.add_argument("--dim-feedforward", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--lane-width", type=float, default=4.0)
    parser.add_argument("--max-distance", type=float, default=80.0)
    parser.add_argument("--max-cross-distance", type=float, default=40.0)
    parser.add_argument("--direction-similarity", type=float, default=0.5)
    return parser.parse_args()


if __name__ == "__main__":
    visualize(parse_args())