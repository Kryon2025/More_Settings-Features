"""按主程序版本挑出属于它的 payload，供发版工作流挂到该主程序版本的 Release 上。

用法：
    python tools/collect_payloads.py <主程序版本> [--out 目录] [--manifest 路径]

判定依据是 manifest.json **每条版本记录**上的 cw2_min / cw2_max（新版结构）；
为兼容早期清单，条目上没有区间时回落到功能级区间。cw2_max 为 null 表示不限上界。
版本比较复用 make_manifest.py 的 cw_in_range，不另造一份。

例：2.0.0.dev20260928 → 该主程序应拿的那批；
    2.0.0.dev20260920 → 当年适配 20260920 的那批（如 1.3.4）。
"""
import argparse
import json
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_manifest import cw_in_range, cw_key  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("main_version", help="主程序版本，如 2.0.0.dev20260928")
    ap.add_argument("--out", default=None, help="把选中的包复制到这个目录")
    ap.add_argument("--manifest", default=None, help="默认用仓库根的 manifest.json")
    args = ap.parse_args()

    manifest_path = pathlib.Path(args.manifest) if args.manifest else ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    picked, skipped = [], []
    for feat in manifest.get("features", []):
        for ver in feat.get("versions", []):
            lo = ver.get("cw2_min", feat.get("cw2_min"))
            hi = ver.get("cw2_max", feat.get("cw2_max"))
            name = ver["asset"].rstrip("/").split("/")[-1]
            row = (feat["id"], ver["version"], lo, hi, name, ver.get("tested"))
            (picked if cw_in_range(args.main_version, lo, hi) else skipped).append(row)

    print(f"主程序 {args.main_version} 的 Release 应当包含：\n")
    print(f"{'功能':24s} {'版本':9s} {'兼容区间':44s} tested  文件")
    print("-" * 118)
    for fid, version, lo, hi, name, tested in picked:
        span = f"{lo or '不限'} ~ {hi or '不限'}"
        print(f"{fid:24s} {version:9s} {span:44s} {str(bool(tested)):6s}  {name}")

    if skipped:
        print("\n不属于该主程序版本的记录：")
        for fid, version, lo, hi, _, _t in skipped:
            print(f"  {fid:24s} {version:9s} {lo or '不限'} ~ {hi or '不限'}")

    if args.out:
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob("*.cwpayload"):
            old.unlink()
        for _fid, _v, _lo, _hi, name, _t in picked:
            src = ROOT / "payloads" / name
            if not src.is_file():
                print(f"  !! 缺文件：{name}")
                return 1
            shutil.copy2(src, out / name)
        print(f"\n已复制 {len(picked)} 个文件到 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
