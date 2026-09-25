"""根据构建产物生成 / 更新适配清单 manifest.json。

用法（在插件根目录执行）：
    python tools/make_manifest.py --dir "F:\\class widgets 2 插件" --tag v1.3.3.20260916

做的事：
    1. 读人工维护的 tools/features.json（策略：功能名、碰的文件、适配的主程序版本区间）
    2. 扫描 --dir 下的 *.cwplugin，算出 sha256 和字节数，读包内 cwplugin.json 拿版本号
    3. 按插件 id 与 features.json 里的 id 对应
    4. 合并进现有 manifest.json：**已有版本条目原样保留**（尤其是你确认过的 tested=true），
       新版本一律先写 tested=false
    5. 写出 manifest.json

设计要点：人工填的字段（name/summary/patches/cw2_min/cw2_max）永远以 features.json 为准，
脚本只负责往里填它自己算得出来的东西（sha256/size/asset/version）。
"""

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys
import zipfile

# ── 主程序版本比较 ────────────────────────────────────────────
# 主程序用 devYYYYMMDD 这种日期版本，不能用 PEP 440 比较
# （packaging 里 "dev20260923" 会直接判无效）。取 8 位日期按整数比。


def cw_key(v):
    """把主程序版本转成可排序的键。取到 8 位日期就按数字，否则退回字符串。"""
    m = re.search(r"(\d{8})", str(v or ""))
    if m:
        return (0, int(m.group(1)))
    return (1, str(v or ""))


def cw_in_range(ver, lo, hi):
    """ver 是否落在 [lo, hi] 内。lo/hi 为 NULL 表示不限该侧。"""
    if not ver:
        return False
    k = cw_key(ver)
    if lo and k < cw_key(lo):
        return False
    if hi and k > cw_key(hi):
        return False
    return True


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_pkg_meta(path):
    """从 .cwplugin（本质是 zip）里读 cwplugin.json。"""
    with zipfile.ZipFile(path) as z:
        for nm in z.namelist():
            if nm.endswith("cwplugin.json") and nm.count("/") <= 1:
                return json.loads(z.read(nm).decode("utf-8"))
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=".", help="扫描 *.cwplugin 的目录")
    ap.add_argument("--tag", default="", help="GitHub Release 标签，如 v1.3.3.20260916")
    ap.add_argument("--features", default="tools/features.json")
    ap.add_argument("--out", default="manifest.json")
    ap.add_argument("--base-url", default="", help="覆盖默认下载地址前缀")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    feat_path = root / args.features
    policy = json.loads(feat_path.read_text(encoding="utf-8"))
    repo = policy["installer"]["repo"]

    out_path = root / args.out
    if out_path.exists():
        manifest = json.loads(out_path.read_text(encoding="utf-8"))
    else:
        manifest = {"schema": policy.get("schema", 1), "installer": {},
                    "features": []}

    # 现有版本索引：feature id -> {version: entry}
    index = {}
    for f in manifest.get("features", []):
        index[f["id"]] = {v["version"]: v for v in f.get("versions", [])}

    scan_dir = pathlib.Path(args.dir)
    found = {}
    for pkg in sorted(scan_dir.rglob("*.cwplugin")):
        meta = read_pkg_meta(pkg)
        pid, ver = meta.get("id"), meta.get("version")
        if not pid or not ver:
            print(f"  跳过（缺少 id/version）: {pkg.name}")
            continue
        found[pid] = (pkg, ver)

    print(f"扫描到 {len(found)} 个包：")
    for pid, (pkg, ver) in found.items():
        print(f"  {pid:<34} {ver:<20} {pkg.name}")

    # 组装 features
    new_features = []
    matched = set()
    for pol in policy.get("features", []):
        fid = pol["id"]
        entry = {
            "id": fid,
            "name": pol.get("name", fid),
            "summary": pol.get("summary", ""),
            "patches": pol.get("patches", []),
            "cw2_min": pol.get("cw2_min"),
            "cw2_max": pol.get("cw2_max"),
            "versions": [],
        }
        versions = dict(index.get(fid, {}))
        if fid in found:
            pkg, ver = found[fid]
            matched.add(fid)
            url = args.base_url or (
                f"https://github.com/{repo}/releases/download/{args.tag}/{pkg.name}"
                if args.tag else "")
            old = versions.get(ver)
            if old and old.get("sha256") == sha256_of(pkg):
                # 同一个版本、同一份文件 → 保留原条目（含 tested 状态和人工备注）
                versions[ver] = old
                print(f"  保持原条目: {fid} {ver} (tested={old.get('tested')})")
            else:
                versions[ver] = {
                    "version": ver,
                    "tested": False,          # 新构建一律先标未测试
                    "note": "",
                    "asset": url,
                    "size": pkg.stat().st_size,
                    "sha256": sha256_of(pkg),
                }
                print(f"  新增/更新条目: {fid} {ver} (tested=False)")
        elif not versions:
            print(f"  注意: 功能 {fid} 没有对应的包，清单里保留空 versions")
        else:
            print(f"  未找到 {fid} 的新构建，沿用已有 {len(versions)} 个版本条目")

        entry["versions"] = sorted(versions.values(),
                                   key=lambda v: cw_key(v["version"]))
        new_features.append(entry)

    manifest["schema"] = policy.get("schema", 1)
    manifest["updated"] = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    manifest["installer"] = {
        "repo": repo,
        "min_cw2": policy["installer"].get("min_cw2"),
    }
    manifest["features"] = new_features

    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(f"\n已写出 {out_path}")
    print(f"  功能 {len(new_features)} 个，"
          f"版本条目 {sum(len(f['versions']) for f in new_features)} 条")

    unmatched = set(found) - matched
    if unmatched:
        print("\n以下包在 features.json 里没有对应功能，未写进清单：")
        for u in unmatched:
            print(f"  {u}  → 请在 tools/features.json 里加一条 id 为 {u} 的功能")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
