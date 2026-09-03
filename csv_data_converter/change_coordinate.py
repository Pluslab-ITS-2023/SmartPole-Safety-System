# -*- coding: UTF-8 -*-

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def convert_to_local_coordinates(
    input_file_name: str,
    output_directory_name: str,
    reference_latitude: float,
    reference_longitude: float,
) -> None:
    """
    CSVファイルの緯度・経度をローカル座標系へ変換して保存する関数

    緯度・経度を以下のローカル座標へ変換する。

    x:
        東方向 [m]

    y:
        北方向 [m]

    latitude、longitudeは削除され、
    x、yに置き換えられる。

    :param input_file_name:
        入力されたCSVファイル名
    :param output_directory_name:
        出力先のディレクトリ名
    :param reference_latitude:
        ローカル座標系の基準点となる緯度 [deg]
    :param reference_longitude:
        ローカル座標系の基準点となる経度 [deg]
    """

    input_file = Path(input_file_name)
    output_directory = Path(output_directory_name)

    # 処理の対象となるCSVファイルの存在確認
    if not input_file.is_file() or input_file.suffix.lower() != ".csv":
        return

    # CSVファイルを読み込む
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(
            f"⚠️ CSVファイル {input_file} "
            f"の読み込みに失敗しました ({e}). "
        )
        return

    # 必要なカラムの存在確認
    required_columns = [
        "latitude",
        "longitude",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        print(
            f"⚠️ CSVファイル {input_file} に "
            f"必要なカラムがありません: {missing_columns}"
        )
        return

    # 緯度・経度を数値型に変換
    latitude = pd.to_numeric(
        df["latitude"],
        errors="coerce",
    )

    longitude = pd.to_numeric(
        df["longitude"],
        errors="coerce",
    )

    # 基準点からの緯度・経度の差
    delta_latitude = (
        latitude - reference_latitude
    )

    delta_longitude = (
        longitude - reference_longitude
    )

    # 基準点の緯度をラジアンへ変換
    reference_latitude_rad = np.radians(
        reference_latitude
    )

    # 1度あたりの距離 [m]
    meters_per_degree_latitude = 111320.0

    meters_per_degree_longitude = (
        111320.0
        * np.cos(reference_latitude_rad)
    )

    # ローカル座標を計算
    #
    # x: 東方向 [m]
    # y: 北方向 [m]
    x = (
        delta_longitude
        * meters_per_degree_longitude
    )

    y = (
        delta_latitude
        * meters_per_degree_latitude
    )

    # latitude・longitudeを削除
    df = df.drop(
        columns=[
            "latitude",
            "longitude",
        ]
    )

    # latitude・longitudeがあった位置に
    # x・yを挿入
    df.insert(
        2,
        "x",
        x,
    )

    df.insert(
        3,
        "y",
        y,
    )

    # 出力先のディレクトリを作成する
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 出力するファイルの名前を設定する
    output_file = (
        output_directory / input_file.name
    )

    # 処理されたCSVファイルを保存する
    try:
        df.to_csv(
            output_file,
            index=False,
        )

        print(
            f"✅ CSVファイル {output_file} "
            f"を保存しました. "
        )

    except Exception as e:
        print(
            f"⚠️ CSVファイルの保存に失敗しました "
            f"({e}). "
        )


def main() -> None:
    """
    コマンドライン引数にて指定されたディレクトリ内の
    全CSVファイルをローカル座標系へ変換する関数
    """

    parser = argparse.ArgumentParser(
        description=(
            "指定されたディレクトリ内の全CSVファイルの "
            "緯度・経度をローカル座標へ変換します. "
        )
    )

    parser.add_argument(
        "input_directory_name",
        nargs="?",
        default="resources/raw_data",
        help=(
            "処理の対象となるCSVファイルが入っている "
            "ディレクトリの名前 "
            "(デフォルト値: `resources/raw_data`)"
        ),
    )

    parser.add_argument(
        "output_directory_name",
        nargs="?",
        default="output/converted",
        help=(
            "処理後のCSVファイルを保存する "
            "ディレクトリの名前 "
            "(デフォルト値: `output/converted`)"
        ),
    )

    parser.add_argument(
        "reference_latitude",
        type=float,
        help="ローカル座標系の基準点となる緯度 [deg]",
    )

    parser.add_argument(
        "reference_longitude",
        type=float,
        help="ローカル座標系の基準点となる経度 [deg]",
    )

    args = parser.parse_args()

    input_directory = Path(
        args.input_directory_name
    )

    # 処理の対象となるディレクトリの存在を確認する
    if not input_directory.is_dir():
        print(
            f"⚠️ 処理の対象となるディレクトリ "
            f"{input_directory} が存在しません. "
        )
        return

    # 処理の対象となるディレクトリ内の
    # 全CSVファイルを取得する
    csv_files = [
        file
        for file in input_directory.iterdir()
        if (
            file.is_file()
            and file.suffix.lower() == ".csv"
        )
    ]

    # CSVファイルの存在を確認する
    if not csv_files:
        print(
            f"⚠️ 処理の対象となるディレクトリ "
            f"{input_directory} 内にCSVファイルがありません. "
        )
        return

    # 全CSVファイルを処理する
    total = len(csv_files)
    digit = len(str(total))

    for current, csv_file in enumerate(
        csv_files,
        start=1,
    ):
        print(
            f"[{current:0{digit}d}/{total}] ",
            end="",
        )

        convert_to_local_coordinates(
            csv_file,
            args.output_directory_name,
            args.reference_latitude,
            args.reference_longitude,
        )


if __name__ == "__main__":
    # 例:
    #
    # python csv_data_converter/convert_to_local_coordinates.py \
    #     resources/raw_data \
    #     output/converted \
    #     35.042733 \
    #     137.146396

    main()