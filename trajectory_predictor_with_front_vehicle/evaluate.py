import argparse

import torch
from torch.utils.data import DataLoader

from dataset import TrajectoryDataset
from model import TrajectoryTransformer
from train import build_dataset, get_csv_files, split_files


def calculate_ade(predictions, targets):
    errors = torch.sqrt(torch.sum((predictions - targets) ** 2, dim=2))
    return errors.mean().item()


def calculate_fde(predictions, targets):
    errors = torch.sqrt(
        torch.sum((predictions[:, -1, :] - targets[:, -1, :]) ** 2, dim=1)
    )
    return errors.mean().item()


def evaluate(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _, _, test_files = split_files(get_csv_files(args.data_dir))
    dataset = build_dataset(args, test_files)
    if not dataset:
        raise ValueError("テスト用サンプルがありません。")
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )
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

    total_ade = 0.0
    total_fde = 0.0
    total_samples = 0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            predictions = model(inputs)
            batch_size = inputs.size(0)
            total_ade += calculate_ade(predictions, targets) * batch_size
            total_fde += calculate_fde(predictions, targets) * batch_size
            total_samples += batch_size

    print(f"ADE: {total_ade / total_samples:.4f} m")
    print(f"FDE: {total_fde / total_samples:.4f} m")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--model", default="trajectory_transformer_front_vehicle.pt")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--pred-len", type=int, default=10)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--d-model", type=int, default=128)
    parser.add_argument("--nhead", type=int, default=8)
    parser.add_argument("--num-layers", type=int, default=4)
    parser.add_argument("--dim-feedforward", type=int, default=256)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--lane-width", type=float, default=4.0)
    parser.add_argument("--max-distance", type=float, default=80.0)
    parser.add_argument("--max-cross-distance", type=float, default=40.0)
    parser.add_argument("--direction-similarity", type=float, default=0.5)
    return parser.parse_args()


if __name__ == "__main__":
    evaluate(parse_args())