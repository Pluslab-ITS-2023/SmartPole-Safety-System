# -*- coding: UTF-8 -*-

import argparse
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


def plot_trajectories(
    input_file_name: str,
    output_file_name: str,
    vehicle_ids: list[int] | None = None
) -> None:
    """
    CSVファイルからvehicleidごとの軌跡を描画する。

    vehicleidが指定された場合、そのIDのみ、または指定された範囲の
    vehicleidを描画する。

    緯度または経度がNaNであるデータは軌跡の描画対象から除外する。

    :param input_file_name:
        入力CSVファイル名
    :param output_file_name:
        出力画像ファイル名
    :param vehicle_ids:
        描画対象のvehicleid。
        1つ指定された場合はそのIDのみ、
        2つ指定された場合は最小値から最大値まで、
        指定されない場合は全IDを描画する。
    """

    input_file = Path(input_file_name)
    output_file = Path(output_file_name)

    # CSVファイルの存在確認
    if not input_file.is_file():
        print(f"⚠️ CSVファイル {input_file} が存在しません.")
        return

    # CSVファイルか確認
    if input_file.suffix.lower() != ".csv":
        print(
            f"⚠️ 指定されたファイル {input_file} "
            "はCSVファイルではありません."
        )
        return

    # CSV読み込み
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"⚠️ CSVファイルの読み込みに失敗しました ({e}).")
        return

    # 必要なカラム
    required_columns = [
        "vehicleid",
        "time",
        "x",
        "y"
    ]

    # 必要なカラムが存在するか確認
    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        print(f"⚠️ 以下のカラムが存在しません: {missing_columns}")
        return

    # vehicleidを数値として扱う
    try:
        df["vehicleid"] = pd.to_numeric(df["vehicleid"])
    except Exception as e:
        print(f"⚠️ vehicleidを数値として扱えません ({e}).")
        return

    # 緯度・経度を数値として扱う
    df["x"] = pd.to_numeric(
        df["x"],
        errors="coerce"
    )
    df["y"] = pd.to_numeric(
        df["y"],
        errors="coerce"
    )

    # vehicleidの範囲を指定
    if vehicle_ids:

        if len(vehicle_ids) == 1:
            # IDを1つ指定 → そのIDだけ
            target_ids = [vehicle_ids[0]]

        elif len(vehicle_ids) == 2:
            # IDを2つ指定 → min〜max
            min_id = min(vehicle_ids)
            max_id = max(vehicle_ids)

            target_ids = df[
                df["vehicleid"].between(min_id, max_id)
            ]["vehicleid"].unique()

        else:
            print("⚠️ vehicleidは1つまたは2つ指定してください.")
            return

        # 指定されたIDだけ残す
        df = df[df["vehicleid"].isin(target_ids)]

        if df.empty:
            print(
                "⚠️ 指定されたvehicleidに該当する"
                "データがありません."
            )
            return

    # vehicleid → timeの順に並び替える
    df = df.sort_values(
        by=["vehicleid", "time"]
    )

    # vehicleidごとにグループ化
    vehicle_groups = df.groupby("vehicleid")

    # 車両IDの一覧
    unique_vehicle_ids = df["vehicleid"].unique()

    # カラーマップ
    cmap = plt.get_cmap("tab20")

    # グラフ作成
    plt.figure(figsize=(10, 8))

    # vehicleidごとに描画
    for index, (vehicle_id, vehicle_data) in enumerate(vehicle_groups):

        # -------------------------------------------------
        # NaNの緯度・経度を除外
        # -------------------------------------------------
        vehicle_data = vehicle_data.dropna(
            subset=["x", "y"]
        )

        # 緯度または経度がすべてNaNの場合
        if vehicle_data.empty:
            continue

        color = cmap(index % cmap.N)

        plt.plot(
            vehicle_data["y"],
            vehicle_data["x"],
            color=color,
            linewidth=1.5,
            marker="o",
            markersize=2,
            label=str(vehicle_id)
        )

    plt.xlabel("Y")
    plt.ylabel("X")
    plt.title("Vehicle Trajectories")

    plt.grid(True)

    # 緯度・経度の縮尺を同じにする
    plt.axis("equal")

    # 車両数が多い場合は凡例を表示しない
    if len(unique_vehicle_ids) <= 20:
        plt.legend(
            title="vehicleid",
            bbox_to_anchor=(1.05, 1),
            loc="upper left"
        )

    plt.tight_layout()

    # 出力先ディレクトリを作成
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # 画像保存
    try:
        plt.savefig(
            output_file,
            format="png",
            dpi=150
        )
        print(
            f"✅ 軌跡画像 {output_file} を保存しました."
        )
    except Exception as e:
        print(
            f"⚠️ 画像の保存に失敗しました ({e})."
        )
        plt.close()
        return

    # ウィンドウ表示
    plt.show()

    plt.close()


def main() -> None:
    """
    コマンドライン引数で指定されたCSVファイルから
    車両ごとの軌跡を描画する。
    """

    parser = argparse.ArgumentParser(
        description=(
            "CSVファイルからvehicleidごとの軌跡を描画します."
        )
    )

    # 入力CSV
    parser.add_argument(
        "input_file",
        help="入力CSVファイル"
    )

    # 出力画像
    parser.add_argument(
        "output_file",
        help="出力画像ファイル"
    )

    # vehicleid
    parser.add_argument(
        "--vehicle-id",
        type=int,
        nargs="*",
        help=(
            "描画するvehicleid。"
            "1つ指定するとそのIDのみ、"
            "2つ指定するとその範囲、"
            "指定なしで全IDを描画します."
        )
    )

    args = parser.parse_args()

    # vehicleidの指定数を確認
    if args.vehicle_id is not None and len(args.vehicle_id) > 2:
        parser.error(
            "--vehicle-id は0〜2個のIDを指定してください."
        )

    plot_trajectories(
        args.input_file,
        args.output_file,
        args.vehicle_id
    )


if __name__ == "__main__":
    main()