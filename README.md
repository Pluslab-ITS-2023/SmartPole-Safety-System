# SmartPole Safety System

スマートポールから得られる交通参加者の軌跡データの活用を目的とするプロジェクト．

## 提供されたデータの形式

| カラム名 | 概要 | 定義 | 不定値 |
|---|---|---|---|
| `sensorid` | センサデータ処理ID | ①`14681857`: 全センサデータ, ②`15730433`: ①の中で複数センサが検出している範囲に存在する物標IDを同定してマージしたデータ, ③`13633281`: ②の後に融合したデータ | - |
| `vehiclelist` | - | - | - |
| `vehicleid` | 物標ID | センサが捉えた交通参加者に付与するユニークなID, 日毎に更新される | - |
| `time` | 日時 | 表示形式: `yyyy/m/d hh:mm:ss.000` | - |
| `latitude` | 物標の緯度 | 単位: deg. | `0` |
| `longitude` | 物標の経度 | 単位: deg. | `0` |
| `speed` | 物標の速さ | 単位: m/s | `655.35` |
| `heading` | 物標の進行方位 | 北を0度として時計回りの方向, 単位: deg. | `819.1875` |
| `acceleration` | - | - | - |
| `vehiclesizeclassification` | 物標種別 | `0`: 大型車, `2`: 普通車, `3`: バイク, `4`: 自転車, `6`: 歩行者 | - |
| `vehicleroleclassification` | - | - | - |

## データの前処理

1. ファイル名の形式を変更する

```
# `t_corrected_pos_info_yyyy_mmdd.csv` -> `yyyymmdd.csv`
python csv_data_converter/rename_file.py resources/raw_data output/renamed
```

2. 列名 `sensorid` の値が `13633281` となる行を抽出する

```
python csv_data_converter/extract_rows.py output/renamed output/extracted sensorid 13633281
```

3. 不必要な列（`sensorid`，`vehiclelist`，`acceleration`，`vehicleroleclassification`）を削除する

```
python csv_data_converter/remove_columns.py output/extracted output/removed sensorid vehiclelist acceleration vehicleroleclassification
```

4. 列名 `time` の値の形式を変更する

```
# `yyyy/m/d hh:mm:ss.000` -> `hh:mm:ss.000`
% python csv_data_converter/change_time_format.py output/removed output/changed_fmt
```

5. 不定値をそれぞれ `NaN` に置換する

```
python csv_data_converter/change_invalid_value.py output/changed_fmt output/changed_nan latitude=0 longitude=0 speed=655.35 heading=819.1875
```

6. 列名 `time` の値についてリサンプリング，重複処理，ソートを行う

```
python csv_data_converter/resample.py output/changed_nan_lat_lon_s_h output/resampled_0.1
```

1. 地理座標系からローカル座標系へ変換する

```
```

8. 移動ベクトルを算出する

```
```

9.  センサによるノイズを除去する

```
```

1.  不必要な列（`latitude`，`longitude`，`speed`, `heading`）を削除する

```

```

10. 交通参加者を分類する

```
```

## 前処理されたデータの形式

- 例: 普通車両

| カラム名 | 概要 | 定義 | 不定値 |
|---|---|---|---|
| `vehicleid` | 物標ID | センサが捉えた交通参加者に付与するユニークなID, 日毎に更新される | - |
| `time` | 時刻 | 表示形式: `hh:mm:ss.0` | - |
xy
velocity_x
velocity_y
| `vehiclesizeclassification` | 物標種別 | `0`: 大型車, `2`: 普通車, `3`: バイク, `4`: 自転車, `6`: 歩行者 | - |



交通参加者の絞り込み

CSVデータを優先道路の南進行→車両ID→時刻，優先道路の北進行→車両ID→時刻のように並び替えれば，前方の交通参加者にアテンションを加えられるのではないか？