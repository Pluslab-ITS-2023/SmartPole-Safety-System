# # # -*- coding: UTF-8 -*-

# # import argparse
# # from pathlib import Path

# # import numpy as np
# # import pandas as pd


# # RESAMPLE_INTERVAL = "100ms"


# # def aggregate_duplicate_times(df: pd.DataFrame) -> pd.DataFrame:
# #     """
# #     同一交通参加者における同一時刻に複数の観測データが存在する場合に1つのデータへ集約する関数

# #     :param df:
# #         入力されたDataFrame
# #     :return:
# #         重複時刻を集約したDataFrame
# #     """

# #     # 進行方位を度数法から弧度法へ変換する
# #     heading_rad = np.deg2rad(df["heading"])
# #     df["heading_sin"] = np.sin(heading_rad)
# #     df["heading_cos"] = np.cos(heading_rad)

# #     # vehicleidとtimeごとにデータを集約する
# #     result = (
# #         df.groupby(["vehicleid", "time"], as_index=False).agg({
# #             "latitude": "mean",
# #             "longitude": "mean",
# #             "speed": "mean",
# #             "heading_sin": "mean",
# #             "heading_cos": "mean",
# #             "vehiclesizeclassification": "first",
# #         })
# #     )

# #     # 進行方位を弧度法から度数法へ変換する
# #     result["heading"] = (
# #         np.rad2deg(
# #             np.arctan2(result["heading_sin"], result["heading_cos"])
# #         ) % 360
# #     )
# #     # 進行方位における補間用のカラムを削除する
# #     result = result.drop(
# #         columns=["heading_sin", "heading_cos"]
# #     )

# #     return result


# # def resample_trajectory(input_file_name: str, output_directory_name: str) -> None:
# #     """
# #     CSVファイルのデータを0.1秒間隔にリサンプリングする関数

# #     :param input_file_name:
# #         入力されたファイル名
# #     :param output_directory_name:
# #         出力先のディレクトリ名
# #     """

# #     input_file = Path(input_file_name)
# #     output_directory = Path(output_directory_name)

# #     # 処理の対象となるCSVファイルの存在確認
# #     if not input_file.is_file() or input_file.suffix.lower() != ".csv":
# #         return
# #     # CSVファイルを読み込む
# #     try:
# #         df = pd.read_csv(input_file)
# #     except Exception as e:
# #         print(f"⚠️ CSVファイル {input_file} の読み込みに失敗しました ({e}). ")
# #         return

# #     # 必要なカラムの存在を確認する
# #     required_columns = [
# #         "vehicleid",
# #         "time",
# #         "latitude",
# #         "longitude",
# #         "speed",
# #         "heading",
# #         "vehiclesizeclassification",
# #     ]
# #     missing_columns = [
# #         column
# #         for column in required_columns
# #         if column not in df.columns
# #     ]
# #     if missing_columns:
# #         print(f"⚠️ CSVファイル {input_file} に必要なカラム {missing_columns} が存在しません. ")
# #         return

# #     # `time` をdatetime型に変換する
# #     try:
# #         df["time"] = pd.to_datetime(df["time"], format="mixed")
# #     except Exception as e:
# #         print(f"⚠️ CSVファイル {input_file} の時間変換に失敗しました ({e}). ")
# #         return

# #     # 完全に一致する重複レコードを削除する
# #     df = df.drop_duplicates()
# #     # 同一車両における同一時刻の重複を確認する
# #     duplicates = df[
# #         df.duplicated(["vehicleid", "time"], keep=False)
# #     ]
# #     if not duplicates.empty:
# #         print(f"⚠️ CSVファイル {input_file} に `vehicleid` 及び `time` が重複しているデータが {len(duplicates)} 件見つかりました. ")
# #         # 同一車両・同一時刻の異なるデータを集約する
# #         df = aggregate_duplicate_times(df)

# #     # `vehicleid` と `time` の順番に並べる
# #     df = df.sort_values(["vehicleid", "time"])

# #     resampled_data = []
# #     # 車両ごとにリサンプリングする
# #     for vehicle_id, vehicle_df in df.groupby("vehicleid"):
# #         vehicle_df = vehicle_df.copy()
# #         vehicle_df = vehicle_df.set_index("time")
# #         vehicle_df = vehicle_df.drop(columns=["vehicleid"])
# #         vehicle_df = vehicle_df[~vehicle_df.index.duplicated(keep="first")]

# #         # 元データの時間範囲を取得
# #         start_time = vehicle_df.index.min()
# #         end_time = vehicle_df.index.max()

