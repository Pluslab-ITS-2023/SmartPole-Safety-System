import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dataset import TrajectoryDataset
from model import TrajectoryTransformer


def get_csv_files(data_directory):
    files = sorted(Path(data_directory).glob("*.csv"))
    if not files:
        raise FileNotFoundError("変換済みCSVファイルが見つかりません。")
    return [file.name for file in files]


def split_files(csv_files, train_ratio=0.7, validation_ratio=0.15):
    total = len(csv_files)
    if total < 3:
        raise ValueError("Train/Validation/Testには少なくとも3個のCSVが必要です。")
    train_end = max(1, int(total * train_ratio))
    validation_end = train_end + int(total * validation_ratio)
    validation_end = min(total - 1, max(train_end + 1, validation_end))
    return (
        csv_files[:train_end],
        csv_files[train_end:validation_end],
        csv_files[validation_end:],
    )


def evaluate_loss(model, loader, criterion, device):
    if len(loader) == 0:
        raise ValueError("評価用データがありません。seq_len/pred_lenを確認してください。")
    model.eval()
    total_loss = 0.0
    with torch.no_grad():
        for inputs, targets in loader:
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            total_loss += criterion(model(inputs), targets).item()
    return total_loss / len(loader)


def build_dataset(args, files):
    return TrajectoryDataset(
        args.data_dir,
        files,
        seq_len=args.seq_len,
        pred_len=args.pred_len,
        stride=args.stride,
        lane_width=args.lane_width,
        max_distance=args.max_distance,
        max_cross_distance=args.max_cross_distance,
        direction_similarity=args.direction_similarity,
    )


def build_model(args, device):
    return TrajectoryTransformer(
        input_dim=17,
        d_model=args.d_model,
        nhead=args.nhead,
        num_layers=args.num_layers,
        dim_feedforward=args.dim_feedforward,
        dropout=args.dropout,
        pred_len=args.pred_len,
    ).to(device)


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    files = get_csv_files(args.data_dir)
    train_files, validation_files, test_files = split_files(files)
    print(f"Device: {device}")
    print(f"Train: {len(train_files)}, Validation: {len(validation_files)}, Test: {len(test_files)}")

    train_dataset = build_dataset(args, train_files)
    validation_dataset = build_dataset(args, validation_files)
    test_dataset = build_dataset(args, test_files)
    if not train_dataset or not validation_dataset or not test_dataset:
        raise ValueError("学習・検証・テストのいずれかにサンプルがありません。")

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

    model = build_model(args, device)
    criterion = nn.MSELoss()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=0.5,
        patience=5,
    )
    best_validation_loss = float("inf")

    for epoch in range(args.epochs):
        model.train()
        total_loss = 0.0
        for inputs, targets in train_loader:
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            optimizer.zero_grad()
            loss = criterion(model(inputs), targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            total_loss += loss.item()

        train_loss = total_loss / len(train_loader)
        validation_loss = evaluate_loss(
            model,
            validation_loader,
            criterion,
            device,
        )
        scheduler.step(validation_loss)
        print(
            f"Epoch {epoch + 1:03d}/{args.epochs} | "
            f"Train: {train_loss:.6f} | Validation: {validation_loss:.6f}"
        )

        if validation_loss < best_validation_loss:
            best_validation_loss = validation_loss
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "epoch": epoch,
                    "validation_loss": validation_loss,
                    "seq_len": args.seq_len,
                    "pred_len": args.pred_len,
                    "input_dim": 17,
                },
                args.output,
            )

    checkpoint = torch.load(args.output, map_location=device)
    model.load_state_dict(checkpoint["model_state_dict"])
    test_loss = evaluate_loss(model, test_loader, criterion, device)
    print(f"Test Loss: {test_loss:.6f}")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output", default="trajectory_transformer_front_vehicle.pt")
    parser.add_argument("--seq-len", type=int, default=20)
    parser.add_argument("--pred-len", type=int, default=10)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
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
    train(parse_args())