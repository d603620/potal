# app/services/license_fetch_service.py
from __future__ import annotations

import base64
import os
from typing import Optional

import requests
from fastapi import HTTPException


class LicenseNotFoundError(Exception):
    """ライセンス情報が取得できなかったことを表すエラー"""
    pass


def _fetch_from_github(repo: str) -> Optional[str]:
    """
    GitHub のリポジトリから LICENSE テキストを取得する。
    repo: "owner/repo" 形式を想定
    """
    if "/" not in repo:
        return None

    url = f"https://api.github.com/repos/{repo}/license"
    headers = {}

    # レートリミット回避用に GitHub Token を使えるようにしておく（任意）
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        return None

    data = resp.json()
    content = data.get("content")
    if not content:
        return None

    try:
        decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
        return decoded
    except Exception:
        return None


def _fetch_from_npm(package_name: str) -> Optional[str]:
    """
    npm パッケージのメタ情報から license フィールドを取得しにいく。
    ※ ライセンス本文ではなく SPDX 名称になる場合が多い点に注意。
    """
    url = f"https://registry.npmjs.org/{package_name}"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return None

    data = resp.json()
    latest = data.get("dist-tags", {}).get("latest")
    if not latest:
        return None

    latest_info = data.get("versions", {}).get(latest, {})
    license_field = latest_info.get("license") or latest_info.get("licenses")
    if isinstance(license_field, str):
        return f"License: {license_field}"
    if isinstance(license_field, list):
        return " / ".join(str(x) for x in license_field)

    return None


def _fetch_from_pypi(package_name: str) -> Optional[str]:
    """
    PyPI パッケージからライセンス情報を取得（こちらも本文ではなくメタデータ寄り）。
    """
    url = f"https://pypi.org/pypi/{package_name}/json"
    resp = requests.get(url, timeout=10)
    if resp.status_code != 200:
        return None

    data = resp.json()
    info = data.get("info", {})
    license_field = info.get("license")
    if license_field:
        return f"License: {license_field}"

    classifiers = info.get("classifiers", [])
    license_classifiers = [
        c for c in classifiers if c.startswith("License ::")
    ]
    if license_classifiers:
        return "\n".join(license_classifiers)

    return None


def fetch_license_text_from_web(software_name: str) -> str:
    """
    ソフトウェア名からライセンステキスト（または少なくともライセンス情報）を
    いくつかの手段で取得する。

    - "owner/repo" 形式なら GitHub を優先
    - それ以外は npm / PyPI を順番に試す（※必要に応じて拡張）
    """
    name = (software_name or "").strip()
    if not name:
        raise HTTPException(
            status_code=400,
            detail="ライセンステキストが空の場合は、ソフトウェア名の指定が必要です。",
        )

    # 1. GitHub リポジトリとして解釈 ("owner/repo")
    text = _fetch_from_github(name)
    if text:
        return text

    # 2. npm パッケージ名として試す
    text = _fetch_from_npm(name)
    if text:
        return text

    # 3. PyPI パッケージ名として試す
    text = _fetch_from_pypi(name)
    if text:
        return text

    # ここまで取得できなければ 404 扱い
    raise HTTPException(
        status_code=404,
        detail=f"ソフトウェア名 '{software_name}' からライセンス情報を取得できませんでした。",
    )
