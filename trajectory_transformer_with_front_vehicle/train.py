# -*- coding: UTF-8 -*-

import argparse
import csv
import logging
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dataset import TrajectoryDataset
from model import TrajectoryTransformer


def get_csv_files(
    data_directory: str
) -> list[Path]:

    data_directory = Path(
        data_directory
    )

    return sorted(
        [
            file
            for file in data_directory.iterdir()
            if file.is_file()
            and file.suffix.lower() == ".csv"
        ]
    )


def split_files(
    csv_files: list[Path]
) -> tuple[list[Path], list[Path], list[Path]]:

    total = len(csv_files)

    train_end = int(
        total * 0.7
    )

    validation_end = int(
        total * 0.85
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
        test_files
    )


def create_logger(
    log_file: Path
) -> logging.Logger:

    logger = logging.getLogger(
        "trajectory_training"
    )

    logger.setLevel(
        logging.INFO
    )

    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s - %(message)s"
    )

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8"
    )

    file_handler.setFormatter(
        formatter
    )

    console_handler = logging.StreamHandler()

    console_handler.setFormatter(
        logging.Formatter(
            "%(message)s"
        )
    )

    logger.addHandler(
        file_handler
    )

    logger.addHandler(
        console_handler
    )

    return logger


def train_one_epoch(
    model,
    loader,
    optimizer,
    criterion,
    device,
    future_times
):

    model.train()

    total_loss = 0.0

    for batch in loader:

        ego = batch["ego"].to(
            device,
            non_blocking=True
        )

        neighbors = batch["neighbors"].to(
            device,
            non_blocking=True
        )

        front_mask = batch["front_mask"].to(
            device,
            non_blocking=True
        )

        neighbor_mask = batch["neighbor_mask"].to(
            device,
            non_blocking=True
        )

        target = batch["target"].to(
            device,
            non_blocking=True
        )

        optimizer.zero_grad()

        prediction, _ = model(
            ego,
            neighbors,
            front_mask,
            neighbor_mask,
            future_times
        )

        loss = criterion(
            prediction,
            target
        )

        loss.backward()

        optimizer.step()

        total_loss += (
            loss.item()
            * ego.size(0)
        )

    return (
        total_loss
        / len(loader.dataset)
    )


