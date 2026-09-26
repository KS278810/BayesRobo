"""BayesRobo quickstart -- 実際の exe を回して、探索の様子を GIF にします。

README の quickstart.gif を手元で再現するための例題スクリプトです。
目的関数は 3 変数の Styblinski-Tang 関数（最小化）:

    f(x1, x2, x3) = 1/2 * sum_i ( x_i^4 - 16 x_i^2 + 5 x_i ),   各変数の範囲は [-5, 5]

局所解が 2^3 = 8 個あり、真の最適解は x1 = x2 = x3 = -2.9035（f = -117.5）です。
「山が複数ある」問題で、exe が何点ずつ・どこに次の点を提案するかを見る例題です。
流れは、12 点の初期設計から始めて、「exe が次の点を提案 -> この式で y を計算 -> CSV に記入」
を繰り返し、その様子をアニメーションにします。

GIF の見方: 上の 3 枚は 3 つの変数のうち 2 つずつを取り出した図（地形は残りの変数を最も良い値に
したときの f）。灰色=初期設計、金色=追加された点、紫=別の領域を確認する探索点、
緑の星=真の最適解、緑の輪=8 個ある局所解の位置。下は「これまでの最良値」の推移です。

準備:
    pip install numpy matplotlib pillow
    bayesrobo-windows-x64.exe（Linux は bayesrobo-linux-x64）をこのファイルと同じフォルダに置く

実行:
    python quickstart.py                          # 3 点ずつ 10 回（既定。合計 30 点）
    python quickstart.py --batch 1 --n-batch 30   # 1 点ずつ 30 回（exe の起動が 30 回になる）

exe は起動のたびに 10〜30 秒ほどかかります。既定（10 回）で数分、1 点ずつ 30 回だと数分〜十数分です。
出力はこのファイルと同じ場所の output/ フォルダ（quickstart.gif と quickstart.csv）です。
"""
import argparse
import csv
import json
import os
import shlex
import shutil
import subprocess
import sys
from itertools import product
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import animation, colors, gridspec, lines

# Inter があればそれを、無ければ matplotlib 同梱の DejaVu Sans を使う（警告を出さないため）。
matplotlib.rcParams["font.family"] = ["Inter", "DejaVu Sans"]

D = 3
LO, HI = -5.0, 5.0
BOUNDS = [(LO, HI)] * D
COLS = ["x1", "x2", "x3"]
BG, PANEL, INK, GRID = "#06080f", "#0b0f1a", "#eef3fa", "#3d4a5e"
CYAN, GREEN, GRAY, GOLD, EXPLORE = "#3fc4ec", "#2fd68e", "#8fa0b8", "#f2b23c", "#b98eff"
LANDSCAPE_CMAP = colors.LinearSegmentedColormap.from_list(
    "bayesrobo_landscape", ["#0b1f3a", "#15508a", "#2f8fc4", "#8fd6ee", "#f1fafd"])

# 1 変数分 g(x) = 1/2 (x^4 - 16 x^2 + 5 x) の 2 つの谷。大域解 x = -2.9035（g = -39.1662）、
# もう一方の局所解 x = 2.7468（g = -25.2943）。全体の局所解は各変数でどちらかを選ぶ 2^3 通り。
X_BEST, X_OTHER, G_MIN = -2.903534, 2.746803, -39.166166
GLOBAL_OPTIMUM = (X_BEST,) * D + (D * G_MIN,)   # (x1, x2, x3, f)
LOCAL_MINIMA = np.array(list(product((X_BEST, X_OTHER), repeat=D)))   # 8 個 (x1, x2, x3)


def g1(x):
    return 0.5 * (x ** 4 - 16.0 * x ** 2 + 5.0 * x)


def objective(X):
    X = np.atleast_2d(np.asarray(X, float))
    return g1(X).sum(axis=1)


experiment = objective   # one "experiment" = evaluating the (unconstrained) objective


def initial_design(n=12, seed=7):
    """初期設計: 範囲内を一様に散らした n 点（乱数の種を固定してあるので毎回同じ点）。
    examples/sample.csv の最初の n 点と同一。小数 3 桁に丸めて CSV に書く。"""
    rng = np.random.default_rng(seed)
    return np.round(rng.uniform(LO, HI, (n, D)), 3)


