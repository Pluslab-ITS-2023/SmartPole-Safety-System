import argparse

import numpy as np
import torch
from torch.utils.data import DataLoader

from dataset import TrajectoryDataset
from model import TrajectoryTransformer
from train import get_csv_files, split_files


def calculate_ade(
    predictions,
    targets,
):
    """
    ADE:
    未来全時刻における平均位置誤差[m]
    """

    errors = torch.sqrt(
        torch.sum(
            (predictions - targets) ** 2,
            dim=2
        )
    )

    return errors.mean().item()


def calculate_fde(
    predictions,
    targets,
):
    """
    FDE:
    最終予測位置の位置誤差[m]
    """

    final_prediction = (
        predictions[:, -1, :]
    )

    final_target = (
        targets[:, -1, :]
    )

    errors = torch.sqrt(
        torch.sum(
            (
                final_prediction
                - final_target
            ) ** 2,
            dim=1
        )
    )

    return errors.mean().item()


def evaluate(args):

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    csv_files = get_csv_files(
        args.data_dir
    )

    _, _, test_files = split_files(
        csv_files
    )

    dataset = TrajectoryDataset(
        args.data_dir,
        test_files,
        seq_len=args.seq_len,
        pred_len=args.pred_len,
        stride=args.stride,
    )

    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
    )

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

    total_ade = 0.0
    total_fde = 0.0

    total_samples = 0

    with torch.no_grad():

        for inputs, targets in loader:

            inputs = inputs.to(device)
            targets = targets.to(device)

            predictions = model(
                inputs
            )

            batch_size = (
                inputs.size(0)
            )

            ade = calculate_ade(
                predictions,
                targets,
            )

            fde = calculate_fde(
                predictions,
                targets,
            )

            total_ade += (
                ade * batch_size
            )

            total_fde += (
                fde * batch_size
            )

            total_samples += (
                batch_size
            )

    print(
        f"ADE: "
        f"{total_ade / total_samples:.4f} m"
    )

    print(
        f"FDE: "
        f"{total_fde / total_samples:.4f} m"
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data-dir",
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
        "--stride",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
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

    parser.add_argument(
        "--num-workers",
        type=int,
        default=4,
    )

    args = parser.parse_args()

    evaluate(args)


if __name__ == "__main__":
    main()