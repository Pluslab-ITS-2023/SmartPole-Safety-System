from pathlib import Path

# 対象のディレクトリを設定
sources_dir = Path("output/speed")

# sourcesディレクトリ内の全CSVファイルを取得
csv_files = sorted(sources_dir.glob("*.csv"))

total_65535 = 0
total_655_35 = 0

print(f"{'ファイル名':<30} | {'65535の数':<10} | {'655.35の数':<10}")
print("-" * 58)

for file_path in csv_files:
    c_65535 = 0
    c_655_35 = 0

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            # 前後の空白・改行を除去
            val = line.strip()
            
            # 完全一致でカウント
            if val == "65535":
                c_65535 += 1
            elif val == "655.35":
                c_655_35 += 1

    total_65535 += c_65535
    total_655_35 += c_655_35

    print(f"{file_path.name:<30} | {c_65535:<10} | {c_655_35:<10}")

print("-" * 58)
print(f"{'合計':<30} | {total_65535:<10} | {total_655_35:<10}")

# from pathlib import Path
# import pandas as pd

# sources_dir = Path("output/speed")
# csv_files = sorted(sources_dir.glob("*.csv"))

# results = []

# for file_path in csv_files:
#     # 全データを文字列として読み込み
#     df = pd.read_csv(file_path, header=None, dtype=str)
#     series = df.iloc[:, 0].str.strip()

#     c_65535 = (series == "65535").sum()
#     c_655_35 = (series == "655.35").sum()

#     results.append({
#         "ファイル名": file_path.name,
#         "65535の数": c_65535,
#         "655.35の数": c_655_35
#     })

# res_df = pd.DataFrame(results)
# print(res_df.to_string(index=False))
# print("-" * 40)
# print(f"合計 65535 : {res_df['65535の数'].sum()}")
# print(f"合計 655.35: {res_df['655.35の数'].sum()}")