@torch.no_grad()
def validate(
    model,
    loader,
    criterion,
    device,
    future_times
):

    model.eval()

    total_loss = 0.0

    for batch in loader:

        ego = batch["ego"].to(
            device,
            non_blocking=True
        )

        neighbors = batch["neighbors"].to(
            device,
            non_blocking=True
        )

        front_mask = batch["front_mask"].to(
            device,
            non_blocking=True
        )

        neighbor_mask = batch["neighbor_mask"].to(
            device,
            non_blocking=True
        )

        target = batch["target"].to(
            device,
            non_blocking=True
        )

        prediction, _ = model(
            ego,
            neighbors,
            front_mask,
            neighbor_mask,
            future_times
        )

        loss = criterion(
            prediction,
            target
        )

        total_loss += (
            loss.item()
            * ego.size(0)
        )

    return (
        total_loss
        / len(loader.dataset)
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "前方車両Attention付き"
            "Trajectory Transformer"
        )
    )

    parser.add_argument(
        "--data-dir",
        required=True
    )

    parser.add_argument(
        "--seq-len",
        type=int,
        default=30
    )

    parser.add_argument(
        "--pred-len",
        type=int,
        default=50
    )

    parser.add_argument(
        "--max-neighbors",
        type=int,
        default=8
    )

    parser.add_argument(
        "--neighbor-distance",
        type=float,
        default=50.0
    )

    parser.add_argument(
        "--front-angle",
        type=float,
        default=45.0
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=256
    )

    parser.add_argument(
        "--epochs",
        type=int,
        default=50
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-4
    )

    parser.add_argument(
        "--num-workers",
        type=int,
        default=4
    )

    parser.add_argument(
        "--d-model",
        type=int,
        default=128
    )

    parser.add_argument(
        "--nhead",
        type=int,
        default=8
    )

    parser.add_argument(
        "--num-layers",
        type=int,
        default=4
    )

    parser.add_argument(
        "--dim-feedforward",
        type=int,
        default=256
    )

    parser.add_argument(
        "--dropout",
        type=float,
        default=0.1
    )

    parser.add_argument(
        "--front-attention-bias",
        type=float,
        default=1.0
    )

    parser.add_argument(
        "--output",
        default="trajectory_transformer.pt"
    )

    args = parser.parse_args()

    # ==============================================
    # 出力ディレクトリ
    # ==============================================

    output_path = Path(
        args.output
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    log_directory = Path(
        "logs"
    ) / output_path.stem

    log_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    logger = create_logger(
        log_directory / "train.log"
    )

    # ==============================================
    # GPU
    # ==============================================

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    logger.info(
        f"Device: {device}"
    )

    if torch.cuda.is_available():

        logger.info(
            f"GPU: "
            f"{torch.cuda.get_device_name(0)}"
        )

        logger.info(
            f"CUDA: "
            f"{torch.version.cuda}"
        )

    # ==============================================
    # CSV
    # ==============================================

    csv_files = get_csv_files(
        args.data_dir
    )

    train_files, validation_files, test_files = (
        split_files(csv_files)
    )

    logger.info(
        f"CSV files: {len(csv_files)}"
    )

    logger.info(
        f"Train files: {len(train_files)}"
    )

    logger.info(
        f"Validation files: "
        f"{len(validation_files)}"
    )

    logger.info(
        f"Test files: {len(test_files)}"
    )

    # ==============================================
    # Dataset
    # ==============================================

    train_dataset = TrajectoryDataset(
        args.data_dir,
        train_files,
        seq_len=args.seq_len,
        pred_len=args.pred_len,
        max_neighbors=args.max_neighbors,
        neighbor_distance=args.neighbor_distance,
        front_angle=args.front_angle
    )

    validation_dataset = TrajectoryDataset(
        args.data_dir,
        validation_files,
        seq_len=args.seq_len,
        pred_len=args.pred_len,
        max_neighbors=args.max_neighbors,
        neighbor_distance=args.neighbor_distance,
        front_angle=args.front_angle
    )

    logger.info(
        f"Train samples: "
        f"{len(train_dataset)}"
    )

    logger.info(
        f"Validation samples: "
        f"{len(validation_dataset)}"
    )

    # ==============================================
    # DataLoader
    # ==============================================

    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available()
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        pin_memory=torch.cuda.is_available()
    )

    # ==============================================
    # Model
    # ==============================================

    model = TrajectoryTransformer(
        ego_dim=5,
        neighbor_dim=6,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
        pred_len=args.pred_len,
        front_attention_bias=args.front_attention_bias
    ).to(device)

    # ==============================================
    # Optimizer
    # ==============================================

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=1e-4
    )

    criterion = nn.MSELoss()

    # ==============================================
    # Future time
    # ==============================================

    future_times = (
        torch.arange(
            1,
            args.pred_len + 1,
            dtype=torch.float32
        )
        * 0.1
    ).to(device)

    # ==============================================
    # Loss CSV
    # ==============================================

    loss_file = (
        log_directory
        / "loss.csv"
    )

    with open(
        loss_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "epoch",
                "train_loss",
                "validation_loss"
            ]
        )

    # ==============================================
    # 学習
    # ==============================================

    best_validation_loss = float(
        "inf"
    )

    for epoch in range(
        1,
        args.epochs + 1
    ):

        train_loss = train_one_epoch(
            model,
            train_loader,
            optimizer,
            criterion,
            device,
            future_times
        )

        validation_loss = validate(
            model,
            validation_loader,
            criterion,
            device,
            future_times
        )

        logger.info(
            f"Epoch [{epoch}/{args.epochs}] "
            f"Train Loss: {train_loss:.6f} "
            f"Val Loss: {validation_loss:.6f}"
        )

        with open(
            loss_file,
            "a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow(
                [
                    epoch,
                    train_loss,
                    validation_loss
                ]
            )

        # ==========================================
        # Best Model
        # ==========================================

        if validation_loss < best_validation_loss:

            best_validation_loss = (
                validation_loss
            )

            torch.save(
                {
                    "model_state_dict":
                        model.state_dict(),

                    "model_config": {
                        "ego_dim": 5,
                        "neighbor_dim": 6,
                        "d_model": args.d_model,
                        "nhead": args.nhead,
                        "num_layers": args.num_layers,
                        "dim_feedforward":
                            args.dim_feedforward,
                        "dropout": args.dropout,
                        "pred_len":
                            args.pred_len,
                        "front_attention_bias":
                            args.front_attention_bias
                    }
                },
                output_path
            )

            logger.info(
                "  -> Best model saved."
            )

    logger.info(
        "Training finished."
    )


if __name__ == "__main__":
    main()
    