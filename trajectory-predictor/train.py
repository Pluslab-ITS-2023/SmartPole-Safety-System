import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dataset import TrajectoryDataset
from model import TrajectoryTransformer


def get_csv_files(
    data_directory
):
    """
    データディレクトリ内のCSVを日付順に取得する。
    """

    data_directory = Path(
        data_directory
    )

    files = sorted(
        data_directory.glob(
            "t_corrected_pos_info_*.csv"
        )
    )

    if not files:
        raise FileNotFoundError(
            "CSVファイルが見つかりません。"
        )

    return [
        file.name
        for file in files
    ]


def split_files(
    csv_files,
    train_ratio=0.7,
    validation_ratio=0.15,
):
    """
    日付順にCSVをTrain / Validation / Testへ分割する。
    """

    total = len(csv_files)

    train_end = int(
        total * train_ratio
    )

    validation_end = (
        train_end
        + int(
            total * validation_ratio
        )
    )

    train_files = csv_files[
        :train_end
    ]

    validation_files = csv_files[
        train_end:validation_end
    ]

    test_files = csv_files[
        validation_end:
    ]

    return (
        train_files,
        validation_files,
        test_files,
    )


def evaluate_loss(
    model,
    loader,
    criterion,
    device,
):
    """
    Validation / Test用のLossを計算する。
    """

    model.eval()

    total_loss = 0.0

    with torch.no_grad():

        for inputs, targets in loader:

            inputs = inputs.to(
                device,
                non_blocking=True
            )

            targets = targets.to(
                device,
                non_blocking=True
            )

            predictions = model(
                inputs
            )

            loss = criterion(
                predictions,
                targets
            )

            total_loss += loss.item()

    return (
        total_loss / len(loader)
    )


def train(args):

    # =====================================================
    # Device
    # =====================================================

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        f"Device: {device}"
    )

    # =====================================================
    # CSV
    # =====================================================

    csv_files = get_csv_files(
        args.data_dir
    )

    (
        train_files,
        validation_files,
        test_files,
    ) = split_files(
        csv_files
    )

    print(
        f"Train files: {len(train_files)}"
    )

    print(
        f"Validation files: "
        f"{len(validation_files)}"
    )

    print(
        f"Test files: {len(test_files)}"
    )

    # =====================================================
    # Dataset
    # =====================================================

    train_dataset = TrajectoryDataset(
        args.data_dir,
        train_files,
        seq_len=args.seq_len,
        pred_len=args.pred_len,
        stride=args.stride,
    )

    validation_dataset = TrajectoryDataset(
        args.data_dir,
        validation_files,
        seq_len=args.seq_len,
        pred_len=args.pred_len,
        stride=args.stride,
    )

    test_dataset = TrajectoryDataset(
        args.data_dir,
        test_files,
        seq_len=args.seq_len,
        pred_len=args.pred_len,
        stride=args.stride,
    )

    # =====================================================
    # DataLoader
    # =====================================================

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=True,
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=True,
    )

    # =====================================================
    # Model
    # =====================================================

    model = TrajectoryTransformer(
        input_dim=5,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
        pred_len=args.pred_len,
    ).to(device)

    print(model)

    # =====================================================
    # Loss
    # =====================================================

    criterion = nn.MSELoss()

    # =====================================================
    # Optimizer
    # =====================================================

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=1e-4,
    )

    # =====================================================
    # Scheduler
    # =====================================================

    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.5,
        patience=5,
    )

    best_validation_loss = float(
        "inf"
    )

    # =====================================================
    # Training
    # =====================================================

    for epoch in range(
        args.epochs
    ):

        model.train()

        train_loss = 0.0

        for inputs, targets in train_loader:

            inputs = inputs.to(
                device,
                non_blocking=True
            )

            targets = targets.to(
                device,
                non_blocking=True
            )

            optimizer.zero_grad()

            predictions = model(
                inputs
            )

            loss = criterion(
                predictions,
                targets
            )

            loss.backward()

            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                max_norm=1.0
            )

            optimizer.step()

            train_loss += loss.item()

        train_loss /= len(
            train_loader
        )

        validation_loss = evaluate_loss(
            model,
            validation_loader,
            criterion,
            device,
        )

        scheduler.step(
            validation_loss
        )

        print(
            f"Epoch "
            f"{epoch + 1:03d}/{args.epochs} "
            f"| Train: "
            f"{train_loss:.6f} "
            f"| Validation: "
            f"{validation_loss:.6f}"
        )

        # =================================================
        # Best model
        # =================================================

        if validation_loss < best_validation_loss:

            best_validation_loss = (
                validation_loss
            )

            torch.save(
                {
                    "model_state_dict":
                        model.state_dict(),

                    "optimizer_state_dict":
                        optimizer.state_dict(),

                    "epoch":
                        epoch,

                    "validation_loss":
                        validation_loss,

                    "seq_len":
                        args.seq_len,

                    "pred_len":
                        args.pred_len,
                },
                args.output,
            )

            print(
                f"  → Model saved: "
                f"{args.output}"
            )

    # =====================================================
    # Test
    # =====================================================

    checkpoint = torch.load(
        args.output,
        map_location=device
    )

    model.load_state_dict(
        checkpoint[
            "model_state_dict"
        ]
    )

    test_loss = evaluate_loss(
        model,
        test_loader,
        criterion,
        device,
    )

    print(
        f"\nTest Loss: "
        f"{test_loss:.6f}"
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--data-dir",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=str,
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
        "--epochs",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-4,
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

    train(args)


if __name__ == "__main__":
    main()