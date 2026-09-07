#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PYTHON="${PYTHON:-python}"

usage() {
    cat <<EOF
Usage:
  $0 INPUT_DIR OUTPUT_DIR REFERENCE_LATITUDE REFERENCE_LONGITUDE [SENSOR_ID]

Example:
  $0 \
    resources/raw_data/大林1001/支援なし \
    output/trajectory_predictor/o1001/ns \
    35.042733 \
    137.146396 \
    13633281

INPUT_DIR must contain CSV files named:
  t_corrected_pos_info_YYYY_MMDD.csv

OUTPUT_DIR will contain the final CSV files with x,y coordinates.
EOF
}

if [[ $# -lt 4 || $# -gt 5 ]]; then
    usage
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
REFERENCE_LATITUDE="$3"
REFERENCE_LONGITUDE="$4"
SENSOR_ID="${5:-13633281}"

if [[ ! -d "$INPUT_DIR" ]]; then
    echo "入力ディレクトリがありません: $INPUT_DIR" >&2
    exit 1
fi

INPUT_DIR="$(realpath "$INPUT_DIR")"
OUTPUT_DIR="$(realpath -m "$OUTPUT_DIR")"
WORK_DIR="${OUTPUT_DIR}.work"

if [[ "$INPUT_DIR" == "$OUTPUT_DIR" || "$INPUT_DIR" == "$WORK_DIR" ]]; then
    echo "入力と出力に同じディレクトリは指定できません。" >&2
    exit 1
fi

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR" "$OUTPUT_DIR"

run_stage() {
    local number="$1"
    local name="$2"
    shift 2
    echo
    echo "[$number/7] $name"
    "$PYTHON" "$@"
}

cleanup() {
    if [[ "${KEEP_INTERMEDIATE:-0}" != "1" ]]; then
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

cd "$PROJECT_DIR"

run_stage "1" "ファイル名変更" \
    "$SCRIPT_DIR/change_file_name.py" \
    "$INPUT_DIR" "$WORK_DIR/01_renamed"

run_stage "2" "sensorid=${SENSOR_ID} の行を抽出" \
    "$SCRIPT_DIR/extract_rows.py" \
    "$WORK_DIR/01_renamed" "$WORK_DIR/02_extracted" \
    sensorid "$SENSOR_ID"

run_stage "3" "不要列を削除" \
    "$SCRIPT_DIR/remove_columns.py" \
    "$WORK_DIR/02_extracted" "$WORK_DIR/03_removed" \
    sensorid vehiclelist acceleration vehicleroleclassification

run_stage "4" "不定値をNaNへ変換" \
    "$SCRIPT_DIR/change_invalid_value.py" \
    "$WORK_DIR/03_removed" "$WORK_DIR/04_invalid_as_nan" \
    latitude=0 longitude=0 speed=655.35 heading=819.1875

run_stage "5" "時刻形式を変換" \
    "$SCRIPT_DIR/change_time_format.py" \
    "$WORK_DIR/04_invalid_as_nan" "$WORK_DIR/05_time_formatted"

run_stage "6" "0.100秒間隔へリサンプリング" \
    "$SCRIPT_DIR/resample.py" \
    "$WORK_DIR/05_time_formatted" "$WORK_DIR/06_resampled_100ms"

run_stage "7" "交差点中心基準のx,yへ変換" \
    "$SCRIPT_DIR/change_coordinate.py" \
    "$WORK_DIR/06_resampled_100ms" "$OUTPUT_DIR" \
    "$REFERENCE_LATITUDE" "$REFERENCE_LONGITUDE"

echo
echo "前処理が完了しました。"
echo "Transformer用データ: $OUTPUT_DIR"
if [[ "${KEEP_INTERMEDIATE:-0}" == "1" ]]; then
    echo "中間データ: $WORK_DIR"
fi