# #         # 0.1秒間隔の時刻を作成
# #         new_time_index = pd.date_range(
# #             start=start_time.ceil(RESAMPLE_INTERVAL),
# #             end=end_time.floor(RESAMPLE_INTERVAL),
# #             freq=RESAMPLE_INTERVAL
# #         )
# #         # 0.1秒間隔の時刻が存在しない場合
# #         if len(new_time_index) == 0:
# #             continue
# #         # 元データの時刻と、補間したい時刻を結合
# #         combined_index = vehicle_df.index.union(
# #             new_time_index
# #         ).sort_values()
# #         vehicle_df = vehicle_df.reindex(
# #             combined_index
# #         )

# #         # 緯度・経度・速さを線形補間する
# #         interpolation_columns = [
# #             "latitude",
# #             "longitude",
# #             "speed"
# #         ]
# #         vehicle_df[interpolation_columns] = (vehicle_df[interpolation_columns].interpolate(method="linear"))

# #         # 進行方位を線形補間する
# #         heading_rad = np.deg2rad(vehicle_df["heading"])
# #         vehicle_df["heading_sin"] = np.sin(heading_rad)
# #         vehicle_df["heading_cos"] = np.cos(heading_rad)
# #         vehicle_df["heading_sin"] = (vehicle_df["heading_sin"].interpolate(method="linear"))
# #         vehicle_df["heading_cos"] = (vehicle_df["heading_cos"].interpolate(method="linear"))
# #         vehicle_df["heading"] = (
# #             np.rad2deg(
# #                 np.arctan2(vehicle_df["heading_sin"], vehicle_df["heading_cos"])
# #             ) % 360
# #         )
# #         vehicle_df = vehicle_df.drop(columns=["heading_sin", "heading_cos"])

# #         # 車両種別を前方補完する
# #         vehicle_df["vehiclesizeclassification"] = vehicle_df["vehiclesizeclassification"].ffill().bfill()
# #         vehicle_df["vehiclesizeclassification"] = (pd.to_numeric(
# #             vehicle_df["vehiclesizeclassification"], errors="coerce"
# #         ).round().astype("Int64"))

# #         vehicle_df["vehicleid"] = vehicle_id
# #         vehicle_df = vehicle_df.loc[new_time_index]

# #         resampled_data.append(vehicle_df.reset_index())

# #     # 車両データを結合する
# #     if not resampled_data:
# #         print(f"⚠️ CSVファイル {input_file} にリサンプリング処理が可能な車両データがありません. ")
# #         return

# #     result = pd.concat(resampled_data, ignore_index=True)
# #     result = result[
# #         [
# #             "vehicleid",
# #             "time",
# #             "latitude",
# #             "longitude",
# #             "speed",
# #             "heading",
# #             "vehiclesizeclassification",
# #         ]
# #     ]
# #     result["time"] = (result["time"].dt.strftime("%H:%M:%S.%f").str[:-3])

# #     # 出力先のディレクトリを作成する
# #     output_directory.mkdir(parents=True, exist_ok=True)
# #     # 出力するファイルの名前を設定する
# #     output_file = output_directory / input_file.name
# #     # CSVファイルを保存する
# #     try:
# #         result.to_csv(output_file, index=False)
# #         print(f"✅ CSVファイル {output_file} を保存しました. ")
# #     except Exception as e:
# #         print(f"⚠️ CSVファイルの保存に失敗しました ({e}). ")


# # def main() -> None:
# #     """
# #     コマンドライン引数にて指定されたディレクトリ内の全CSVファイルを0.1秒間隔にリサンプリングする関数
# #     """

# #     parser = argparse.ArgumentParser(
# #         description=("指定されたディレクトリ内の全CSVファイルを0.1秒間隔にリサンプリングします. ")
# #     )
# #     parser.add_argument(
# #         "input_directory_name",
# #         nargs="?",
# #         default="resources/raw_data",
# #         help=("処理の対象となるCSVファイルが入っているディレクトリの名前 (デフォルト値: `resources/raw_data`)")
# #     )
# #     parser.add_argument(
# #         "output_directory_name",
# #         nargs="?",
# #         default="output/resampled",
# #         help=("処理後のCSVファイルを保存するディレクトリの名前 (デフォルト値: `output/resampled`)")
# #     )
# #     args = parser.parse_args()

