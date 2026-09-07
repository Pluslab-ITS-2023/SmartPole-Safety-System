# -*- coding: UTF-8 -*-

import argparse
import shutil
from pathlib import Path

from change_coordinate import convert_to_local_coordinates
from change_file_name import rename_file
from change_invalid_value import change_invalidity_to_nan
from change_time_format import change_datetime_to_time
from extract_rows import extract_rows
from remove_columns import remove_columns
from resample import resample_trajectory


DEFAULT_REMOVE_COLUMNS = [
    "sensorid",
    "vehiclelist",
    "acceleration",
    "vehicleroleclassification",
]
DEFAULT_INVALID_VALUES = [
    ("latitude", 0.0),
    ("longitude", 0.0),
    ("speed", 655.35),
    ("heading", 819.1875),
]


def _csv_files(directory):
    return sorted(
        path
        for path in Path(directory).iterdir()
        if path.is_file() and path.suffix.lower() == ".csv"
    )


def _run_stage(stage_name, input_directory, output_directory, function, *args):
    input_directory = Path(input_directory)
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    input_files = _csv_files(input_directory)
    if not input_files:
        raise RuntimeError(
            f"{stage_name} の入力CSVがありません: {input_directory}"
        )

    print(f"\n[{stage_name}] {len(input_files)} files")
    for input_file in input_files:
        function(input_file, output_directory, *args)

    output_files = _csv_files(output_directory)
    if not output_files:
        raise RuntimeError(
            f"{stage_name} の出力CSVがありません: {output_directory}"
        )


def prepare_data(
    input_directory,
    output_directory,
    reference_latitude,
    reference_longitude,
    sensorid="13633281",
    keep_intermediate=False,
):
    """元CSV群をTransformer用の共通座標CSVへ一括変換する。"""

    input_directory = Path(input_directory)
    output_directory = Path(output_directory)
    if not input_directory.is_dir():
        raise FileNotFoundError(f"入力ディレクトリがありません: {input_directory}")

    work_directory = output_directory.parent / f".{output_directory.name}_work"
    if work_directory.exists():
        shutil.rmtree(work_directory)
    work_directory.mkdir(parents=True)
    output_directory.mkdir(parents=True, exist_ok=True)

    try:
        renamed = work_directory / "01_renamed"
        for input_file in _csv_files(input_directory):
            rename_file(input_file, renamed)
        if not _csv_files(renamed):
            raise RuntimeError(
                "ファイル名が t_corrected_pos_info_YYYY_MMDD.csv 形式ではありません。"
            )

        extracted = work_directory / "02_extracted"
        _run_stage(
            "sensorid抽出",
            renamed,
            extracted,
            extract_rows,
            "sensorid",
            str(sensorid),
        )

        removed = work_directory / "03_removed"
        _run_stage(
            "不要列削除",
            extracted,
            removed,
            remove_columns,
            DEFAULT_REMOVE_COLUMNS,
        )

        invalid_as_nan = work_directory / "04_invalid_as_nan"
        _run_stage(
            "不定値をNaNへ変換",
            removed,
            invalid_as_nan,
            change_invalidity_to_nan,
            DEFAULT_INVALID_VALUES,
        )

        formatted_time = work_directory / "05_time_formatted"
        _run_stage(
            "時刻形式変換",
            invalid_as_nan,
            formatted_time,
            change_datetime_to_time,
        )

        resampled = work_directory / "06_resampled_100ms"
        _run_stage(
            "0.100秒リサンプリング",
            formatted_time,
            resampled,
            resample_trajectory,
        )

        _run_stage(
            "交差点中心基準のx,y変換",
            resampled,
            output_directory,
            convert_to_local_coordinates,
            float(reference_latitude),
            float(reference_longitude),
        )
    finally:
        if not keep_intermediate and work_directory.exists():
            shutil.rmtree(work_directory)

    print(f"\n完了: Transformer用データを {output_directory} に保存しました。")


def main():
    parser = argparse.ArgumentParser(
        description="CSVコンバータを一括実行してTransformer用データを作成します。"
    )
    parser.add_argument("input_directory")
    parser.add_argument("output_directory")
    parser.add_argument("reference_latitude", type=float)
    parser.add_argument("reference_longitude", type=float)
    parser.add_argument("--sensorid", default="13633281")
    parser.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="中間CSVをoutput_directoryの隣に残します。",
    )
    args = parser.parse_args()
    prepare_data(
        args.input_directory,
        args.output_directory,
        args.reference_latitude,
        args.reference_longitude,
        sensorid=args.sensorid,
        keep_intermediate=args.keep_intermediate,
    )


if __name__ == "__main__":
    main()
