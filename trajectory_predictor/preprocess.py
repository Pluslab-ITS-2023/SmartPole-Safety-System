# -*- coding: UTF-8 -*-

from pathlib import Path

import numpy as np
import pandas as pd


# =========================================================
# 定数
# =========================================================

INVALID_SPEED = 655.35
INVALID_HEADING = 819.1875

SAMPLE_INTERVAL = "100ms"


# =========================================================
# CSV読み込み
# =========================================================

def load_csv(csv_path):
    """
    CSVファイルを読み込む。

    timeは複数の日時フォーマットが混在している可能性があるため、
    format="mixed" を使用する。
    """

    df = pd.read_csv(csv_path)

    required_columns = [
        "vehicleid",
        "time",
        "latitude",
        "longitude",
        "speed",
        "heading",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{csv_path} に必要なカラムがありません: "
            f"{missing_columns}"
        )

    # timeをdatetimeへ変換
    df["time"] = pd.to_datetime(
        df["time"],
        format="mixed",
        errors="coerce"
    )

    # 変換できなかった日時を確認
    invalid_time = df["time"].isna()

    if invalid_time.any():

        invalid_count = invalid_time.sum()

        print(
            f"[Warning] {csv_path.name}: "
            f"timeを変換できない行が "
            f"{invalid_count}件あります。"
        )

        df = df.loc[
            ~invalid_time
        ].copy()

    # vehicleid → time順にソート
    df = df.sort_values(
        ["vehicleid", "time"]
    )

    return df


# =========================================================
# 不定値処理
# =========================================================

def replace_invalid_values(df):
    """
    不定値をNaNに置換する。

    speed:
        655.35 → NaN

    heading:
        819.1875 → NaN

    latitude / longitude:
        0 → NaN
    """

    df = df.copy()

    df["latitude"] = df["latitude"].replace(
        0,
        np.nan
    )

    df["longitude"] = df["longitude"].replace(
        0,
        np.nan
    )

    df["speed"] = df["speed"].replace(
        INVALID_SPEED,
        np.nan
    )

    df["heading"] = df["heading"].replace(
        INVALID_HEADING,
        np.nan
    )

    return df


# =========================================================
# headingをsin/cosへ変換
# =========================================================

def convert_heading(df):
    """
    headingをsin/cos表現に変換する。

    角度の0°/360°境界問題を避けるため、
    headingそのものではなくsin/cosを使用する。
    """

    df = df.copy()

    heading_rad = np.radians(
        df["heading"]
    )

    df["heading_sin"] = np.sin(
        heading_rad
    )

    df["heading_cos"] = np.cos(
        heading_rad
    )

    return df


# =========================================================
# 線形補間
# =========================================================

def interpolate_values(df):
    """
    欠損値を時間方向に補間する。

    latitude / longitude / speed / heading_sin / heading_cos
    を補間する。
    """

    df = df.copy()

    columns = [
        "latitude",
        "longitude",
        "speed",
        "heading_sin",
        "heading_cos",
    ]

    df = df.set_index("time")

    df[columns] = df[columns].interpolate(
        method="time",
        limit_direction="both"
    )

    df = df.reset_index()

    return df


# =========================================================
# 0.1秒間隔へのリサンプリング
# =========================================================

def resample_vehicle(df):
    """
    車両1台分のデータを0.1秒間隔にリサンプリングする。
    """

    df = df.copy()

    df = df.sort_values("time")

    df = df.drop_duplicates(
        subset="time"
    )

    if len(df) < 2:
        return None

    df = df.set_index("time")

    columns = [
        "latitude",
        "longitude",
        "speed",
        "heading_sin",
        "heading_cos",
    ]

    # 0.1秒間隔にリサンプリング
    df = df[columns].resample(
        SAMPLE_INTERVAL
    ).mean()

    # 時間方向に補間
    df[columns] = df[columns].interpolate(
        method="time",
        limit_direction="both"
    )

    df = df.reset_index()

    return df


# =========================================================
# 緯度経度 → メートル座標
# =========================================================

def latitude_longitude_to_xy(df, origin=None):
    """
    緯度・経度を局所的なメートル座標に変換する。

    x:
        東方向

    y:
        北方向
    """

    df = df.copy()

    if origin is None:
        lat0 = df["latitude"].iloc[0]
        lon0 = df["longitude"].iloc[0]
    else:
        lat0, lon0 = origin

    x = (
        (df["longitude"] - lon0)
        * 111000.0
        * np.cos(np.radians(lat0))
    )

    y = (
        (df["latitude"] - lat0)
        * 111000.0
    )

    df["x"] = x
    df["y"] = y

    return df


# =========================================================
# 車両データ全体の前処理
# =========================================================

def preprocess_vehicle(vehicle_df, origin=None):
    """
    1台の車両データをTransformer用データへ変換する。
    """

    # 不定値処理
    vehicle_df = replace_invalid_values(
        vehicle_df
    )

    # heading → sin/cos
    vehicle_df = convert_heading(
        vehicle_df
    )

    # 補間
    vehicle_df = interpolate_values(
        vehicle_df
    )

    # 0.1秒間隔
    vehicle_df = resample_vehicle(
        vehicle_df
    )

    if vehicle_df is None:
        return None

    # 緯度経度 → x,y
    vehicle_df = latitude_longitude_to_xy(
        vehicle_df,
        origin=origin,
    )

    # 必要なデータが残っているか確認
    required_columns = [
        "x",
        "y",
        "speed",
        "heading_sin",
        "heading_cos",
    ]

    if vehicle_df[required_columns].isna().any().any():
        return None

    return vehicle_df


# =========================================================
# CSVから車両軌跡を取得
# =========================================================

def load_and_preprocess_csv(csv_path):
    """
    1日分のCSVから車両ごとの軌跡を取得する。

    Returns
    -------
    list[pandas.DataFrame]
        車両ごとの前処理済みDataFrame
    """

    df = load_csv(csv_path)

    df = df.sort_values(
        ["vehicleid", "time"]
    )

    vehicle_trajectories = []

    for vehicle_id, vehicle_df in df.groupby(
        "vehicleid"
    ):

        processed = preprocess_vehicle(
            vehicle_df
        )

        if processed is None:
            continue

        processed["vehicleid"] = vehicle_id

        vehicle_trajectories.append(
            processed
        )

    return vehicle_trajectories


def load_and_preprocess_scene_csv(csv_path):
    """1日分の車両軌跡を共通のメートル座標系で前処理する。"""

    df = replace_invalid_values(load_csv(csv_path))
    valid_coordinates = df[["latitude", "longitude"]].dropna()

    if valid_coordinates.empty:
        return []

    origin = (
        valid_coordinates["latitude"].iloc[0],
        valid_coordinates["longitude"].iloc[0],
    )
    trajectories = []

    for vehicle_id, vehicle_df in df.groupby("vehicleid"):
        processed = preprocess_vehicle(
            vehicle_df,
            origin=origin,
        )

        if processed is None:
            continue

        processed["vehicleid"] = vehicle_id
        trajectories.append(processed)

    return trajectories

