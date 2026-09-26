@echo off
rem  ---- This top part is the Windows batch launcher (kept ASCII-only on purpose). ----
rem  ---- The real program is the PowerShell code below the "#PS-START" line.        ----
setlocal
cd /d "%~dp0"
chcp 65001 >nul
powershell -NoLogo -NoProfile -Command "$t=[IO.File]::ReadAllText('%~f0',[Text.Encoding]::UTF8); iex $t.Substring($t.LastIndexOf([string][char]10+'#PS-START'))"
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%
#PS-START
# ===========================================================================
#  BayesRobo 例題デモ（ダブルクリックで実行）
#
#  やっていること:  exe に「次に試す条件」を提案させる -> この下の Evaluate で結果(y)を
#  計算する -> CSV に書き戻す、を繰り返します。メモ帳などで開いて読めます。
#
#  自分の実験・計算に応用するには:
#    1. 下の Evaluate 関数の中身を、自分の実験（や計算）に置き換える
#    2. sample.csv を自分のデータ（変数の列 + 結果の列、min/max 行つき）に差し替える
#       ※ 変数の数が 3 つでない場合は、Evaluate と、下のループ内の x1,x2,x3 の読み出しを合わせる
# ===========================================================================
$ErrorActionPreference = "Stop"
# 日本語の表示が文字化けしないよう、出力を UTF-8 にそろえる（bat 側の chcp 65001 と同じ向き）。
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

# ---- 設定 ------------------------------------------------------------------
$Rounds = 10      # exe を呼ぶ回数（毎回、起動に数秒〜数十秒かかります）
$Batch  = 3       # 1 回で提案してもらう点の数（10 回 x 3 点 = 30 点）
$Exe    = ".\bayesrobo-windows-x64.exe"
$Source = ".\sample.csv"          # 元のデータ（書き換えません）
$Csv    = ".\demo_result.csv"     # 結果はこのファイルに書き込みます

# ---- 実験（評価）: x の値を受け取り、結果 y を返す --------------------------
# 例題: 深さの違う 4 つの谷がある関数（小さいほど良い）。
# 最小は y = -2.74（x1 = -2.96, x2 = -2.87, x3 = 2.93 のあたり）。
$Wells = @(   # 谷の中心 c・深さ d・幅 s
    @{ c = -3,-3,3; d = -3.0; s = 1.5,2.6,1.9 },
    @{ c = 3,3,3;   d = -2.4; s = 2.5,1.5,1.8 },
    @{ c = 3,-3,-3; d = -2.0; s = 1.6,2.4,2.2 },
    @{ c = -3,3,-3; d = -1.6; s = 2.2,1.6,1.7 }
)
function Evaluate([double[]]$x) {
    $y = 0.01 * ($x[0]*$x[0] + $x[1]*$x[1] + $x[2]*$x[2])
    foreach ($w in $Wells) {
        $q = 0.0
        for ($j = 0; $j -lt 3; $j++) { $q += [math]::Pow(($x[$j] - $w.c[$j]) / $w.s[$j], 2) }
        $y += $w.d * [math]::Exp(-0.5 * $q)
    }
    return $y
}

# ---- 準備の確認 ------------------------------------------------------------
if (-not (Test-Path $Exe)) {
    Write-Host "bayesrobo-windows-x64.exe が、この bat と同じフォルダにありません。" -ForegroundColor Red
    Write-Host "exe・sample.csv・run_demo.bat の 3 つを同じフォルダに置いてください。"
    exit 1
}
if (-not (Test-Path $Source)) {
    Write-Host "sample.csv が、この bat と同じフォルダにありません。" -ForegroundColor Red
    exit 1
}

# exe（Windows 版）は起動のたびにロゴ画面を出す。何度もちらつかないよう抑える。
$env:PYINSTALLER_SUPPRESS_SPLASH_SCREEN = "1"
$ci = [Globalization.CultureInfo]::InvariantCulture
Copy-Item $Source $Csv -Force

Write-Host ""
Write-Host "BayesRobo 例題デモ: $Batch 点ずつ、$Rounds 回（合計 $($Rounds * $Batch) 点）追加します。"
Write-Host "exe は毎回起動し直すため、全体で数分かかります。閉じずにお待ちください。"
Write-Host ""
$sw = [Diagnostics.Stopwatch]::StartNew()

for ($i = 1; $i -le $Rounds; $i++) {
    Write-Host ("[{0}/{1}] 次の条件を exe に提案させています..." -f $i, $Rounds)
    & $Exe append $Csv --quiet --batch $Batch | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "exe がエラーで終了しました（終了コード $LASTEXITCODE）。" -ForegroundColor Red
        exit 1
    }

    # y が空欄の行 = 提案されたばかりの条件。Evaluate で y を計算して書き込む。
    $rows = @(Import-Csv $Csv)
    $added = 0
    foreach ($r in $rows) {
        if (($r.id -notin "min", "max") -and ($r.y -eq "")) {
            $x = @([double]::Parse($r.x1, $ci), [double]::Parse($r.x2, $ci), [double]::Parse($r.x3, $ci))
            $r.y = (Evaluate $x).ToString("G10", $ci)
            $added++
        }
    }
    $rows | Export-Csv $Csv -NoTypeInformation -Encoding UTF8

    $best = $rows | Where-Object { $_.y -ne "" } | Sort-Object { [double]::Parse($_.y, $ci) } | Select-Object -First 1
    Write-Host ("      +{0} 点を評価。ここまでの最良 y = {1}" -f $added, $best.y)
}

$sw.Stop()
Write-Host ""
Write-Host ("完了（{0:N0} 秒）。結果は demo_result.csv に入っています（y が埋まった行が評価済みの点）。" -f $sw.Elapsed.TotalSeconds)
Write-Host ("最良の条件: x1={0}  x2={1}  x3={2}   y={3}" -f $best.x1, $best.x2, $best.x3, $best.y)
Write-Host "（真の最適解は x1=-2.96, x2=-2.87, x3=2.93 のあたりで y=-2.74 です）"
