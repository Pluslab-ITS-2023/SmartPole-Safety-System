# -*- coding: UTF-8 -*-

import argparse
from pathlib import Path

import pandas as pd


def remove_columns(input_file_name: str, output_directly_name: str, column_names: list[str]) -> None:
    """
    CSVファイルから指定されたカラムを削除して保存する関数

    :param input_file_name:
        入力されたファイル名
    :param output_directly_name:
        出力先のディレクトリ名
    :param column_names:
        削除の対象となるカラム名
    """

    input_file = Path(input_file_name)
    output_directory = Path(output_directly_name)

    # 処理の対象となるCSVファイルの存在確認
    if not input_file.is_file() or input_file.suffix.lower() != ".csv":
        # print(f"⚠️ 処理の対象となるCSVファイル {input_file} が存在しません. ")
        return
    # CSVファイルを読み込む
    try:
        df = pd.read_csv(input_file)
    except Exception as e:
        print(f"⚠️ CSVファイル {input_file} の読み込みに失敗しました ({e}). ")
        return

    # 存在するカラムを抽出する
    existing_columns = [
        column
        for column in column_names
        if column in df.columns
    ]
    # カラムを削除する
    df = df.drop(columns=existing_columns)

    # 出力先のディレクトリを作成する
    output_directory.mkdir(parents=True, exist_ok=True)
    # 出力するファイルの名前を設定する
    output_file = output_directory / input_file.name
    # 処理されたCSVファイルを保存する
    try:
        df.to_csv(output_file, index=False)
        print(f"✅ CSVファイル {output_file} を保存しました. ")
    except Exception as e:
        print(f"⚠️ CSVファイルの保存に失敗しました ({e}). ")


def main() -> None:
    """
    コマンドライン引数にて指定されたディレクトリ内の全CSVファイルから指定されたカラムを削除する関数
    """

    parser = argparse.ArgumentParser(
        description="指定されたディレクトリ内の全CSVファイルから指定されたカラムを削除します. "
    )
    parser.add_argument(
        "input_directory_name",
        nargs="?",
        default="resources/raw_data",
        help="処理の対象となるCSVファイルが入っているディレクトリの名前 (デフォルト値: `resources/raw_data`)"
    )
    parser.add_argument(
        "output_directory_name",
        nargs="?",
        default="output/removed",
        help="処理後のCSVファイルを保存するためのディレクトリの名前 (デフォルト値: `output/removed`)"
    )
    parser.add_argument(
        "column_names",
        nargs="+",
        help="削除の対象となるカラム名 (複数指定可能)"
    )
    args = parser.parse_args()

    input_directory = Path(args.input_directory_name)
    # 処理の対象となるディレクトリの存在を確認する
    if not input_directory.is_dir():
        print(f"⚠️ 処理の対象となるディレクトリ {input_directory} が存在しません. ")
        return
    
    # 処理の対象となるディレクトリ内の全CSVファイルを取得する
    csv_files = [
        file for file in input_directory.iterdir()
        if file.is_file() and file.suffix.lower() == ".csv"
    ]
    # CSVファイルの存在を確認する
    if not csv_files:
        print(f"⚠️ 処理の対象となるディレクトリ {input_directory} 内にCSVファイルがありません. ")
        return
    # 全CSVファイルを処理する
    total = len(csv_files)
    digit = len(str(total))
    for current, csv_file in enumerate(csv_files, start=1):
        print(f"[{current:0{digit}d}/{total}] ", end="")
        remove_columns(csv_file, args.output_directory_name, args.column_names)


if __name__ == "__main__":
    # `python csv_data_converter/remove_columns.py resources/raw_data output/removed vehiclelist acceleration vehicleroleclassification`
    main()
