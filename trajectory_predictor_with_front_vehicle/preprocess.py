# -*- coding: UTF-8 -*-

from pathlib import Path

import numpy as np
import pandas as pd


INVALID_SPEED = 655.35
INVALID_HEADING = 819.1875
DEFAULT_LANE_WIDTH = 4.0
DEFAULT_MAX_FRONT_DISTANCE = 80.0
DEFAULT_MAX_CROSS_DISTANCE = 40.0
DEFAULT_DIRECTION_SIMILARITY = 0.5

FEATURE_COLUMNS = [
    "x",
    "y",
    "speed",
    "heading_sin",
    "heading_cos",
    "same_lane_front_exists",
    "same_lane_front_longitudinal",
    "same_lane_front_lateral",
    "same_lane_front_speed_delta",
    "opposing_exists",
    "opposing_distance",
    "opposing_lateral",
    "opposing_speed_delta",
    "cross_exists",
    "cross_distance",
    "cross_lateral",
    "cross_speed_delta",
]


def load_converted_csv(csv_path):
    """csv_data_converter後の共通座標CSVを読み込む。"""

    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    required_columns = [
        "vehicleid",
        "time",
        "x",
        "y",
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
            f"{csv_path} に必要なカラムがありません: {missing_columns}"
        )

    df = df[required_columns].copy()
    df["time"] = pd.to_datetime(
        df["time"],
        format="mixed",
        errors="coerce",
    )
    for column in ["x", "y", "speed", "heading"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df.loc[df["speed"] == INVALID_SPEED, "speed"] = np.nan
    df.loc[df["heading"] == INVALID_HEADING, "heading"] = np.nan
    df = df.dropna(subset=["vehicleid", "time", "x", "y"])
    return df.sort_values(["time", "vehicleid"]).reset_index(drop=True)


def _prepare_vehicle(vehicle_df):
    """1台分の重複を整理し、方位をsin/cosへ変換する。"""

    vehicle_df = vehicle_df.sort_values("time").copy()
    vehicle_df = vehicle_df.drop_duplicates("time", keep="first")
    if len(vehicle_df) < 2:
        return None

    heading_rad = np.deg2rad(vehicle_df["heading"])
    vehicle_df["heading_sin"] = np.sin(heading_rad)
    vehicle_df["heading_cos"] = np.cos(heading_rad)

    return vehicle_df.dropna(
        subset=[
            "x",
            "y",
            "speed",
            "heading_sin",
            "heading_cos",
        ]
    ).reset_index(drop=True)


def _add_front_vehicle_features(
    scene_df,
    lane_width=DEFAULT_LANE_WIDTH,
    max_distance=DEFAULT_MAX_FRONT_DISTANCE,
    max_cross_distance=DEFAULT_MAX_CROSS_DISTANCE,
    direction_similarity=DEFAULT_DIRECTION_SIMILARITY,
):
    """同一車線、対向車線、交差方向の車両特徴量を追加する。"""

    result = scene_df.copy()
    context_columns = FEATURE_COLUMNS[5:]
    for column in context_columns:
        result[column] = 0.0

    for _, time_indices in result.groupby("time", sort=False).groups.items():
        frame = result.loc[time_indices]
        positions = frame[["x", "y"]].to_numpy(dtype=np.float64)
        speeds = frame["speed"].to_numpy(dtype=np.float64)
        headings_sin = frame["heading_sin"].to_numpy(dtype=np.float64)
        headings_cos = frame["heading_cos"].to_numpy(dtype=np.float64)

        for row_number, row_index in enumerate(frame.index):
            if not np.isfinite(headings_sin[row_number]) or not np.isfinite(
                headings_cos[row_number]
            ):
                continue

            forward_x = headings_sin[row_number]
            forward_y = headings_cos[row_number]
            relative = positions - positions[row_number]
            longitudinal = (
                relative[:, 0] * forward_x
                + relative[:, 1] * forward_y
            )
            lateral = (
                relative[:, 0] * forward_y
                - relative[:, 1] * forward_x
            )
            distances = np.linalg.norm(relative, axis=1)
            direction_similarity_values = (
                headings_sin * forward_x
                + headings_cos * forward_y
            )

            base_mask = (
                (np.arange(len(frame)) != row_number)
                & np.isfinite(speeds)
            )

            same_lane_mask = (
                base_mask
                & (longitudinal > 0.0)
                & (longitudinal <= max_distance)
                & (np.abs(lateral) <= lane_width)
                & (direction_similarity_values >= direction_similarity)
            )
            _set_nearest_context(
                result,
                row_index,
                candidate_mask=same_lane_mask,
                ranking=longitudinal,
                names=(
                    "same_lane_front_exists",
                    "same_lane_front_longitudinal",
                    "same_lane_front_lateral",
                    "same_lane_front_speed_delta",
                ),
                distance_values=longitudinal,
                lateral=lateral,
                distances=distances,
                speeds=speeds,
                ego_speed=speeds[row_number],
            )

            opposing_mask = (
                base_mask
                & (longitudinal > 0.0)
                & (distances <= max_distance)
                & (np.abs(lateral) <= lane_width * 3.0)
                & (direction_similarity_values <= -direction_similarity)
            )
            _set_nearest_context(
                result,
                row_index,
                candidate_mask=opposing_mask,
                ranking=distances,
                names=(
                    "opposing_exists",
                    "opposing_distance",
                    "opposing_lateral",
                    "opposing_speed_delta",
                ),
                distance_values=distances,
                lateral=lateral,
                distances=distances,
                speeds=speeds,
                ego_speed=speeds[row_number],
            )

            cross_mask = (
                base_mask
                & (longitudinal > 0.0)
                & (distances <= max_cross_distance)
                & (np.abs(direction_similarity_values) < direction_similarity)
            )
            _set_nearest_context(
                result,
                row_index,
                candidate_mask=cross_mask,
                ranking=distances,
                names=(
                    "cross_exists",
                    "cross_distance",
                    "cross_lateral",
                    "cross_speed_delta",
                ),
                distance_values=distances,
                lateral=lateral,
                distances=distances,
                speeds=speeds,
                ego_speed=speeds[row_number],
            )

    return result


def _set_nearest_context(
    result,
    row_index,
    candidate_mask,
    ranking,
    names,
    distance_values,
    lateral,
    distances,
    speeds,
    ego_speed,
):
    if not candidate_mask.any():
        return

    candidate_indices = np.flatnonzero(candidate_mask)
    nearest = candidate_indices[np.argmin(ranking[candidate_indices])]
    exists_name, distance_name, lateral_name, speed_delta_name = names
    result.loc[row_index, exists_name] = 1.0
    result.loc[row_index, distance_name] = distance_values[nearest]
    result.loc[row_index, lateral_name] = lateral[nearest]
    result.loc[row_index, speed_delta_name] = speeds[nearest] - ego_speed


def load_and_preprocess_scene_csv(
    csv_path,
    lane_width=DEFAULT_LANE_WIDTH,
    max_distance=DEFAULT_MAX_FRONT_DISTANCE,
    max_cross_distance=DEFAULT_MAX_CROSS_DISTANCE,
    direction_similarity=DEFAULT_DIRECTION_SIMILARITY,
):
    """共通座標CSVから前方車両特徴量付きの車両軌跡を作る。"""

    df = load_converted_csv(csv_path)
    processed_vehicles = []
    for vehicle_id, vehicle_df in df.groupby("vehicleid", sort=False):
        processed = _prepare_vehicle(vehicle_df)
        if processed is None:
            continue
        processed["vehicleid"] = vehicle_id
        processed_vehicles.append(processed)

    if not processed_vehicles:
        return []

    scene_df = pd.concat(processed_vehicles, ignore_index=True)
    scene_df = _add_front_vehicle_features(
        scene_df,
        lane_width=lane_width,
        max_distance=max_distance,
        max_cross_distance=max_cross_distance,
        direction_similarity=direction_similarity,
    )
    trajectories = []
    for _, vehicle_df in scene_df.groupby("vehicleid", sort=False):
        vehicle_df = vehicle_df.sort_values("time").reset_index(drop=True)
        if vehicle_df[FEATURE_COLUMNS].isna().any().any():
            continue
        trajectories.append(vehicle_df)
    return trajectories