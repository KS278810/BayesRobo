"""BayesRobo quickstart -- 実際の exe を回して、探索の様子を GIF にします。

README の quickstart.gif を手元で再現するための例題スクリプトです。
目的関数 f(x1, x2) = sin(x1) - cos(2*x1)*cos(x2)（最小化）を題材に、
3x3 の格子点（初期設計）から始めて、「exe が次の点を提案 -> この式で y を計算
-> CSV に記入」を繰り返し、その様子をアニメーションにします。
（式は Shintani (2023) IJNME 124(10):2196-2214, Fig. 11 の項の符号を反転したもの。）

GIF の見方: 左は地形と点（灰色=初期設計、金色=追加された点、紫=別の領域を確認する探索点、
緑の星=真の最適解）、右は「これまでの最良値」の推移です。

準備:
    pip install numpy matplotlib pillow
    bayesrobo-windows-x64.exe（Linux は bayesrobo-linux-x64）をこのファイルと同じフォルダに置く

実行:
    python quickstart.py                          # 30 回（既定）
    python quickstart.py --batch 3 --n-batch 10   # 短縮版（exe の起動が 10 回で済む）

exe は起動のたびに 10〜30 秒ほどかかるため、既定では全体で数分〜十数分かかります。
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
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import animation, colors, gridspec, lines

# Inter があればそれを、無ければ matplotlib 同梱の DejaVu Sans を使う（警告を出さないため）。
matplotlib.rcParams["font.family"] = ["Inter", "DejaVu Sans"]

TWO_PI = 2.0 * np.pi
# Search window: one full period on each axis, shifted so that an interior
# local minimum is inside the frame.
BOUNDS = [(np.pi / 4, np.pi / 4 + TWO_PI), (-np.pi / 2, -np.pi / 2 + TWO_PI)]
BG, PANEL, INK, GRID = "#06080f", "#0b0f1a", "#eef3fa", "#3d4a5e"
CYAN, GREEN, GRAY, GOLD, EXPLORE = "#3fc4ec", "#2fd68e", "#8fa0b8", "#f2b23c", "#b98eff"
LANDSCAPE_CMAP = colors.LinearSegmentedColormap.from_list(
    "bayesrobo_landscape", ["#06080f", "#0d2a45", "#155a82", CYAN])

GLOBAL_OPTIMUM = (3 * np.pi / 2, np.pi, -2.0)   # (x1, x2, f) -- see _find_optima()
LOCAL_MINIMUM = (3 * np.pi / 2 - 1.322, 0.0, -1.125)   # (x1, x2, f) -- an interior local minimum


def objective(X):
    X = np.atleast_2d(np.asarray(X, float))
    return np.sin(X[:, 0]) - np.cos(2 * X[:, 0]) * np.cos(X[:, 1])


experiment = objective   # one "experiment" = evaluating the (unconstrained) objective


def _find_optima():
    """Multistart L-BFGS-B used once, offline, to derive GLOBAL_OPTIMUM above.

    Not called by this script (needs scipy, which nothing else here uses) --
    kept so GLOBAL_OPTIMUM is reproducible rather than hand-typed.
    """
    from scipy.optimize import minimize
    seen = {}
    xs = np.linspace(0, TWO_PI, 20)
    for x1 in xs:
        for x2 in xs:
            r = minimize(lambda x: float(objective(x)[0]), [x1, x2], bounds=BOUNDS, method="L-BFGS-B")
            if r.success:
                seen[round(float(r.fun), 3)] = (round(float(r.x[0]), 3), round(float(r.x[1]), 3))
    for val, (x1, x2) in sorted(seen.items()):
        print(f"f={val:+.3f}  x=({x1:.3f}, {x2:.3f})")
    return seen


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
    pts = [(float(r["x1"]), float(r["x2"]), float(r["y"]))
           for r in rows if r["id"] not in ("min", "max") and r["y"]]
    return np.array(pts) if pts else np.empty((0, 3))


def fill_blank_y(path):
    """Fill in rows whose y is blank by "running the experiment". Returns how many rows that was."""
    with open(path, newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
        fields = list(rows[0].keys())
    todo = [r for r in rows if r["id"] not in ("min", "max") and not r["y"]]
    if todo:
        X = np.array([[float(r["x1"]), float(r["x2"])] for r in todo])
        for r, v in zip(todo, experiment(X)):
            r["y"] = f"{v:.6f}"
        with open(path, "w", newline="", encoding="utf-8-sig") as fp:
            w = csv.DictWriter(fp, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    return len(todo)


def draw(fig, grid, snap, n_batch):
    """One frame: left = landscape + points, right = best value found so far."""
    X1, X2, F = grid
    pts, sizes, batch_i, best_hist, kind = snap
    gs = gridspec.GridSpec(1, 2, width_ratios=[1.5, 1], wspace=0.28)

    ax = fig.add_subplot(gs[0])
    ax.set_facecolor(PANEL)
    ax.contourf(X1, X2, F, levels=40, cmap=LANDSCAPE_CMAP)
    ax.contour(X1, X2, F, levels=12, colors="white", linewidths=0.4, alpha=0.25)
    gx, gy, gv = GLOBAL_OPTIMUM
    ax.scatter(gx, gy, marker="*", s=340, facecolors="none", edgecolors=GREEN,
               linewidths=2.0, zorder=6)

    if len(pts):
        n_initial = sizes[0]
        done = int(np.sum(sizes[:batch_i + 1]))
        prev = int(np.sum(sizes[:batch_i]))
        # Initial 3x3 grid: neutral gray, stays gray for the whole animation.
        ax.scatter(pts[:n_initial, 0], pts[:n_initial, 1], s=90, facecolors=GRAY,
                   edgecolors=INK, linewidths=0.9, zorder=4)
        # Everything BayesRobo has added so far (older batches): dimmer gold.
        if prev > n_initial:
            ax.scatter(pts[n_initial:prev, 0], pts[n_initial:prev, 1], s=90, facecolors=GOLD,
                       edgecolors=BG, linewidths=1.0, alpha=0.45, zorder=5)
        # This frame's newly-added points: full-brightness halo, gold for an
        # ordinary proposal, violet when the exe marks it as an exploration
        # point (proposal_kind starts with "exploration").
        new_start = max(prev, n_initial) if batch_i > 0 else 0
        new_color = EXPLORE if kind.startswith("exploration") else GOLD
        if done > new_start:
            ax.scatter(pts[new_start:done, 0], pts[new_start:done, 1], s=260, facecolors=new_color,
                       edgecolors="none", alpha=0.25, zorder=5)
            ax.scatter(pts[new_start:done, 0], pts[new_start:done, 1], s=100, facecolors=new_color,
                       edgecolors=INK, linewidths=1.4, zorder=6)

    ax.set_xlim(*BOUNDS[0]); ax.set_ylim(*BOUNDS[1]); ax.set_aspect("equal")
    ax.set_xlabel("x1", color=INK, fontsize=12)
    ax.set_ylabel("x2", color=INK, fontsize=12)
    ax.tick_params(colors=INK, labelsize=11)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.set_title("Landscape", fontsize=13, color=INK, pad=10)
    handles = [
        lines.Line2D([], [], marker="o", linestyle="none", markersize=9,
                     markerfacecolor=GRAY, markeredgecolor=BG, label="initial"),
        lines.Line2D([], [], marker="o", linestyle="none", markersize=9,
                     markerfacecolor=GOLD, markeredgecolor=INK, label="added"),
        lines.Line2D([], [], marker="o", linestyle="none", markersize=9,
                     markerfacecolor=EXPLORE, markeredgecolor=INK, label="explore"),
        lines.Line2D([], [], marker="*", linestyle="none", markersize=13,
                     markerfacecolor="none", markeredgecolor=GREEN, label="optimum"),
    ]
    ax.legend(handles=handles, loc="upper right", fontsize=9.5, facecolor=PANEL,
              edgecolor=GRID, labelcolor=INK, framealpha=0.92)

    ax3 = fig.add_subplot(gs[1])
    ax3.set_facecolor(PANEL)
    ax3.plot(range(1, len(best_hist) + 1), best_hist, "-o", ms=4, lw=2.0, color=GOLD)
    # No inline label for this line: its color (green, matching the star on the
    # left) is the only explanation, so a legend box never has to fight the
    # line for space or jump around as the line moves frame to frame.
    ax3.axhline(gv, ls=":", lw=1.6, color=GREEN)
    ax3.set_title("Best y", fontsize=13, color=INK, pad=10)
    ax3.set_xlabel("points", color=INK, fontsize=12)
    ax3.set_ylabel("y", color=INK, fontsize=12)
    ax3.set_xlim(1, len(best_hist) if len(best_hist) > 1 else 2)
    ax3.tick_params(colors=INK, labelsize=11)
    ax3.grid(alpha=0.18, color=GRID)
    for s in ax3.spines.values():
        s.set_color(GRID)

    done = int(np.sum(sizes[:batch_i + 1]))
    label = "initial" if batch_i == 0 else f"batch {batch_i}/{n_batch}"
    fig.suptitle(f"{label}  ·  {done} pts  ·  best {best_hist[done - 1]:.3f}",
                 fontsize=14, fontweight="bold", color=INK)


def initial_grid_points(n_per_axis=3):
    """A plain n x n grid strictly inside the bounds (not on the edges), so it
    reads as "a deliberate starting layout" rather than touching the frame."""
    fracs = (np.arange(n_per_axis) + 0.5) / n_per_axis
    xs = BOUNDS[0][0] + fracs * (BOUNDS[0][1] - BOUNDS[0][0])
    ys = BOUNDS[1][0] + fracs * (BOUNDS[1][1] - BOUNDS[1][0])
    X1, X2 = np.meshgrid(xs, ys)
    return np.c_[X1.ravel(), X2.ravel()]


def main():
    # Japanese output must not crash on a non-UTF-8 console / pipe (e.g. cp1252).
    for st in (sys.stdout, sys.stderr):
        if hasattr(st, "reconfigure"):
            st.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", type=int, default=1, help="1 回の exe 呼び出しで提案させる点数 [既定: 1]")
    ap.add_argument("--n-batch", type=int, default=30, help="exe を呼ぶ回数 [既定: 30]")
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

    # Initial design: our own 3x3 grid, not the tool's space-filling design --
    # makes "what we started with" vs "what BayesRobo added" unambiguous.
    grid_pts = initial_grid_points(3)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.writer(fp)
        w.writerow(["id", "x1", "x2", "y"])
        w.writerow(["min", BOUNDS[0][0], BOUNDS[1][0], ""])
        w.writerow(["max", BOUNDS[0][1], BOUNDS[1][1], ""])
        for i, (x1, x2) in enumerate(grid_pts):
            w.writerow([i, x1, x2, ""])

    n = 300
    xs = np.linspace(*BOUNDS[0], n)
    X1, X2 = np.meshgrid(xs, np.linspace(*BOUNDS[1], n))
    flat = np.c_[X1.ravel(), X2.ravel()]
    grid = (X1, X2, experiment(flat).reshape(X1.shape))

    print(f"[1/3] 使用する exe: {' '.join(exe)}")
    print(f"      exe は起動のたびに 10〜30 秒かかります（{a.n_batch} 回呼び出します。しばらくお待ちください）")
    # exe（Windows 版）は起動画面を出すが、30 回ちらつかせないよう抑制する（PyInstaller 公式の環境変数）。
    child_env = dict(os.environ, PYINSTALLER_SUPPRESS_SPLASH_SCREEN="1")
    sizes, snaps = [len(grid_pts)], []
    fill_blank_y(csv_path)   # evaluate the 3x3 grid directly, no proposal step
    pts = read_points(csv_path)
    best = np.minimum.accumulate(pts[:, 2])
    snaps.append((pts.copy(), list(sizes), 0, best.copy(), "acquisition"))
    print(f"      初期設計: {sizes[-1]} 点  最良 y={best[-1]:.3f}")

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
        best = np.minimum.accumulate(pts[:, 2])
        snaps.append((pts.copy(), list(sizes), i, best.copy(), kind))
        tag = "（探索点）" if kind.startswith("exploration") else ""
        print(f"      {i}/{a.n_batch} 回目: +{sizes[-1]} 点（計 {len(pts)} 点）  最良 y={best[-1]:.3f}{tag}")

    print("[2/3] GIF を作成中...")
    fig = plt.figure(figsize=(13, 6.2), facecolor=BG)
    writers = [("gif", animation.PillowWriter(fps=1.3), out_dir / "quickstart.gif")]
    if animation.writers.is_available("ffmpeg"):
        writers.append(("mp4", animation.FFMpegWriter(fps=1.3, bitrate=2600),
                        out_dir / "quickstart.mp4"))
    for kind, writer, path in writers:
        with writer.saving(fig, str(path), dpi=110):
            for j, snap in enumerate(snaps):
                draw(fig, grid, snap, a.n_batch)
                for _ in range(3 if j in (0, len(snaps) - 1) else 1):
                    writer.grab_frame()
                fig.clf()
        print(f"      {kind}: {path}")
    plt.close(fig)

    print("[3/3] 完了")
    gx, gy, gv = GLOBAL_OPTIMUM
    dist = np.sqrt((((pts[:, :2] - [gx, gy]) / TWO_PI) ** 2).sum(-1)).min()
    print(f"      真の最適解に最も近い測定点までの距離: {dist:.3f}（探索範囲に対する比）")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