# #     input_directory = Path(args.input_directory_name)
# #     # 処理の対象となるディレクトリの存在を確認する
# #     if not input_directory.is_dir():
# #         print(f"⚠️ 処理の対象となるディレクトリ {input_directory} が存在しません. ")
# #         return
# #     # CSVファイルを取得する
# #     csv_files = [
# #         file for file in input_directory.iterdir()
# #         if file.is_file() and file.suffix.lower() == ".csv"
# #     ]
# #     # CSVファイルの存在を確認する
# #     if not csv_files:
# #         print(f"⚠️ 処理の対象となるディレクトリ {input_directory} 内にCSVファイルがありません. ")
# #         return

# #     # 全CSVファイルを処理する
# #     total = len(csv_files)
# #     digit = len(str(total))
# #     for current, csv_file in enumerate(csv_files, start=1):
# #         print(f"[{current:0{digit}d}/{total}] ", end="")
# #         resample_trajectory(str(csv_file), args.output_directory_name)


# # if __name__ == "__main__":
# #     # `python csv_data_converter/resample.py resources/raw_data output/resampled`
# #     main()



# # -*- coding: UTF-8 -*-

# import argparse
# from pathlib import Path

# import numpy as np
# import pandas as pd


# # リサンプリング間隔
# RESAMPLE_INTERVAL = "100ms"


# def aggregate_duplicate_times(df: pd.DataFrame) -> pd.DataFrame:
#     """
#     同一車両における同一時刻の複数観測データを1つに集約する。

#     緯度・経度・速度は平均値、
#     headingは角度を考慮して平均し、
#     車両種別は最初の値を使用する。
#     """

#     # headingをsin/cosへ変換
#     heading_rad = np.deg2rad(df["heading"])

#     df = df.copy()
#     df["heading_sin"] = np.sin(heading_rad)
#     df["heading_cos"] = np.cos(heading_rad)

#     # vehicleid + timeごとに集約
#     result = (
#         df.groupby(
#             ["vehicleid", "time"],
#             as_index=False
#         )
#         .agg({
#             "latitude": "mean",
#             "longitude": "mean",
#             "speed": "mean",
#             "heading_sin": "mean",
#             "heading_cos": "mean",
#             "vehiclesizeclassification": "first",
#         })
#     )

#     # sin/cosからheadingを復元
#     result["heading"] = (
#         np.rad2deg(
#             np.arctan2(
#                 result["heading_sin"],
#                 result["heading_cos"]
#             )
#         ) % 360
#     )

#     # 補助カラムを削除
#     result = result.drop(
#         columns=["heading_sin", "heading_cos"]
#     )

#     return result


# def interpolate_heading(vehicle_df: pd.DataFrame) -> pd.DataFrame:
#     """
#     headingを角度の循環性を考慮して線形補間する。

#     例:
#         359° → 1°
#     を
#         359° → 180° → 1°
#     とせず、

#         359° → 0° → 1°
#     として補間する。
#     """

#     # headingをラジアンへ変換
#     heading_rad = np.deg2rad(vehicle_df["heading"])

#     # sin/cosへ変換
#     vehicle_df["heading_sin"] = np.sin(heading_rad)
#     vehicle_df["heading_cos"] = np.cos(heading_rad)

#     # 線形補間
#     vehicle_df["heading_sin"] = (
#         vehicle_df["heading_sin"]
#         .interpolate(method="linear")
#     )

#     vehicle_df["heading_cos"] = (
#         vehicle_df["heading_cos"]
#         .interpolate(method="linear")
#     )

#     # sin/cosから角度へ戻す
#     vehicle_df["heading"] = (
#         np.rad2deg(
#             np.arctan2(
#                 vehicle_df["heading_sin"],
#                 vehicle_df["heading_cos"]
#             )
#         ) % 360
#     )

#     # 補助カラムを削除
#     vehicle_df = vehicle_df.drop(
#         columns=["heading_sin", "heading_cos"]
#     )

#     return vehicle_df


# def resample_trajectory(
#     input_file_name: str,
#     output_directory_name: str
# ) -> None:
#     """
#     CSVファイルのデータを0.1秒間隔にリサンプリングする。

#     lat / lon / speed / headingを補間し、
#     vehiclesizeclassificationは前後補完する。
#     """

#     input_file = Path(input_file_name)
#     output_directory = Path(output_directory_name)

#     # CSVファイルの存在確認
#     if not input_file.is_file() or input_file.suffix.lower() != ".csv":
#         return

#     # CSV読み込み
#     try:
#         df = pd.read_csv(input_file)
#     except Exception as e:
#         print(
#             f"⚠️ CSVファイル {input_file} の読み込みに失敗しました ({e}). "
#         )
#         return

