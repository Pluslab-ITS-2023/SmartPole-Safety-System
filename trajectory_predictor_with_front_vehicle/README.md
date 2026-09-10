# trajectory_predictor_with_front_vehicle

`csv_data_converter` で `x,y` へ変換したCSVを入力にして、自車線前方・対向車線・交差方向の車両を別々に考慮する軌跡予測器です。既存の `trajectory_predictor` は変更しません。

## 前処理を一括実行

各変換プログラムを順番に実行するシェルスクリプトがあります。

```bash
conda activate smartpole
chmod +x csv_data_converter/prepare_trajectory_data.sh

./csv_data_converter/prepare_trajectory_data.sh \
  resources/raw_data/土橋一丁目 \
  output/trajectory_predictor/土橋一丁目 \
  35.042733 \
  137.146396 \
  13633281
```

実行される順番は次の通りです。

```text
1. ファイル名変更
2. sensorid抽出
3. 不要列削除
4. 不定値をNaNへ変換
5. 時刻形式変換
6. 0.100秒間隔へリサンプリング
7. 交差点中心基準のx,yへ変換
```

最終的なCSVは指定した出力ディレクトリに保存されます。途中の処理で失敗した場合は `set -euo pipefail` により停止します。中間ファイルも確認したい場合は次のように実行します。

```bash
KEEP_INTERMEDIATE=1 ./csv_data_converter/prepare_trajectory_data.sh \
  resources/raw_data/土橋一丁目 \
  output/trajectory_predictor/土橋一丁目 \
  35.042733 137.146396
```

## 入力CSV

少なくとも次の列が必要です。

```text
vehicleid,time,x,y,speed,heading
```

`x` は東方向、`y` は北方向のメートル座標です。全車両が同じ交差点中心基準の座標系に変換されている必要があります。

## 前方車両の判定

heading の規約は既存処理と同じく、北を0度、時計回りを正とします。各時刻で、自車両の進行方向に対して前方にあり、横方向のずれが `lane_width` 以下、前後距離が `max_distance` 以下の車両から最も近い1台を選びます。

モデル入力は自車両5列と、各方向4列の合計17列です。

```text
x,y,speed,heading_sin,heading_cos,
same_lane_front_exists,same_lane_front_longitudinal,
same_lane_front_lateral,same_lane_front_speed_delta,
opposing_exists,opposing_distance,opposing_lateral,opposing_speed_delta,
cross_exists,cross_distance,cross_lateral,cross_speed_delta
```

前方・対向・交差方向の車両がない場合は、それぞれの `*_exists=0`、他の特徴量は0です。

すべての方向で、まず自車両から見て前方（進行方向への投影距離が0mより大きい）であることを条件にします。デフォルトの判定値は、自車線前方が横4m以内かつ前方80m以内、対向車線が前方かつ80m以内、交差方向が前方かつ40m以内です。方向の内積が `0.5` 以上なら同方向、`-0.5` 以下なら対向、絶対値が `0.5` 未満なら交差方向とします。

## 学習

```bash
cd trajectory_predictor_with_front_vehicle
python3 train.py \
  --data-dir ../output/converted_coord \
  --output trajectory_transformer_front_vehicle.pt \
  --max-cross-distance 40 \
  --direction-similarity 0.5
```
```bash
nohup python3 -u train.py \
  --data-dir ../output/trajectory_predictor/o1001/ns \
  --output trajectory_transformer_front_vehicle.pt \
  --max-cross-distance 40 \
  --direction-similarity 0.5 \
  > nohup.out 2>&1 &
  ```

CSVファイルを日付順に70%/15%/15%へ分割します。デフォルトでは過去20点から未来10点を予測します。

## 評価

```bash
python3 evaluate.py \
  --data-dir ../output/converted_coord \
  --model trajectory_transformer_front_vehicle.pt
```

## 可視化

```bash
python3 visualize.py \
  --csv ../output/converted_coord/t_corrected_pos_info_2024_0920.csv \
  --vehicle-id 12345 \
  --model trajectory_transformer_front_vehicle.pt
```