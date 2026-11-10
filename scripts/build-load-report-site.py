#!/usr/bin/env python3
"""Build and merge sanitized static load-test report bundles."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from typing import Any

RUN_KEY_PATTERN = re.compile(r"^[0-9]+-[0-9]+-[0-9a-f]{7}$")
PRESET_PATTERN = re.compile(r"^[a-z0-9_]+$")


def load_metadata(path: Path) -> dict[str, Any]:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "commit_sha",
        "environment",
        "github_run_url",
        "preset",
        "recorded_at_utc",
        "run_key",
        "run_note",
        "test_ended_at_utc",
        "test_started_at_utc",
    }
    missing = sorted(required.difference(metadata))
    if missing:
        raise ValueError(f"Missing metadata fields: {', '.join(missing)}")
    if not RUN_KEY_PATTERN.fullmatch(str(metadata["run_key"])):
        raise ValueError("Invalid run_key")
    if not PRESET_PATTERN.fullmatch(str(metadata["preset"])):
        raise ValueError("Invalid preset")
    return metadata


def page_template(title: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }}
    body {{
      margin: 0 auto;
      max-width: 1440px;
      padding: 2rem;
      line-height: 1.5;
    }}
    a {{ color: #2f9e7a; }}
    .metadata, .report {{
      border: 1px solid #8491a3;
      border-radius: 12px;
      padding: 1rem 1.25rem;
      margin: 1rem 0;
    }}
    .dashboard {{
      display: block;
      width: 100%;
      height: auto;
      border: 1px solid #8491a3;
      border-radius: 12px;
      margin: 1rem 0 2rem;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      border-bottom: 1px solid #8491a3;
      padding: .65rem;
      text-align: left;
      vertical-align: top;
    }}
    code {{ overflow-wrap: anywhere; }}
  </style>
</head>
<body>
{content}
</body>
</html>
"""


def build_bundle(run_dir: Path, output_dir: Path) -> None:
    metadata = load_metadata(run_dir / "metadata.json")
    required_files = (
        "report.html",
        "grafana-application.png",
        "grafana-infrastructure.png",
        "metadata.json",
    )
    missing = [name for name in required_files if not (run_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing report files: {', '.join(missing)}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    for name in required_files:
        shutil.copy2(run_dir / name, output_dir / name)

    title = f"Zipp load test: {metadata['preset']}"
    environment = html.escape(str(metadata["environment"]))
    commit_sha = html.escape(str(metadata["commit_sha"]))
    github_run_url = html.escape(str(metadata["github_run_url"]), quote=True)
    content = f"""
  <p><a href="../../index.html">&larr; All load-test runs</a></p>
  <h1>{html.escape(title)}</h1>
  <section class="metadata">
    <p><strong>Run note:</strong> {html.escape(str(metadata["run_note"]))}</p>
    <p><strong>Environment:</strong> <code>{environment}</code></p>
    <p>
      <strong>Started:</strong>
      {html.escape(str(metadata["test_started_at_utc"]))}
    </p>
    <p>
      <strong>Finished:</strong>
      {html.escape(str(metadata["test_ended_at_utc"]))}
    </p>
    <p><strong>Commit:</strong> <code>{commit_sha}</code></p>
    <p><a href="{github_run_url}">GitHub Actions run</a></p>
  </section>
  <section class="report">
    <h2>Locust report</h2>
    <p><a href="report.html">Open the native Locust HTML report</a></p>
  </section>
  <h2>Application metrics</h2>
  <a href="grafana-application.png">
    <img class="dashboard" src="grafana-application.png"
         alt="Grafana application dashboard">
  </a>
  <h2>Infrastructure metrics</h2>
  <a href="grafana-infrastructure.png">
    <img class="dashboard" src="grafana-infrastructure.png"
         alt="Grafana infrastructure dashboard">
  </a>
  """
    (output_dir / "index.html").write_text(
        page_template(title, content), encoding="utf-8"
    )


def merge_bundle(bundle_dir: Path, site_dir: Path) -> None:
    metadata = load_metadata(bundle_dir / "metadata.json")
    run_key = str(metadata["run_key"])
    preset = str(metadata["preset"])
    runs_dir = site_dir / "runs"
    latest_dir = site_dir / "latest" / preset
    destination = runs_dir / run_key

    if destination.exists():
        raise FileExistsError(f"Run already exists in report history: {run_key}")
    runs_dir.mkdir(parents=True, exist_ok=True)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle_dir, destination)
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    latest_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle_dir, latest_dir)

    reports: list[dict[str, Any]] = []
    for metadata_path in runs_dir.glob("*/metadata.json"):
        report = load_metadata(metadata_path)
        reports.append(report)
    reports.sort(key=lambda item: str(item["recorded_at_utc"]), reverse=True)

    rows = []
    for report in reports:
        key = html.escape(str(report["run_key"]), quote=True)
        run_url = html.escape(str(report["github_run_url"]), quote=True)
        preset = html.escape(str(report["preset"]))
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(report['recorded_at_utc']))}</td>"
            f'<td><a href="runs/{key}/index.html">{preset}</a></td>'
            f"<td>{html.escape(str(report['run_note']))}</td>"
            f"<td><code>{html.escape(str(report['commit_sha']))[:7]}</code></td>"
            f'<td><a href="{run_url}">Actions</a></td>'
            "</tr>"
        )

    content = f"""
  <h1>Zipp performance reports</h1>
  <p>
    Version-controlled history of GitHub-triggered Locust runs against the
    EC2-hosted k3s environment.
  </p>
  <table>
    <thead>
      <tr>
        <th>Recorded</th><th>Preset</th><th>Run note</th>
        <th>Commit</th><th>Workflow</th>
      </tr>
    </thead>
    <tbody>{"".join(rows)}</tbody>
  </table>
  """
    (site_dir / "index.html").write_text(
        page_template("Zipp performance reports", content), encoding="utf-8"
    )
    (site_dir / ".nojekyll").touch()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    bundle = subparsers.add_parser("bundle")
    bundle.add_argument("--run-dir", type=Path, required=True)
    bundle.add_argument("--output-dir", type=Path, required=True)

    merge = subparsers.add_parser("merge")
    merge.add_argument("--bundle-dir", type=Path, required=True)
    merge.add_argument("--site-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "bundle":
        build_bundle(args.run_dir, args.output_dir)
    else:
        merge_bundle(args.bundle_dir, args.site_dir)


if __name__ == "__main__":
    main()