#     # 必要なカラム
#     required_columns = [
#         "vehicleid",
#         "time",
#         "latitude",
#         "longitude",
#         "speed",
#         "heading",
#         "vehiclesizeclassification",
#     ]

#     # カラム存在確認
#     missing_columns = [
#         column
#         for column in required_columns
#         if column not in df.columns
#     ]

#     if missing_columns:
#         print(
#             f"⚠️ CSVファイル {input_file} に "
#             f"必要なカラム {missing_columns} が存在しません. "
#         )
#         return

#     # timeをdatetime型へ変換
#     try:
#         df["time"] = pd.to_datetime(
#             df["time"],
#             format="mixed"
#         )
#     except Exception as e:
#         print(
#             f"⚠️ CSVファイル {input_file} の "
#             f"時間変換に失敗しました ({e}). "
#         )
#         return

#     # ---------------------------------------------------------
#     # 1. 完全一致する重複レコードを削除
#     # ---------------------------------------------------------

#     df = df.drop_duplicates()

#     # ---------------------------------------------------------
#     # 2. vehicleid + time の重複を確認
#     # ---------------------------------------------------------

#     duplicates = df[
#         df.duplicated(
#             ["vehicleid", "time"],
#             keep=False
#         )
#     ]

#     if not duplicates.empty:
#         print(
#             f"⚠️ CSVファイル {input_file} に "
#             f"`vehicleid` 及び `time` が重複しているデータが "
#             f"{len(duplicates)} 件見つかりました. "
#         )

#         # 同一時刻のデータを集約
#         df = aggregate_duplicate_times(df)

#     # ---------------------------------------------------------
#     # 3. vehicleid + timeで並べ替え
#     # ---------------------------------------------------------

#     df = df.sort_values(
#         ["vehicleid", "time"]
#     )

#     resampled_data = []

#     # ---------------------------------------------------------
#     # 4. 車両ごとに処理
#     # ---------------------------------------------------------

#     for vehicle_id, vehicle_df in df.groupby(
#         "vehicleid"
#     ):

#         vehicle_df = vehicle_df.copy()

#         # 時刻順に並べる
#         vehicle_df = vehicle_df.sort_values("time")

#         # 念のため同一時刻を削除
#         vehicle_df = vehicle_df.drop_duplicates(
#             subset=["time"],
#             keep="first"
#         )

#         # -----------------------------------------------------
#         # 5. timeをインデックスにする
#         # -----------------------------------------------------

#         vehicle_df = vehicle_df.set_index("time")

#         # vehicleidは後で設定するため削除
#         vehicle_df = vehicle_df.drop(
#             columns=["vehicleid"]
#         )

#         # -----------------------------------------------------
#         # 6. 元データの時間範囲
#         # -----------------------------------------------------

#         start_time = vehicle_df.index.min()
#         end_time = vehicle_df.index.max()

#         # -----------------------------------------------------
#         # 7. 0.1秒間隔の時刻を作る
#         # -----------------------------------------------------

#         new_time_index = pd.date_range(
#             start=start_time.ceil(RESAMPLE_INTERVAL),
#             end=end_time.floor(RESAMPLE_INTERVAL),
#             freq=RESAMPLE_INTERVAL
#         )

#         # 0.1秒刻みの時刻が存在しない場合
#         if len(new_time_index) == 0:
#             continue

#         # -----------------------------------------------------
#         # 8. 元データ + 0.1秒刻みの時刻を統合
#         # -----------------------------------------------------

#         combined_index = (
#             vehicle_df.index
#             .union(new_time_index)
#             .sort_values()
#         )

#         vehicle_df = vehicle_df.reindex(
#             combined_index
#         )

#         # -----------------------------------------------------
#         # 9. lat / lon / speedを線形補間
#         # -----------------------------------------------------

#         interpolation_columns = [
#             "latitude",
#             "longitude",
#             "speed"
#         ]

#         vehicle_df[interpolation_columns] = (
#             vehicle_df[interpolation_columns]
#             .interpolate(method="linear")
#         )

#         # -----------------------------------------------------
#         # 10. headingを補間
#         # -----------------------------------------------------

#         vehicle_df = interpolate_heading(
#             vehicle_df
#         )

#         # -----------------------------------------------------
#         # 11. 車両種別を補完
#         # -----------------------------------------------------

#         vehicle_df["vehiclesizeclassification"] = (
#             vehicle_df["vehiclesizeclassification"]
#             .ffill()
#             .bfill()
#         )

