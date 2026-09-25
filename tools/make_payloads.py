#!/usr/bin/env python3
"""把 features_src/<功能 id>/ 打成可分发的 payload 文件，并同步 manifest.json。

payload 是一个普通 zip（**不含 cwplugin.json**），里面有：
    payload.json     功能元数据（id / name / version / entry / resources）
    feature.py       入口，实现 on_load(host) / on_unload(host)
    ...              以及 payload.json 里 resources 声明的资源文件

主程序的插件扫描只认带 cwplugin.json 的目录，所以 payload 不会被当成插件 ——
这正是「装了什么不在插件列表里显示」的实现方式。

确定性（重要）：zip 内所有条目的时间戳统一固定为 1980-01-01，同样的源码永远
产出同样的字节和同样的 sha256。这样本地生成的 manifest.json 提交进仓库后，
CI 重新构建也能对得上，不会出现「本地算的 hash 与发布产物不一致」的问题。

用法（在仓库根目录执行）：

    # 1) 正式流程：本地生成 payload 并更新 manifest.json，然后把 manifest.json 提交
    python tools/make_payloads.py --out-dir dist --tag v1.3.3.20260916

    # 2) CI 里校验：已提交的 manifest.json 是否与本次构建产物一致（不一致就报错退出）
    python tools/make_payloads.py --out-dir dist --tag v1.3.3.20260916 --check

    # 3) 发布正式版、确认过可用时，加 --tested 把新条目标成已测试
    python tools/make_payloads.py --out-dir dist --tag v1.3.3.20260916 --tested
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import sys
import zipfile

# zip 内统一的固定时间戳：保证构建可复现（同源码 → 同字节 → 同 sha256）
_FIXED_DT = (1980, 1, 1, 0, 0, 0)

# 发行版附件下载地址模板；features.json 里的同名字段可覆盖。
# Gitee 与 GitHub 的格式不同，所以做成模板而不是写死一家。
_DEFAULT_ASSET_URL = "https://github.com/{repo}/releases/download/{tag}/{name}"


def cw_key(v):
    """把版本串转成可排序的键。

    主程序版本既可能是 2.0.0.dev20260923（PEP 440 合法），也可能是裸日期串；
    功能版本用 1.3.3.20260916 这类四段式。优先 PEP 440，失败再退回日期/字符串。
    """
    s = str(v or "").strip()
    if s:
        try:
            from packaging.version import Version

            return (0, Version(s))
        except Exception:
            pass
    m = re.search(r"(\d{8})", s)
    if m:
        return (2, int(m.group(1)))
    return (3, s)


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plugin_version(root: pathlib.Path) -> str:
    try:
        data = json.loads((root / "cwplugin.json").read_text(encoding="utf-8"))
        return str(data.get("version", "")).strip()
    except Exception:
        return ""


def add_bytes(zf: zipfile.ZipFile, name: str, data: bytes):
    zi = zipfile.ZipInfo(name, date_time=_FIXED_DT)
    zi.compress_type = zipfile.ZIP_DEFLATED
    zi.external_attr = 0o644 << 16
    zf.writestr(zi, data)


def build_payload(root: pathlib.Path, feature: dict, out_dir: pathlib.Path):
    """按 features_src/<id>/ 打一个 payload。返回 (路径, sha256, 版本, 元数据)。"""
    fid = feature["id"]
    src = root / "features_src" / fid
    if not src.is_dir():
        raise FileNotFoundError(f"缺少 payload 源目录: features_src/{fid}")

    meta_path = src / "payload.json"
    if not meta_path.is_file():
        raise FileNotFoundError(f"缺少 payload.json: features_src/{fid}/payload.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    if str(meta.get("id", "")).strip() != fid:
        raise ValueError(
            f"features_src/{fid}/payload.json 里的 id 是 {meta.get('id')!r}，与 features.json 的 {fid!r} 不一致")

    version = str(meta.get("version") or "").strip() or plugin_version(root)
    if not version:
        raise ValueError(f"{fid}: 拿不到版本号（payload.json 没写，插件也没写）")
    meta["version"] = version

    entry = str(meta.get("entry") or "feature.py")
    if not (src / entry).is_file():
        raise FileNotFoundError(f"{fid}: 入口文件不存在 features_src/{fid}/{entry}")

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{fid}-{version}.cwpayload"

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        # payload.json 放最外层：导入时要先读到它才知道这是什么功能
        add_bytes(zf, "payload.json",
                  json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))
        add_bytes(zf, entry, (src / entry).read_bytes())

        # 资源文件从仓库里拷贝（声明 dest -> src，src 相对仓库根，避免资源存两份）
        for dest_rel, src_rel in (meta.get("resources") or {}).items():
            sp = root / str(src_rel)
            if not sp.is_file():
                raise FileNotFoundError(f"{fid}: 资源缺失 {src_rel}")
            add_bytes(zf, str(dest_rel), sp.read_bytes())

    return out, sha256_of(out), version, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="dist", help="payload 输出目录")
    ap.add_argument("--tag", default="", help="GitHub Release 标签，如 v1.3.3.20260916")
    ap.add_argument("--features", default="tools/features.json")
    ap.add_argument("--manifest", default="manifest.json")
    ap.add_argument("--repo", default="", help="覆盖 features.json 里的仓库（owner/repo）")
    ap.add_argument("--tested", action="store_true",
                    help="把本次新增的版本条目标为已测试")
    ap.add_argument("--check", action="store_true",
                    help="只校验：已提交的 manifest.json 是否与本次构建一致，不一致就退出码 1")
    args = ap.parse_args()

    root = pathlib.Path(__file__).resolve().parent.parent
    policy = json.loads((root / args.features).read_text(encoding="utf-8"))
    repo = args.repo or policy["installer"]["repo"]
    out_dir = (root / args.out_dir) if not pathlib.Path(args.out_dir).is_absolute() \
        else pathlib.Path(args.out_dir)

    manifest_path = root / args.manifest
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.exists() else {"schema": 1, "features": []}

    index = {f["id"]: {v["version"]: v for v in f.get("versions", [])}
             for f in manifest.get("features", [])}

    # 只处理声明了 payload 的功能；其余（如插件本体）不属于 payload 体系
    targets = [f for f in policy.get("features", []) if f.get("payload")]
    if not targets:
        print("features.json 里没有标记 \"payload\": true 的功能，无事可做")
        return 0

    built = {}
    problems = []
    for feat in targets:
        fid = feat["id"]
        try:
            path, digest, version, meta = build_payload(root, feat, out_dir)
        except Exception as e:
            problems.append(f"{fid}: 构建失败 — {e}")
            print(f"  !! {fid}: {e}")
            continue
        built[fid] = (path, digest, version, meta)
        print(f"  OK  {fid:<26} {version:<18} {path.stat().st_size:>9,} 字节  {digest[:12]}…")

    if args.check:
        print("\n校验已提交的 manifest.json：")
        bad = 0
        for fid, (path, digest, version, meta) in built.items():
            old = index.get(fid, {}).get(version)
            if not old:
                print(f"  !! {fid} {version}: manifest.json 里没有这个版本条目")
                bad += 1
            elif str(old.get("sha256", "")).lower() != digest.lower():
                print(f"  !! {fid} {version}: sha256 不一致")
                print(f"       清单: {old.get('sha256')}")
                print(f"       本次: {digest}")
                bad += 1
            else:
                print(f"  OK  {fid} {version}")
        if bad or problems:
            print(f"\n共 {bad + len(problems)} 处不一致。"
                  f"请先在本地跑一次 make_payloads.py 并把 manifest.json 提交。")
            return 1
        print("\n清单与构建产物一致")
        return 0

    # 组装 manifest：人工维护的字段以 features.json 为准，脚本只填算得出来的
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
        if fid in built:
            path, digest, version, _meta = built[fid]
            matched.add(fid)
            tpl = (policy["installer"].get("asset_url_template")
                   or _DEFAULT_ASSET_URL)
            url = tpl.format(repo=repo, tag=args.tag, name=path.name) \
                if args.tag else ""
            old = versions.get(version)
            if old and str(old.get("sha256", "")).lower() == digest.lower():
                # 同一份文件：保留原条目（含 tested 状态和人工备注），只补地址
                old["asset"] = url or old.get("asset", "")
                versions[version] = old
                print(f"  保持原条目: {fid} {version} (tested={old.get('tested')})")
            else:
                versions[version] = {
                    "version": version,
                    "tested": bool(args.tested),
                    "note": "",
                    "asset": url,
                    "size": path.stat().st_size,
                    "sha256": digest,
                }
                print(f"  {'新增' if not old else '更新'}条目: {fid} {version} "
                      f"(tested={bool(args.tested)})")
        elif not versions:
            print(f"  注意: 功能 {fid} 没有 payload 产物，清单里保留空 versions")
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
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\n已写出 {manifest_path}")
    print(f"  功能 {len(new_features)} 个，"
          f"版本条目 {sum(len(f['versions']) for f in new_features)} 条")

    unmatched = set(built) - matched
    if unmatched:
        print("\n以下 payload 在 features.json 里没有对应条目：")
        for u in sorted(unmatched):
            print(f"  {u}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
