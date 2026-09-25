#!/usr/bin/env python3
"""把 dist/ 里的 .cwpayload 传到 Gitee 发行版。

为什么不直接在流水线里写 curl：Gitee 的接口要两步（先建发行版拿 id，
再往 /releases/<id>/attach_files 传附件），而且重跑要能复用已有的发行版。
写成脚本既能被流水线调用，也能本地手动跑一次。

用法：

    set GITEE_TOKEN=你的私人令牌
    python tools/gitee_release.py --owner kryonF --repo more_-settings-features \
        --tag v1.3.3.20260916 --dist dist

只依赖标准库。Gitee 的 tag 名称里带点号是允许的。
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://gitee.com/api/v5"
TIMEOUT = 120


def _get(url: str, token: str):
    """GET，404 返回 None（用来判断发行版是否已存在）。"""
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(f"{url}{sep}access_token={urllib.parse.quote(token)}")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _post_form(url: str, fields: dict, token: str) -> dict:
    data = urllib.parse.urlencode({**fields, "access_token": token}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _post_file(url: str, filename: str, content: bytes, token: str) -> dict:
    """手搓 multipart —— 只为少一个 requests 依赖。"""
    boundary = "----cwpayload" + os.urandom(8).hex()
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="access_token"\r\n\r\n'
        f"{token}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    body = head + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--tag", required=True, help="如 v1.3.3.20260916")
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--branch", default="main", help="发行版指向的分支")
    ap.add_argument("--token", default=os.environ.get("GITEE_TOKEN", ""),
                    help="默认取环境变量 GITEE_TOKEN")
    args = ap.parse_args()

    if not args.token:
        print("缺少令牌：设环境变量 GITEE_TOKEN，或用 --token 传入。")
        print("（Gitee 个人设置 -> 私人令牌，勾 projects 权限）")
        return 2

    dist = pathlib.Path(args.dist)
    files = sorted(dist.glob("*.cwpayload"))
    if not files:
        print(f"{dist}/ 里没有 .cwpayload —— 先跑 make_payloads.py")
        return 1

    base = f"{API}/repos/{args.owner}/{args.repo}"

    rel = _get(f"{base}/releases/tags/{args.tag}", args.token)
    if rel:
        print(f"发行版 {args.tag} 已存在，复用它（id={rel['id']}）")
    else:
        rel = _post_form(f"{base}/releases", {
            "tag_name": args.tag,
            "name": args.tag,
            "target_commitish": args.branch,
        }, args.token)
        print(f"已创建发行版 {args.tag}（id={rel['id']}）")

    # 附件同名就跳过，重复跑不会堆出一串重复文件
    existing = set()
    for a in (rel.get("assets") or []):
        name = a.get("name") or a.get("title") or ""
        if name:
            existing.add(str(name))

    failed = 0
    for f in files:
        if f.name in existing:
            print(f"  跳过（已在上）{f.name}")
            continue
        try:
            _post_file(f"{base}/releases/{rel['id']}/attach_files",
                       f.name, f.read_bytes(), args.token)
            print(f"  已上传 {f.name}（{f.stat().st_size:,} 字节）")
        except Exception as e:
            print(f"  !! 上传失败 {f.name}: {e}")
            failed += 1

    if failed:
        print(f"\n{failed} 个文件没传上去。")
        return 1
    print("\n完成。记得确认 manifest.json 已在仓库里（插件就是读它找这些包的）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