def find_binary():
    """exe の探し方: このファイルと同じフォルダ -> カレントフォルダ -> dist/ ->
    PATH 上の bayesrobo -> `python -m bayesrobo`（最後の 2 つは開発用）。"""
    here = Path(__file__).resolve().parent
    if sys.platform == "win32":
        names = ("bayesrobo-windows-x64.exe", "bayesrobo.exe")
    else:
        names = ("bayesrobo-linux-x64", "bayesrobo")
    for folder in (here, Path.cwd(), here.parent / "dist"):
        for name in names:
            p = folder / name
            if p.is_file():
                if sys.platform != "win32" and not os.access(p, os.X_OK):
                    raise SystemExit(f"{p} に実行権限がありません。次を実行してください: chmod +x {p}")
                return [str(p)]
    found = shutil.which("bayesrobo")
    return [found] if found else [sys.executable, "-m", "bayesrobo"]


def read_points(path):
    with open(path, newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
    pts = [tuple(float(r[c]) for c in COLS) + (float(r["y"]),)
           for r in rows if r["id"] not in ("min", "max") and r["y"]]
    return np.array(pts) if pts else np.empty((0, D + 1))


def fill_blank_y(path):
    """Fill in rows whose y is blank by "running the experiment". Returns how many rows that was."""
    with open(path, newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
        fields = list(rows[0].keys())
    todo = [r for r in rows if r["id"] not in ("min", "max") and not r["y"]]
    if todo:
        X = np.array([[float(r[c]) for c in COLS] for r in todo])
        for r, v in zip(todo, experiment(X)):
            r["y"] = f"{v:.6f}"
        with open(path, "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.DictWriter(fp, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    return len(todo)


# 上段の 3 枚: (横軸, 縦軸) の組。残りの変数は「いちばん良い値」にした断面でなく、その変数について
# 最小化した値を使う。f は変数ごとに分かれる形（和）なので、2 変数の地形は g(xa)+g(xb)+g の最小値。
PAIRS = [(0, 1), (0, 2), (1, 2)]


def draw(fig, grid, snap, n_batch):
    """One frame: top = 3 projections (landscape + points), bottom = best value found so far."""
    s, F = grid
    pts, sizes, batch_i, best_hist, kind = snap
    gs = gridspec.GridSpec(2, 3, height_ratios=[1.7, 1], hspace=0.45, wspace=0.28)

    n_initial = sizes[0]
    done = int(np.sum(sizes[:batch_i + 1]))
    prev = int(np.sum(sizes[:batch_i]))
    new_start = max(prev, n_initial) if batch_i > 0 else 0
    new_color = EXPLORE if kind.startswith("exploration") else GOLD

    for k, (a, b) in enumerate(PAIRS):
        ax = fig.add_subplot(gs[0, k])
        ax.set_facecolor(PANEL)
        # 値の分位で段を切る（f は端で急に大きくなるので、等間隔だと谷の構造が暗く潰れる）。
        lv = np.unique(np.percentile(F, np.linspace(0, 100, 41)))
        ax.contourf(s, s, F, levels=lv, cmap=LANDSCAPE_CMAP)
        ax.contour(s, s, F, levels=lv[::4], colors="white", linewidths=0.4, alpha=0.3)
        # 8 個の局所解（この 2 変数に射影すると 4 か所）と、大域解（緑の星）。
        for u, v in {(m[a], m[b]) for m in LOCAL_MINIMA}:
            ax.scatter(u, v, s=150, facecolors="none", edgecolors=GREEN, linewidths=1.1,
                       alpha=0.75, zorder=5)
        ax.scatter(X_BEST, X_BEST, marker="*", s=330, facecolors="none", edgecolors=GREEN,
                   linewidths=2.0, zorder=6)
        if len(pts):
            # Initial design: neutral gray, stays gray for the whole animation.
            ax.scatter(pts[:n_initial, a], pts[:n_initial, b], s=70, facecolors=GRAY,
                       edgecolors=INK, linewidths=0.9, zorder=4)
            # Everything BayesRobo has added so far (older batches): dimmer gold.
            if prev > n_initial:
                ax.scatter(pts[n_initial:prev, a], pts[n_initial:prev, b], s=70, facecolors=GOLD,
                           edgecolors=BG, linewidths=1.0, alpha=0.45, zorder=5)
            # This frame's newly-added points: full-brightness halo, gold for an ordinary
            # proposal, violet when the exe marks it as an exploration point.
            if done > new_start:
                ax.scatter(pts[new_start:done, a], pts[new_start:done, b], s=230,
                           facecolors=new_color, edgecolors="none", alpha=0.25, zorder=5)
                ax.scatter(pts[new_start:done, a], pts[new_start:done, b], s=80,
                           facecolors=new_color, edgecolors=INK, linewidths=1.3, zorder=6)
        ax.set_xlim(LO, HI); ax.set_ylim(LO, HI); ax.set_aspect("equal")
        ax.set_xlabel(COLS[a], color=INK, fontsize=11)
        ax.set_ylabel(COLS[b], color=INK, fontsize=11)
        ax.tick_params(colors=INK, labelsize=10)
        for sp in ax.spines.values():
            sp.set_color(GRID)
        ax.set_title(f"{COLS[a]} - {COLS[b]}", fontsize=12, color=INK, pad=8)
        if k == 0:
            handles = [
                lines.Line2D([], [], marker="o", linestyle="none", markersize=8,
                             markerfacecolor=GRAY, markeredgecolor=BG, label="initial"),
                lines.Line2D([], [], marker="o", linestyle="none", markersize=8,
                             markerfacecolor=GOLD, markeredgecolor=INK, label="added"),
                lines.Line2D([], [], marker="o", linestyle="none", markersize=8,
                             markerfacecolor=EXPLORE, markeredgecolor=INK, label="explore"),
                lines.Line2D([], [], marker="*", linestyle="none", markersize=12,
                             markerfacecolor="none", markeredgecolor=GREEN, label="optimum"),
            ]
            ax.legend(handles=handles, loc="upper right", fontsize=8.5, facecolor=PANEL,
                      edgecolor=GRID, labelcolor=INK, framealpha=0.92)

    ax3 = fig.add_subplot(gs[1, :])
    ax3.set_facecolor(PANEL)
    ax3.plot(range(1, len(best_hist) + 1), best_hist, "-o", ms=4, lw=2.0, color=GOLD)
    # No inline label for this line: its color (green, matching the star above) is the
    # only explanation, so a legend box never has to fight the line for space.
    ax3.axhline(GLOBAL_OPTIMUM[-1], ls=":", lw=1.6, color=GREEN)
    ax3.set_title("Best y", fontsize=12, color=INK, pad=8)
    ax3.set_xlabel("points", color=INK, fontsize=11)
    ax3.set_ylabel("y", color=INK, fontsize=11)
    ax3.set_xlim(1, len(best_hist) if len(best_hist) > 1 else 2)
    ax3.tick_params(colors=INK, labelsize=10)
    ax3.grid(alpha=0.18, color=GRID)
    for sp in ax3.spines.values():
        sp.set_color(GRID)

    label = "initial" if batch_i == 0 else f"batch {batch_i}/{n_batch}"
    fig.suptitle(f"{label}  ·  {done} pts  ·  best {best_hist[done - 1]:.2f}",
                 fontsize=14, fontweight="bold", color=INK)


def main():
    # Japanese output must not crash on a non-UTF-8 console / pipe (e.g. cp1252).
    for st in (sys.stdout, sys.stderr):
        if hasattr(st, "reconfigure"):
            st.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", type=int, default=3, help="1 回の exe 呼び出しで提案させる点数 [既定: 3]")
    ap.add_argument("--n-batch", type=int, default=10, help="exe を呼ぶ回数 [既定: 10]")
    ap.add_argument("--exe", default=None,
                    help="使う exe のパス [既定: このファイルと同じフォルダの "
                         "bayesrobo-windows-x64.exe / bayesrobo-linux-x64]")
    ap.add_argument("--explore", default=None,
                    help="`append --explore` へそのまま渡す（省略時は exe の既定）")
    ap.add_argument("--edge-tau", type=float, default=None, dest="edge_tau",
                    help="`append --edge-tau` へそのまま渡す（省略時は exe の既定）")
    a = ap.parse_args()

    exe = shlex.split(a.exe) if a.exe else find_binary()
    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / "quickstart.csv"

    # Initial design: our own fixed set of points, not the tool's space-filling design --
    # makes "what we started with" vs "what BayesRobo added" unambiguous.
    design = initial_design()
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["id"] + COLS + ["y"])
        w.writerow(["min"] + [b[0] for b in BOUNDS] + [""])
        w.writerow(["max"] + [b[1] for b in BOUNDS] + [""])
        for i, row in enumerate(design):
            w.writerow([i] + list(row) + [""])

    # 上段の地形: f は和の形なので、2 変数 (xa, xb) の地形は g(xa) + g(xb) + (残りの変数の最小値)。
    s = np.linspace(LO, HI, 300)
    F = g1(s)[None, :] + g1(s)[:, None] + G_MIN
    grid = (s, F)

    print(f"[1/3] 使用する exe: {' '.join(exe)}")
    print(f"      exe は起動のたびに 10〜30 秒かかります（{a.n_batch} 回呼び出します。しばらくお待ちください）")
    # exe（Windows 版）は起動画面を出すが、何度もちらつかせないよう抑制する（PyInstaller 公式の環境変数）。
    child_env = dict(os.environ, PYINSTALLER_SUPPRESS_SPLASH_SCREEN="1")
    sizes, snaps = [len(design)], []
    fill_blank_y(csv_path)   # evaluate the initial design directly, no proposal step
    pts = read_points(csv_path)
    best = np.minimum.accumulate(pts[:, -1])
    snaps.append((pts.copy(), list(sizes), 0, best.copy(), "acquisition"))
    print(f"      初期設計: {sizes[-1]} 点  最良 y={best[-1]:.2f}")

    for i in range(1, a.n_batch + 1):
        cmd = exe + ["append", str(csv_path), "--quiet", "--json",
                    "--goal", "min", "--batch", str(a.batch)]
        if a.explore is not None:
            cmd += ["--explore", str(a.explore)]
        if a.edge_tau is not None:
            cmd += ["--edge-tau", str(a.edge_tau)]
        p = subprocess.run(cmd, text=True, capture_output=True, env=child_env)
        if p.returncode != 0:
            print(p.stdout, p.stderr, file=sys.stderr)
            raise SystemExit(f"'{' '.join(cmd)}' が失敗しました (終了コード {p.returncode})")
        kind = "acquisition"
        for line in p.stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                kind = json.loads(line).get("proposal_kind", kind)
        sizes.append(fill_blank_y(csv_path))
        pts = read_points(csv_path)
        best = np.minimum.accumulate(pts[:, -1])
        snaps.append((pts.copy(), list(sizes), i, best.copy(), kind))
        tag = "（探索点）" if kind.startswith("exploration") else ""
        print(f"      {i}/{a.n_batch} 回目: +{sizes[-1]} 点（計 {len(pts)} 点）  最良 y={best[-1]:.2f}{tag}")

    print("[2/3] GIF を作成中...")
    fig = plt.figure(figsize=(13, 7.4), facecolor=BG)
    writers = [("gif", animation.PillowWriter(fps=1.3), out_dir / "quickstart.gif")]
    if animation.writers.is_available("ffmpeg"):
        writers.append(("mp4", animation.FFMpegWriter(fps=1.3, bitrate=2600),
                        out_dir / "quickstart.mp4"))
    for kind, writer, path in writers:
        with writer.saving(fig, str(path), dpi=100):
            for j, snap in enumerate(snaps):
                draw(fig, grid, snap, a.n_batch)
                for _ in range(3 if j in (0, len(snaps) - 1) else 1):
                    writer.grab_frame()
                fig.clf()
        print(f"      {kind}: {path}")
    plt.close(fig)

    print("[3/3] 完了")
    dist = np.sqrt((((pts[:, :D] - X_BEST) / (HI - LO)) ** 2).sum(-1)).min()
    print(f"      真の最適解に最も近い測定点までの距離: {dist:.3f}（探索範囲に対する比）")
    print(f"      最良 y = {best[-1]:.2f}（真の最適解は {GLOBAL_OPTIMUM[-1]:.1f}）")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
