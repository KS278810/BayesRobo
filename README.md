# BayesRobo

CSVから次の実験条件を1点提案。ガウス過程によるベイズ最適化。インストール不要。

![探索の様子](assets/quickstart.gif)

## Web版（一番かんたん）

<https://ks278810.github.io/BayesRobo/> を開き、CSVをドラッグ&ドロップ。
ブラウザ内で完結、データ送信なし。

## 実行ファイル版

[Releases](https://github.com/KS278810/BayesRobo/releases/latest) から取得。

- Windows: `bayesrobo-windows-x64.exe`
- Linux: `bayesrobo-linux-x64`（初回のみ端末で `chmod +x bayesrobo-linux-x64` が必要）

CSVをドラッグ&ドロップするだけで、次の1点を追記（既定は最小化）。

## 自動で回す（PowerShell）

exe と同じフォルダに `template.csv` を置き、PowerShell で次を貼り付け。
例題の式で `y` を自動計算し、提案 → 評価 → 追記を 20 回繰り返し。

```powershell
$exe = ".\bayesrobo-windows-x64.exe"
$csv = "template.csv"
foreach ($i in 1..20) {
    & $exe append $csv --quiet
    $rows = Import-Csv $csv
    foreach ($r in $rows) {
        if ($r.y -eq "" -and $r.id -notin "min","max") {
            $x1 = [double]$r.x1; $x2 = [double]$r.x2
            $r.y = ($x1 - 0.3) * ($x1 - 0.3) + ($x2 - 0.7) * ($x2 - 0.7)   # 例題: 最小は (0.3, 0.7)
        }
    }
    $rows | Export-Csv $csv -NoTypeInformation -Encoding UTF8
}
Import-Csv $csv | Where-Object { $_.y -ne "" } | Sort-Object { [double]$_.y } | Select-Object -First 1
```

`$r.y = …` の行を実際の実験・計算に置き換えれば、そのまま自動最適化。
最大化は `append` の後ろに `--goal max`。

Linux: `./bayesrobo-linux-x64 append …` で同様。

## CSVの作り方

```csv
id,x1_temp_C,x2_time_sec,y_bitterness
min,88,20,
max,96,40,
1,88,20,54.1
2,88,40,161.1
3,96,20,54.6
4,96,40,161.4
5,92,30,8.3
```

- 変数のあとに結果の列（一番右）
- `min`/`max` 行で範囲を指定（結果は空欄のまま）
- 未測定は空欄。**失敗した実験は空欄にせず最悪値を記入**（空欄は「まだ」の意味）

サンプル同梱: `template.csv`（空の書式）・`sample_coffee_extraction.csv`（実例）。
[examples/](examples/) にも同じものあり（開いて「Raw」→「名前を付けて保存」）。

## 繰り返し方

1. CSVをドロップ → 次の条件が1行追記
2. その条件で実験、結果を記入して保存
3. 1へ戻る

## 詰まったら

- 既定は最小化。大きいほど良い場合は `--goal max`（コマンド版・PowerShell版のみ）
- 結果を埋めずに再ドロップは不可
- Windows警告「保護されました」→「詳細情報」→「実行」
- 配布ビルドには使用期限あり（ビルド月の翌月末）

## コマンド版

```bash
bayesrobo append データ.csv --goal max --batch 3
```

全オプションは `bayesrobo -h`。

## このリポジトリについて

ビルド済み配布物のみ。ソースは非公開の開発リポジトリ側。自動生成のため直接編集不可、履歴なし。

## 問い合わせ

[Issues](https://github.com/KS278810/BayesRobo/issues) へ。
