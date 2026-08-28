# -*- coding: UTF-8 -*-

import argparse
import re
import shutil
from pathlib import Path


def rename_file(input_file_name: str, output_directly_name: str) -> None:
    """
    `t_corrected_pos_info_yyyy_mmdd.csv` 形式のCSVファイルの名前を `yyyymmdd.csv` 形式に変更する関数

    :param input_file_name:
        入力されたファイル名
    :param output_directly_name:
        出力先のディレクトリ名
    """

    input_file = Path(input_file_name)
    output_directory = Path(output_directly_name)

    # 処理の対象となるCSVファイルの存在確認
    if not input_file.is_file() or input_file.suffix.lower() != ".csv":
        # print(f"⚠️ 処理の対象となるCSVファイルが存在しません. ")
        return
    # ファイル名の形式（`t_corrected_pos_info_yyyy_mmdd.csv`）を確認する
    match = re.fullmatch(
        r"t_corrected_pos_info_(\d{4})_(\d{4})\.csv",
        input_file.name
    )
    if match is None:
        # print(f"⚠️ 処理の対象となるファイル名の形式ではありません. ")
        return

    # 出力先のディレクトリを作成する
    output_directory.mkdir(parents=True, exist_ok=True)
    # ファイル名を変更する
    output_file_name = f"{match.group(1)}{match.group(2)}.csv"
    output_file = output_directory / output_file_name

    # CSVファイルを保存する
    try:
        shutil.copy2(input_file, output_file)
        print(f"✅ CSVファイル {output_file} を保存しました. ")
    except Exception as e:
        print(f"⚠️ CSVファイルの保存に失敗しました ({e}). ")


def main() -> None:
    """
    コマンドライン引数にて指定されたディレクトリ内の全CSVファイルの名前を変更する関数
    """

    parser = argparse.ArgumentParser(
        description="指定されたディレクトリ内の全CSVファイルの名前を変更します. "
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
        default="output/renamed",
        help="処理後のCSVファイルを保存するためのディレクトリの名前 (デフォルト値: `output/renamed`)"
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
    for csv_file in csv_files:
        rename_file(str(csv_file), args.output_directory_name)


if __name__ == "__main__":
    main()
