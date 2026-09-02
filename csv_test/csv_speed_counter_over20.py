from pathlib import Path
import pandas as pd

# パスを指定（スクリプトからの位置に合わせて変更してください）
sources_dir = Path("output/speed")

csv_files = sorted(sources_dir.glob("*.csv"))

if not csv_files:
    print(f"エラー: '{sources_dir.resolve()}' 内に CSV ファイルが見つかりませんでした。")
else:
    results = []

    for file_path in csv_files:
        try:
            # 全データを文字列として読み込み
            df = pd.read_csv(file_path, header=None, dtype=str)
            if df.empty:
                continue

            # 1列目のデータを取得
            series_str = df.iloc[:, 0].astype(str).str.strip()

            # 不定値（文字列比較）
            c_65535 = (series_str == "65535").sum()
            c_655_35 = (series_str == "655.35").sum()

            # 数値変換（文字列ヘッダー等は NaN に変換されるため安全）
            series_num = pd.to_numeric(series_str, errors='coerce')

            # 20以上のカウント
            # 1. 20以上（65535 や 655.35 などの不定値を除外した正常値）
            is_valid_ge_20 = (series_num >= 20) & (~series_str.isin(["65535", "655.35"]))
            c_ge_20_valid = is_valid_ge_20.sum()

            # 2. 20以上（不定値も含めた単純カウント）
            c_ge_20_all = (series_num >= 20).sum()

            results.append({
                "ファイル名": file_path.name,
                "65535の数": c_65535,
                "655.35の数": c_655_35,
                "20以上(正常値)": c_ge_20_valid,
                "20以上(全件)": c_ge_20_all
            })

        except Exception as e:
            print(f"警告: {file_path.name} の処理中にエラーが発生しました ({e})")

    if results:
        res_df = pd.DataFrame(results)
        print(res_df.to_string(index=False))
        print("-" * 65)
        print(f"合計 65535        : {res_df['65535の数'].sum()}")
        print(f"合計 655.35       : {res_df['655.35の数'].sum()}")
        print(f"合計 20以上(正常値): {res_df['20以上(正常値)'].sum()}")
        print(f"合計 20以上(全件)  : {res_df['20以上(全件)'].sum()}")
    else:
        print("処理対象となるデータがありませんでした。")