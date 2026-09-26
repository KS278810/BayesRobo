# BayesRobo

CSVから次の実験条件を1点提案。ガウス過程によるベイズ最適化。インストール不要。

![探索の様子](assets/quickstart.gif)

## Web版（一番かんたん）

<https://ks278810.github.io/BayesRobo/> を開き、CSVをドラッグ&ドロップ。
ブラウザ内で完結、データ送信なし。

## 入手

[Releases](https://github.com/KS278810/BayesRobo/releases/latest) から3つ取得。
すべて同じフォルダに置く。

- Windows: `bayesrobo-windows-x64.exe`
- Linux: `bayesrobo-linux-x64`（初回のみ端末で `chmod +x bayesrobo-linux-x64` が必要）
- サンプル: `sample.csv`（上のGIFと同じ例題。[examples/](examples/) からも取得可、
  開いて「Raw」→「名前を付けて保存」）

## CSVの作り方

`sample.csv` の中身:

```csv
id,x1,x2,y
min,0.785,-1.571,
max,7.069,4.712,
1,1.833,-0.524,1.715
2,3.927,-0.524,-0.707
3,6.021,-0.524,-1.009
4,1.833,1.571,0.966
5,3.927,1.571,-0.707
6,6.021,1.571,-0.259
7,1.833,3.665,0.216
8,3.927,3.665,-0.707
9,6.021,3.665,0.491
```

- 変数のあとに結果の列（一番右）
- `min`/`max` 行で範囲を指定（結果は空欄のまま）
- 未測定は空欄。**失敗した実験は空欄にせず最悪値を記入**（空欄は「まだ」の意味）

## まず1回だけ試す

`sample.csv` をexeへドラッグ&ドロップ。10行目に次の条件が1行追記される
（`y` は空欄）。その条件で実験し、`y` に結果を記入して保存。もう一度ドロップすると、
また次の条件が1行追記される。この繰り返し。

コマンドでも同じことができる: `.\bayesrobo-windows-x64.exe append sample.csv`
（Linux: `./bayesrobo-linux-x64 append sample.csv`）

## 自動で回す（PowerShell）

「毎回手で記入」を、簡単な数式に置き換えて自動化する例。exe と `sample.csv` を
同じフォルダに置き、PowerShell で次を貼り付け。上のGIFと同じ例題の式で `y` を
自動計算し、提案 → 計算 → 追記を30回繰り返す。

```powershell
$exe = ".\bayesrobo-windows-x64.exe"
$csv = "sample.csv"
foreach ($i in 1..30) {
    & $exe append $csv --quiet
    $rows = Import-Csv $csv
    foreach ($r in $rows) {
        if ($r.y -eq "" -and $r.id -notin "min","max") {
            $x1 = [double]$r.x1; $x2 = [double]$r.x2
            $r.y = [math]::Sin($x1) - [math]::Cos(2 * $x1) * [math]::Cos($x2)   # 例題の式(GIFと同じ)
        }
    }
    $rows | Export-Csv $csv -NoTypeInformation -Encoding UTF8
}
Import-Csv $csv | Where-Object { $_.y -ne "" } | Sort-Object { [double]$_.y } | Select-Object -First 1
```

`$r.y = …` の行を実際の実験・計算に置き換えれば、そのまま自動最適化。
最大化は `append` の後ろに `--goal max`。

Linux: `./bayesrobo-linux-x64 append …` で同様。

## 詰まったら

- 既定は最小化。大きいほど良い場合は `--goal max`（コマンド版・PowerShell版のみ）
- 一度に複数の候補が欲しいときは `--batch 3` のように追加
- 結果を埋めずに再ドロップは不可
- Windows警告「保護されました」→「詳細情報」→「実行」
- 配布ビルドには使用期限あり（ビルド月の翌月末）
- 全オプションは `bayesrobo -h`

## このリポジトリについて

ビルド済み配布物のみ。ソースは非公開の開発リポジトリ側。自動生成のため直接編集不可、履歴なし。

## 問い合わせ

[Issues](https://github.com/KS278810/BayesRobo/issues) へ。
