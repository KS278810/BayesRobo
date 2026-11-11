# Third-party notices of the BayesRobo web build

Own code: Copyright 2026 Kohei Shintani, all rights reserved, the text is in `LICENSE`. The public copy at https://github.com/KS278810/BayesRobo carries `LICENSE`, this file and the `licenses` folder.
`node build.mjs` fails when a part served from `vendor/pyodide` is not named in this file.

## Served from `vendor/pyodide`, unmodified

| Part | Version | Licence | Text or source |
|---|---|---|---|
| Pyodide runtime, `pyodide.asm.js`, `pyodide.asm.wasm`, `pyodide.mjs`, `pyodide-lock.json` | 0.27.7 | MPL-2.0 | `licenses/Pyodide-MPL-2.0.txt`; source https://github.com/pyodide/pyodide at tag 0.27.7; the tarball is checked by the sha256 in `build.mjs` |
| Python standard library, `python_stdlib.zip` | CPython 3.12.7 | PSF License Agreement | `licenses/CPython-PSF-3.12.txt` |
| OpenBLAS, `openblas-0.3.26.zip` | 0.3.26 | BSD-3-Clause | `licenses/OpenBLAS-BSD-3-Clause.txt` |
| numpy wheel | 2.0.2 | BSD-3-Clause, with the sub-licences of its random and ma parts | inside the wheel, `numpy/random/LICENSE.md` and `numpy/ma/LICENSE` |
| scipy wheel | 1.14.1 | BSD-3-Clause, with the sub-licences of uarray, pocketfft, arpack and Qhull | inside the wheel, `scipy/_lib/_uarray/LICENSE`, `scipy/fft/_pocketfft/LICENSE.md`, `scipy/sparse/linalg/_eigen/arpack/COPYING`, `scipy/spatial/qhull_src/COPYING.txt` |

The wheels are served whole, so each licence text inside a wheel travels with it. The numpy and scipy wasm wheels list no libgfortran, libquadmath or other `.libs` file; the wheel file list alone cannot show what is linked statically into a compiled module, so that point stays unverified.
The MPL-2.0 parts are Pyodide's own files, served without change. Their source is at the Pyodide repository named above.

## Not bundled

No font file is bundled. The page names Chakra Petch and IBM Plex Mono and falls back to the fonts of the visitor's system. No script is loaded from another host.

## Mascot

`assets/gratitude.gif`, `joy.gif`, `thinking.gif` and `surprise.gif`, with their `_still.png`, show robot14_ivory. The still image is made with Qwen-Image, Apache-2.0, the motion with Wan 2.2 I2V-A14B, Apache-2.0, and the background is removed by the author's own keyer. No MiniMax H3 file is used. The cards were read on 2026-11-10, see `02_ResearchRobo-agent/projects/video-models/gates.md`.
