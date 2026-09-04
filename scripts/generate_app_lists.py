#!/usr/bin/env python3
"""Generate privacy app-list HTML from apps.txt (working memo)."""

from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPS_FILE = ROOT / "apps.txt"
EXAMPLE_FILE = ROOT / "apps.example.txt"


def default_policy(ads: str) -> str:
    return "ads.html" if ads == "yes" else "no-ads.html"


def load_apps(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"{path.name} がありません。\n"
            f"  cp {EXAMPLE_FILE.name} {path.name}\n"
            f"で作成してから再実行してください。"
        )

    apps: list[dict] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = raw.split("\t") if "\t" in raw else re.split(r"\s{2,}", raw.strip())
        if len(parts) < 3:
            raise SystemExit(f"{path.name}:{lineno}: 列が足りません → {raw!r}")
        platform, ads, name = parts[0].strip(), parts[1].strip(), parts[2].strip()
        app_id = parts[3].strip() if len(parts) > 3 else "-"
        policy = parts[4].strip() if len(parts) > 4 and parts[4].strip() else default_policy(ads)
        if platform not in {"android", "ios"}:
            raise SystemExit(f"{path.name}:{lineno}: platform は android/ios → {platform!r}")
        if ads not in {"yes", "no"}:
            raise SystemExit(f"{path.name}:{lineno}: ads は yes/no → {ads!r}")
        apps.append(
            {
                "platform": platform,
                "ads": ads,
                "name": name,
                "id": app_id,
                "policy": policy,
            }
        )
    if not apps:
        raise SystemExit(f"{path.name}: アプリが1件もありません")
    return apps


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def display_id(app_id: str) -> str:
    return "—" if app_id in {"", "-", "—"} else app_id


def policy_label(policy: str, *, ads_label: str, no_ads_label: str, dedicated_label: str) -> str:
    if policy == "ads.html":
        return ads_label
    if policy == "no-ads.html":
        return no_ads_label
    return dedicated_label


def table_rows(
    apps: list[dict],
    *,
    ads_label: str,
    no_ads_label: str,
    dedicated_label: str,
) -> str:
    rows = []
    for app in apps:
        app_id = display_id(app["id"])
        id_html = f"<code>{esc(app_id)}</code>" if app_id != "—" else "—"
        label = policy_label(
            app["policy"],
            ads_label=ads_label,
            no_ads_label=no_ads_label,
            dedicated_label=dedicated_label,
        )
        policy = f'<a href="{esc(app["policy"])}">{esc(label)}</a>'
        rows.append(
            "    <tr>\n"
            f"      <td>{esc(app['name'])}</td>\n"
            f"      <td>{id_html}</td>\n"
            f"      <td>{policy}</td>\n"
            "    </tr>"
        )
    return "\n".join(rows) + ("\n" if rows else "")


def list_items(
    apps: list[dict],
    *,
    id_label: str,
    empty_text: str,
    compact: bool = False,
) -> str:
    if not apps:
        return f"  <li>{esc(empty_text)}</li>\n"
    items = []
    for app in apps:
        app_id = display_id(app["id"])
        if compact or app_id == "—":
            items.append(f"  <li><strong>{esc(app['name'])}</strong></li>")
        else:
            items.append(
                "  <li>\n"
                f"    <strong>{esc(app['name'])}</strong><br>\n"
                f"    {esc(id_label)}: <code>{esc(app_id)}</code>\n"
                "  </li>"
            )
    return "\n".join(items) + "\n"


def replace_block(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- BEGIN:{re.escape(name)} -->\n)(.*?)(<!-- END:{re.escape(name)} -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"マーカーが見つかりません: <!-- BEGIN:{name} -->")
    return pattern.sub(rf"\1{body}\3", text)


def update_file(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for name, body in replacements.items():
        text = replace_block(text, name, body)
    path.write_text(text, encoding="utf-8")
    print(f"updated: {path.relative_to(ROOT)}")


def main() -> None:
    apps = load_apps(APPS_FILE)
    android = [a for a in apps if a["platform"] == "android"]
    ios = [a for a in apps if a["platform"] == "ios"]
    # Shared policy pages only list apps that still point to them.
    android_ads = [a for a in android if a["policy"] == "ads.html"]
    android_no = [a for a in android if a["policy"] == "no-ads.html"]
    ios_ads = [a for a in ios if a["policy"] == "ads.html"]
    ios_no = [a for a in ios if a["policy"] == "no-ads.html"]

    index = ROOT / "privacy" / "index.html"
    update_file(
        index,
        {
            "ANDROID_APPS_JA": table_rows(
                android,
                ads_label="広告あり版",
                no_ads_label="広告なし版",
                dedicated_label="専用ポリシー",
            ),
            "IOS_APPS_JA": table_rows(
                ios,
                ads_label="広告あり版",
                no_ads_label="広告なし版",
                dedicated_label="専用ポリシー",
            ),
            "ANDROID_APPS_EN": table_rows(
                android,
                ads_label="With ads",
                no_ads_label="No ads",
                dedicated_label="Dedicated policy",
            ),
            "IOS_APPS_EN": table_rows(
                ios,
                ads_label="With ads",
                no_ads_label="No ads",
                dedicated_label="Dedicated policy",
            ),
        },
    )

    ads = ROOT / "privacy" / "ads.html"
    update_file(
        ads,
        {
            "ADS_ANDROID_EN": list_items(
                android_ads, id_label="Package name", empty_text="None"
            ),
            "ADS_IOS_EN": list_items(
                ios_ads, id_label="Bundle ID", empty_text="None"
            ),
            "ADS_ANDROID_JA": list_items(
                android_ads, id_label="パッケージ名", empty_text="該当なし"
            ),
            "ADS_IOS_JA": list_items(
                ios_ads, id_label="Bundle ID", empty_text="該当なし"
            ),
        },
    )

    no_ads = ROOT / "privacy" / "no-ads.html"
    update_file(
        no_ads,
        {
            "NOADS_ANDROID_EN": list_items(
                android_no, id_label="Package name", empty_text="None", compact=True
            ),
            "NOADS_IOS_EN": list_items(
                ios_no, id_label="Bundle ID", empty_text="None"
            ),
            "NOADS_ANDROID_JA": list_items(
                android_no, id_label="パッケージ名", empty_text="該当なし", compact=True
            ),
            "NOADS_IOS_JA": list_items(
                ios_no, id_label="Bundle ID", empty_text="該当なし"
            ),
        },
    )

    dedicated = [a for a in apps if a["policy"] not in {"ads.html", "no-ads.html"}]
    print(
        f"done: android={len(android)} ios={len(ios)} "
        f"shared_ads={len(android_ads)+len(ios_ads)} "
        f"shared_noads={len(android_no)+len(ios_no)} "
        f"dedicated={len(dedicated)}"
    )


if __name__ == "__main__":
    main()
