# -*- coding: UTF-8 -*-

import argparse
from pathlib import Path

import pandas as pd


def remove_columns_from_csv(input_file_name: str, output_directly_name: str, columns: list[str]) -> None:
    """
    CSVファイルから指定されたカラムを削除して保存する関数

    :param input_file_name:
        入力されたファイル名
    :param output_directly_name:
        出力先のディレクトリ名
    :param columns:
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
        for column in columns
        if column in df.columns
    ]
    # カラムを削除する
    df = df.drop(columns=existing_columns)

    # 出力先のディレクトリを作成する
    output_directory.mkdir(parents=True, exist_ok=True)

    # 元のファイル名を使用
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
    # 処理の対象となるディレクトリ
    parser.add_argument(
        "input_directory",
        help="処理の対象となるCSVファイルが入っているディレクトリの名称"
    )
    # 出力先となるディレクトリ
    parser.add_argument(
        "output_directory",
        help="処理後のCSVファイルを保存するためのディレクトリの名称"
    )
    # 削除の対象となるカラム
    parser.add_argument(
        "columns",
        nargs="+",
        help="削除の対象となるカラム名 (複数指定可能)"
    )

    args = parser.parse_args()

    input_directory = Path(args.input_directory)
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
        remove_columns_from_csv(csv_file, args.output_directory, args.columns)


if __name__ == "__main__":
    main()