#         # int型へ変換
#         vehicle_df["vehiclesizeclassification"] = (
#             pd.to_numeric(
#                 vehicle_df[
#                     "vehiclesizeclassification"
#                 ],
#                 errors="coerce"
#             )
#             .round()
#             .astype("Int64")
#         )

#         # -----------------------------------------------------
#         # 12. 0.1秒刻みの時刻だけを残す
#         # -----------------------------------------------------

#         vehicle_df = vehicle_df.loc[
#             new_time_index
#         ].copy()

#         # -----------------------------------------------------
#         # 13. vehicleidを設定
#         # -----------------------------------------------------

#         vehicle_df["vehicleid"] = vehicle_id

#         # -----------------------------------------------------
#         # 14. timeを通常の列へ戻す
#         # -----------------------------------------------------

#         vehicle_df = vehicle_df.reset_index()

#         # reset_index()後の時刻列名を明示
#         vehicle_df = vehicle_df.rename(
#             columns={"index": "time"}
#         )

#         resampled_data.append(
#             vehicle_df
#         )

#     # ---------------------------------------------------------
#     # 15. 車両データを結合
#     # ---------------------------------------------------------

#     if not resampled_data:
#         print(
#             f"⚠️ CSVファイル {input_file} に "
#             f"リサンプリング処理が可能な車両データがありません. "
#         )
#         return

#     result = pd.concat(
#         resampled_data,
#         ignore_index=True
#     )

#     # ---------------------------------------------------------
#     # 16. カラム順を統一
#     # ---------------------------------------------------------

#     result = result[
#         [
#             "vehicleid",
#             "time",
#             "latitude",
#             "longitude",
#             "speed",
#             "heading",
#             "vehiclesizeclassification",
#         ]
#     ]

#     # ---------------------------------------------------------
#     # 17. timeをHH:MM:SS.sss形式へ戻す
#     # ---------------------------------------------------------

#     result["time"] = (
#         result["time"]
#         .dt.strftime("%H:%M:%S.%f")
#         .str[:-3]
#     )

#     # ---------------------------------------------------------
#     # 18. 出力ディレクトリ作成
#     # ---------------------------------------------------------

#     output_directory.mkdir(
#         parents=True,
#         exist_ok=True
#     )

#     # 出力ファイル
#     output_file = (
#         output_directory /
#         input_file.name
#     )

#     # ---------------------------------------------------------
#     # 19. CSV保存
#     # ---------------------------------------------------------

#     try:
#         result.to_csv(
#             output_file,
#             index=False
#         )

#         print(
#             f"✅ CSVファイル {output_file} を保存しました. "
#         )

#     except Exception as e:
#         print(
#             f"⚠️ CSVファイルの保存に失敗しました ({e}). "
#         )


# def main() -> None:
#     """
#     コマンドライン引数で指定されたディレクトリ内の
#     全CSVファイルを0.1秒間隔にリサンプリングする。
#     """

#     parser = argparse.ArgumentParser(
#         description=(
#             "指定されたディレクトリ内の全CSVファイルを"
#             "0.1秒間隔にリサンプリングします. "
#         )
#     )

#     parser.add_argument(
#         "input_directory_name",
#         nargs="?",
#         default="resources/raw_data",
#         help=(
#             "処理対象のCSVファイルが入っている"
#             "ディレクトリ名"
#         )
#     )

#     parser.add_argument(
#         "output_directory_name",
#         nargs="?",
#         default="output/resampled",
#         help=(
#             "処理後のCSVファイルを保存する"
#             "ディレクトリ名"
#         )
#     )

#     args = parser.parse_args()

#     input_directory = Path(
#         args.input_directory_name
#     )

#     # 入力ディレクトリ確認
#     if not input_directory.is_dir():
#         print(
#             f"⚠️ 処理の対象となるディレクトリ "
#             f"{input_directory} が存在しません. "
#         )
#         return

#     # CSV取得
#     csv_files = [
#         file
#         for file in input_directory.iterdir()
#         if file.is_file()
#         and file.suffix.lower() == ".csv"
#     ]

#     # CSV存在確認
#     if not csv_files:
#         print(
#             f"⚠️ 処理の対象となるディレクトリ "
#             f"{input_directory} 内にCSVファイルがありません. "
#         )
#         return

#     # ---------------------------------------------------------
#     # 全CSVファイルを処理
#     # ---------------------------------------------------------

#     total = len(csv_files)
#     digit = len(str(total))

#     for current, csv_file in enumerate(
#         csv_files,
#         start=1
#     ):

