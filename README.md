# BayesRobo

CSVから次の実験条件を1点提案。ガウス過程によるベイズ最適化。インストール不要。

![探索の様子](assets/quickstart.gif)

## Web版（一番かんたん）

<https://ks278810.github.io/BayesRobo/> を開き、CSVをドラッグ&ドロップ。
ブラウザ内で完結、データ送信なし。

## 入手

[Releases](https://github.com/KS278810/BayesRobo/releases/latest) の「Assets」から、
次のファイルを取得して同じフォルダに置く。

- Windows: `bayesrobo-windows-x64.exe` と `sample.csv`
- Linux: `bayesrobo-linux-x64`（初回のみ端末で `chmod +x bayesrobo-linux-x64` が必要）と `sample.csv`
- GIFを自分で再現したい人だけ: `quickstart.py`（Python が必要。下の「GIFを再現する」）

`sample.csv` は上のGIFと同じ例題（3変数・局所解が8個ある関数）です（[examples/](examples/) からも取得可）。

> Assets の下にある「Source code (zip / tar.gz)」と、緑の「Code」→「Download ZIP」は、
> GitHub が自動で付ける項目で、消せません。中身は README と例題（`sample.csv`・`quickstart.py`）
> だけなので、通常は不要です。Web 版は上のURLを開くだけで使えます（ダウンロード不要）。

## CSVの作り方

`sample.csv` の中身:

```csv
id,x1,x2,x3,y
min,-5,-5,-5,
max,5,5,5,
1,1.251,3.972,2.757,-25.0266
2,-2.748,-1.998,3.736,-72.6453
3,-4.947,3.212,2.971,45.7927
4,-0.321,-1.97,-2.216,-62.8310
5,-2.451,-0.549,0.045,-39.7843
6,0.535,4.955,2.927,91.9394
7,1.222,4.89,-2.847,59.9342
8,-3.398,1.125,-4.561,-2.1658
9,-4.643,0.149,-0.338,46.7374
10,4.172,1.292,0.141,14.1253
11,-0.031,-2.525,-4.882,44.0732
12,-3.076,1.92,-2.994,-95.5384
```

- 変数のあとに結果の列（一番右）
- `min`/`max` 行で範囲を指定（結果は空欄のまま）
- 未測定は空欄。**失敗した実験は空欄にせず最悪値を記入**（空欄は「まだ」の意味）

## まず1回だけ試す

`sample.csv` をexeへドラッグ&ドロップ。

1. 展開に**10〜30秒ほどかかる**。Windows版はロゴ画面が表示され、終わると文字だけの
   コンソール画面に切り替わる（Linux版は表示なし）。閉じずに待つ。
2. Windows に「Windows によって PC が保護されました」と出たら、
   **「詳細情報」→「実行」**（[詳しくは下](#windowsの警告について)）。
3. `BayesRobo: loading, please wait...` の文字が出れば動いている。数行の結果が出て、
   16行目に次の条件が1行追記される（`y` は空欄）。

その条件で実験し、`y` に結果を記入して保存。もう一度ドロップすると、
また次の条件が1行追記される。この繰り返し。

コマンドでも同じことができる: `.\bayesrobo-windows-x64.exe append sample.csv`
（Linux: `./bayesrobo-linux-x64 append sample.csv`）

## 自動で回す（PowerShell）

「毎回手で記入」を、簡単な数式に置き換えて自動化する例。exe と `sample.csv` を
同じフォルダに置き、PowerShell で次を貼り付け。上のGIFと同じ例題の式で `y` を
自動計算し、提案 → 計算 → 追記を30回繰り返す。exe は起動のたびに10〜30秒かかるため、
全体で数分〜十数分かかる。

```powershell
$env:PYINSTALLER_SUPPRESS_SPLASH_SCREEN = "1"   # 起動のたびにロゴ画面が出るのを抑える
$exe = ".\bayesrobo-windows-x64.exe"
$csv = "sample.csv"
foreach ($i in 1..30) {
    & $exe append $csv --quiet
    $rows = Import-Csv $csv
    foreach ($r in $rows) {
        if ($r.y -eq "" -and $r.id -notin "min","max") {
            $y = 0.0
            foreach ($v in [double]$r.x1, [double]$r.x2, [double]$r.x3) {
                $y += 0.5 * ([math]::Pow($v, 4) - 16 * [math]::Pow($v, 2) + 5 * $v)   # 例題の式(GIFと同じ)
            }
            $r.y = $y
        }
    }
    $rows | Export-Csv $csv -NoTypeInformation -Encoding UTF8
}
Import-Csv $csv | Where-Object { $_.y -ne "" } | Sort-Object { [double]$_.y } | Select-Object -First 1
```

`$r.y = …` の行を実際の実験・計算に置き換えれば、そのまま自動最適化。
最大化は `append` の後ろに `--goal max`。

Linux: `./bayesrobo-linux-x64 append …` で同様。

## GIFを再現する（任意）

上のGIFと同じ動きを手元で作るスクリプト（Python が必要）。`quickstart.py` を
exe と同じフォルダに置いて実行すると、`output/quickstart.gif` ができる。

```
pip install numpy matplotlib pillow
python quickstart.py                           # 3点ずつ10回（合計30点）。数分
python quickstart.py --batch 1 --n-batch 30    # 1点ずつ30回。数分〜十数分
```

## Windowsの警告について

「Windows によって PC が保護されました」は、exe に**デジタル署名がない**ために出ます
（署名には有料の証明書が要り、署名しても初回の警告は消えません）。ウイルスが
見つかったという意味ではありません。

- 出たら: **「詳細情報」→「実行」**（「実行」ボタンは「詳細情報」を押すまで表示されません）
- 毎回出るのが煩わしい場合: exe を右クリック →「プロパティ」→ 下の「許可する」にチェック →
  OK（または PowerShell で `Unblock-File .\bayesrobo-windows-x64.exe`）
- 警告を出さずに入手する（任意）: ブラウザで落とすと「ダウンロード元の記録」が付き、これが
  警告の元になる。PowerShell で直接取得すると付かない:

```powershell
Invoke-WebRequest https://github.com/KS278810/BayesRobo/releases/latest/download/bayesrobo-windows-x64.exe -OutFile bayesrobo-windows-x64.exe
Invoke-WebRequest https://github.com/KS278810/BayesRobo/releases/latest/download/sample.csv -OutFile sample.csv
```

- Windows 11 の「スマート アプリ コントロール」がオンの環境では、署名のない exe は警告ではなく
  起動がブロックされることがあります。その場合は Web 版を使ってください。

## 詰まったら

- 既定は最小化。大きいほど良い場合は `--goal max`（コマンド版・PowerShell版のみ）
- 一度に複数の候補が欲しいときは `--batch 3` のように追加
- 結果を埋めずに再ドロップは不可
- 配布ビルドには使用期限あり（ビルド月の翌月末）。毎月1日に新しいビルドが
  [Releases](https://github.com/KS278810/BayesRobo/releases/latest) に自動で出るので、
  期限切れの表示が出たら取り直してください
- 全オプションは `bayesrobo -h`

## このリポジトリについて

ビルド済み配布物のみ。ソースは非公開の開発リポジトリ側。自動生成のため直接編集不可、履歴なし。

## 問い合わせ

[Issues](https://github.com/KS278810/BayesRobo/issues) へ。
