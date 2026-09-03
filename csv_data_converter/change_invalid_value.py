# -*- coding: UTF-8 -*-

import argparse
from pathlib import Path

import pandas as pd


def change_invalidity_to_nan(input_file_name: str, output_directly_name: str, invalid_values: list[tuple[str, float]]) -> None:
    """
    CSVファイルから指定されたカラムの要素が不定値である場合に `NaN` に置換する関数

    :param input_file_name:
        入力されたファイル名
    :param output_directly_name:
        出力先のディレクトリ名
    :param invalid_values:
        置換の対象となるカラム名と不定値の組
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

    # 指定された不定値を `NaN` に置換する
    for column_name, invalid_value in invalid_values:
        # 指定されたカラムの存在を確認する
        if column_name not in df.columns:
            print(f"⚠️ CSVファイル {input_file} にカラム {column_name} が存在しません. ")
            continue
        df.loc[df[column_name] == invalid_value, column_name] = float("nan")

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
    コマンドライン引数にて指定されたディレクトリ内の全CSVファイルから不定値を `NaN` に置換する関数
    """

    parser = argparse.ArgumentParser(
        description="指定されたディレクトリ内の全CSVファイルから不定値を `NaN` に置換します. "
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
        help="処理後のCSVファイルを保存するためのディレクトリの名前 (デフォルト値: `output/changed_nan`)"
    )
    parser.add_argument(
        "invalid_values",
        nargs="+",
        help="置換の対象となるカラム名と不定値の組 (例: `latitude=0 longitude=0`)"
    )
    args = parser.parse_args()

    # 指定された不定値を取得する
    invalid_values = []
    for invalid_value in args.invalid_values:
        try:
            column_name, value = invalid_value.split("=", 1)
            invalid_values.append(
                (column_name, float(value))
            )
        except ValueError:
            print(f"⚠️ 不定値の入力形式が正しくありません. ")
            return

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
        change_invalidity_to_nan(csv_file, args.output_directory_name, invalid_values)


if __name__ == "__main__":
    # `python csv_data_converter/change_invalid_value.py resources/raw_data output/changed_nan latitude=0 longitude=0`
    main()