#         print(
#             f"[{current:0{digit}d}/{total}] ",
#             end=""
#         )

#         resample_trajectory(
#             str(csv_file),
#             args.output_directory_name
#         )


# if __name__ == "__main__":

#     # 例:
#     # python csv_data_converter/resample.py \
#     #     output/changed_nan_lat_lon_s_h \
#     #     output/resampled_0.1

#     main()



# -*- coding: UTF-8 -*-

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


# リサンプリング間隔
RESAMPLE_INTERVAL = "100ms"


def aggregate_duplicate_times(df: pd.DataFrame) -> pd.DataFrame:
    """
    同一車両における同一時刻の異なる観測データを1つに集約する関数

    :param df:
        入力されたDataFrame
    :return:
        重複時刻を集約したDataFrame
    """

    # headingを角度からsin/cosへ変換
    heading_rad = np.deg2rad(df["heading"])

    df = df.copy()

    df["heading_sin"] = np.sin(heading_rad)
    df["heading_cos"] = np.cos(heading_rad)

    # vehicleidとtimeごとに集約
    result = (
        df.groupby(
            ["vehicleid", "time"],
            as_index=False
        ).agg({
            "latitude": "mean",
            "longitude": "mean",
            "speed": "mean",
            "heading_sin": "mean",
            "heading_cos": "mean",
            "vehiclesizeclassification": "first",
        })
    )

    # sin/cosからheadingへ戻す
    result["heading"] = (
        np.rad2deg(
            np.arctan2(
                result["heading_sin"],
                result["heading_cos"]
            )
        ) % 360
    )

    # 補間用カラムを削除
    result = result.drop(
        columns=["heading_sin", "heading_cos"]
    )

    return result


def interpolate_without_original_nan(
    vehicle_df: pd.DataFrame,
    original_index: pd.DatetimeIndex
) -> pd.DataFrame:
    """
    リサンプリングによって生成された時刻のみ補間する関数

    元データがNaNだった箇所は補間せず、NaNのまま保持する。

    :param vehicle_df:
        リサンプリング後のDataFrame
    :param original_index:
        リサンプリング前の元データの時刻
    :return:
        補間後のDataFrame
    """

    # =====================================================
    # 緯度・経度・速度
    # =====================================================

    interpolation_columns = [
        "latitude",
        "longitude",
        "speed",
    ]

    # 元データに存在していた時刻かどうか
    original_time_mask = vehicle_df.index.isin(original_index)

    # 元データでNaNだった箇所を記録
    original_nan_mask = (
        vehicle_df[interpolation_columns].isna()
        & original_time_mask[:, None]
    )

    # 線形補間
    vehicle_df[interpolation_columns] = (
        vehicle_df[interpolation_columns]
        .interpolate(method="linear")
    )

    # 元データでNaNだった箇所はNaNに戻す
    for column in interpolation_columns:
        vehicle_df.loc[
            original_nan_mask[column],
            column
        ] = np.nan

    # =====================================================
    # heading
    # =====================================================

    # 元データのheadingがNaNだった箇所を記録
    original_heading_nan_mask = (
        vehicle_df["heading"].isna()
        & original_time_mask
    )

    # headingをsin/cosへ変換
    heading_rad = np.deg2rad(vehicle_df["heading"])

    vehicle_df["heading_sin"] = np.sin(heading_rad)
    vehicle_df["heading_cos"] = np.cos(heading_rad)

    # sin/cosを線形補間
    vehicle_df["heading_sin"] = (
        vehicle_df["heading_sin"]
        .interpolate(method="linear")
    )

    vehicle_df["heading_cos"] = (
        vehicle_df["heading_cos"]
        .interpolate(method="linear")
    )

    # sin/cosからheadingへ戻す
    vehicle_df["heading"] = (
        np.rad2deg(
            np.arctan2(
                vehicle_df["heading_sin"],
                vehicle_df["heading_cos"]
            )
        ) % 360
    )

    # 元データでheadingがNaNだった箇所はNaNに戻す
    vehicle_df.loc[
        original_heading_nan_mask,
        "heading"
    ] = np.nan

    # 補間用カラムを削除
    vehicle_df = vehicle_df.drop(
        columns=[
            "heading_sin",
            "heading_cos"
        ]
    )

    return vehicle_df


