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

`sample.csv` は上のGIFと同じ例題です（[examples/](examples/) からも取得可）。

> Assets の下にある「Source code (zip / tar.gz)」と、緑の「Code」→「Download ZIP」は、
> GitHub が自動で付ける項目で、消せません。中身は README と例題（`sample.csv`・`quickstart.py`）
> だけなので、通常は不要です。Web 版は上のURLを開くだけで使えます（ダウンロード不要）。

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

`sample.csv` をexeへドラッグ&ドロップ。

1. 展開に**10〜30秒ほどかかる**。Windows版はロゴ画面が表示され、終わると文字だけの
   コンソール画面に切り替わる（Linux版は表示なし）。閉じずに待つ。
2. Windows に「Windows によって PC が保護されました」と出たら、
   **「詳細情報」→「実行」**（[詳しくは下](#windowsの警告について)）。
3. `BayesRobo: loading, please wait...` の文字が出れば動いている。数行の結果が出て、
   10行目に次の条件が1行追記される（`y` は空欄）。

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

## GIFを再現する（任意）

上のGIFと同じ動きを手元で作るスクリプト（Python が必要）。`quickstart.py` を
exe と同じフォルダに置いて実行すると、`output/quickstart.gif` ができる。

```
pip install numpy matplotlib pillow
python quickstart.py                           # 30回。数分〜十数分
python quickstart.py --batch 3 --n-batch 10    # 短縮版（exeの起動が10回で済む）
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