def resample_trajectory(
    input_file_name: str,
    output_directory_name: str
) -> None:
    """
    CSVファイルのデータを0.1秒間隔にリサンプリングする関数

    :param input_file_name:
        入力されたファイル名
    :param output_directory_name:
        出力先のディレクトリ名
    """

    input_file = Path(input_file_name)
    output_directory = Path(output_directory_name)

    # =====================================================
    # CSVファイルの確認
    # =====================================================

    if not input_file.is_file() or input_file.suffix.lower() != ".csv":
        return

    # =====================================================
    # CSVファイルを読み込む
    # =====================================================

    try:
        df = pd.read_csv(input_file)

    except Exception as e:
        print(
            f"⚠️ CSVファイル {input_file} の読み込みに失敗しました "
            f"({e}). "
        )
        return

    # =====================================================
    # 必要なカラムの確認
    # =====================================================

    required_columns = [
        "vehicleid",
        "time",
        "latitude",
        "longitude",
        "speed",
        "heading",
        "vehiclesizeclassification",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        print(
            f"⚠️ CSVファイル {input_file} に "
            f"必要なカラム {missing_columns} が存在しません. "
        )
        return

    # =====================================================
    # timeをdatetime型へ変換
    # =====================================================

    try:
        df["time"] = pd.to_datetime(
            df["time"],
            format="mixed"
        )

    except Exception as e:
        print(
            f"⚠️ CSVファイル {input_file} の "
            f"時間変換に失敗しました ({e}). "
        )
        return

    # =====================================================
    # 完全に一致する重複レコードを削除
    # =====================================================

    df = df.drop_duplicates()

    # =====================================================
    # vehicleid + timeの重複を確認
    # =====================================================

    duplicates = df[
        df.duplicated(
            ["vehicleid", "time"],
            keep=False
        )
    ]

    if not duplicates.empty:

        print(
            f"⚠️ CSVファイル {input_file} に "
            f"`vehicleid` 及び `time` が重複しているデータが "
            f"{len(duplicates)} 件見つかりました. "
        )

        # 異なるデータを1つへ集約
        df = aggregate_duplicate_times(df)

    # =====================================================
    # vehicleid → timeの順にソート
    # =====================================================

    df = df.sort_values(
        ["vehicleid", "time"]
    )

    # =====================================================
    # 車両ごとにリサンプリング
    # =====================================================

    resampled_data = []

    for vehicle_id, vehicle_df in df.groupby(
        "vehicleid"
    ):

        vehicle_df = vehicle_df.copy()

        # -------------------------------------------------
        # timeをindexにする
        # -------------------------------------------------

        vehicle_df = vehicle_df.set_index(
            "time"
        )

        # vehicleidは後で設定するので削除
        vehicle_df = vehicle_df.drop(
            columns=["vehicleid"]
        )

        # -------------------------------------------------
        # 念のためtimeの重複を削除
        # -------------------------------------------------

        vehicle_df = vehicle_df[
            ~vehicle_df.index.duplicated(
                keep="first"
            )
        ]

        # -------------------------------------------------
        # 元データの時刻を保存
        # -------------------------------------------------

        original_index = vehicle_df.index.copy()

        # -------------------------------------------------
        # 元データの時間範囲
        # -------------------------------------------------

        start_time = vehicle_df.index.min()
        end_time = vehicle_df.index.max()

        # -------------------------------------------------
        # 0.1秒間隔の時刻を生成
        # -------------------------------------------------

        new_time_index = pd.date_range(
            start=start_time.ceil(RESAMPLE_INTERVAL),
            end=end_time.floor(RESAMPLE_INTERVAL),
            freq=RESAMPLE_INTERVAL,
            name="time"
        )

        # -------------------------------------------------
        # 0.1秒間隔の時刻が存在しない場合
        # -------------------------------------------------

        if len(new_time_index) == 0:
            continue

        # -------------------------------------------------
        # 元データと新しい時刻を結合
        # -------------------------------------------------

        combined_index = (
            vehicle_df.index
            .union(new_time_index)
            .sort_values()
        )

        vehicle_df = vehicle_df.reindex(
            combined_index
        )

        # -------------------------------------------------
        # 緯度・経度・速度・headingを補間
        #
        # 元データのNaNは補間しない
        # -------------------------------------------------

        vehicle_df = (
            interpolate_without_original_nan(
                vehicle_df,
                original_index
            )
        )

        # -------------------------------------------------
        # 車両種別を補完
        # -------------------------------------------------

        vehicle_df[
            "vehiclesizeclassification"
        ] = (
            vehicle_df[
                "vehiclesizeclassification"
            ]
            .ffill()
            .bfill()
        )

        # -------------------------------------------------
        # 車両種別を整数型へ変換
        # -------------------------------------------------

        vehicle_df[
            "vehiclesizeclassification"
        ] = (
            pd.to_numeric(
                vehicle_df[
                    "vehiclesizeclassification"
                ],
                errors="coerce"
            )
            .round()
            .astype("Int64")
        )

        # -------------------------------------------------
        # vehicleidを設定
        # -------------------------------------------------

        vehicle_df["vehicleid"] = vehicle_id

        # -------------------------------------------------
        # 生成した0.1秒時刻だけを残す
        # -------------------------------------------------

        vehicle_df = vehicle_df.loc[
            new_time_index
        ]

        # -------------------------------------------------
        # DataFrameを保存
        # -------------------------------------------------

        resampled_data.append(
            vehicle_df.reset_index()
        )

    # =====================================================
    # リサンプリング結果が存在しない場合
    # =====================================================

    if not resampled_data:

        print(
            f"⚠️ CSVファイル {input_file} に "
            f"リサンプリング処理が可能な車両データがありません. "
        )

        return

    # =====================================================
    # 車両データを結合
    # =====================================================

    result = pd.concat(
        resampled_data,
        ignore_index=True
    )

    # =====================================================
    # vehicleid → timeの順にソート
    # =====================================================

    result = result.sort_values(
        ["vehicleid", "time"]
    )

    # =====================================================
    # カラム順を元のCSVに合わせる
    # =====================================================

    result = result[
        [
            "vehicleid",
            "time",
            "latitude",
            "longitude",
            "speed",
            "heading",
            "vehiclesizeclassification",
        ]
    ]

    # =====================================================
    # timeをHH:MM:SS.sss形式へ戻す
    # =====================================================

    result["time"] = (
        result["time"]
        .dt.strftime("%H:%M:%S.%f")
        .str[:-3]
    )

    # =====================================================
    # 出力先ディレクトリを作成
    # =====================================================

    output_directory.mkdir(
        parents=True,
        exist_ok=True
    )

    # =====================================================
    # 出力ファイル名
    # =====================================================

    output_file = (
        output_directory
        / input_file.name
    )

    # =====================================================
    # CSV保存
    # =====================================================

    try:

        result.to_csv(
            output_file,
            index=False
        )

        print(
            f"✅ CSVファイル {output_file} を保存しました. "
        )

    except Exception as e:

        print(
            f"⚠️ CSVファイルの保存に失敗しました "
            f"({e}). "
        )


def main() -> None:
    """
    コマンドライン引数にて指定されたディレクトリ内の
    全CSVファイルを0.1秒間隔にリサンプリングする関数
    """

    parser = argparse.ArgumentParser(
        description=(
            "指定されたディレクトリ内の全CSVファイルを"
            "0.1秒間隔にリサンプリングします. "
        )
    )

    parser.add_argument(
        "input_directory_name",
        nargs="?",
        default="resources/raw_data",
        help=(
            "処理の対象となるCSVファイルが"
            "入っているディレクトリの名前 "
            "(デフォルト値: `resources/raw_data`)"
        ),
    )

    parser.add_argument(
        "output_directory_name",
        nargs="?",
        default="output/resampled",
        help=(
            "処理後のCSVファイルを保存する"
            "ディレクトリの名前 "
            "(デフォルト値: `output/resampled`)"
        ),
    )

    args = parser.parse_args()

    # =====================================================
    # 入力ディレクトリ
    # =====================================================

    input_directory = Path(
        args.input_directory_name
    )

    if not input_directory.is_dir():

        print(
            f"⚠️ 処理の対象となるディレクトリ "
            f"{input_directory} が存在しません. "
        )

        return

    # =====================================================
    # CSVファイルを取得
    # =====================================================

    csv_files = [
        file
        for file in input_directory.iterdir()
        if (
            file.is_file()
            and file.suffix.lower() == ".csv"
        )
    ]

    if not csv_files:

        print(
            f"⚠️ 処理の対象となるディレクトリ "
            f"{input_directory} 内にCSVファイルがありません. "
        )

        return

    # =====================================================
    # 全CSVファイルを処理
    # =====================================================

    total = len(csv_files)
    digit = len(str(total))

    for current, csv_file in enumerate(
        csv_files,
        start=1
    ):

        print(
            f"[{current:0{digit}d}/{total}] ",
            end=""
        )

        resample_trajectory(
            str(csv_file),
            args.output_directory_name
        )


if __name__ == "__main__":

    # 例:
    # python csv_data_converter/resample.py \
    #     output/changed_nan_lat_lon_s_h \
    #     output/resampled_0.1

    main()

