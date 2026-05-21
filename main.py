#!/usr/bin/env python3

import argparse
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from openai import OpenAI

META_RE = re.compile(r"^@(instructions|voice|speed|format|model|prefix)\s*:\s*(.*)$")
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
OVERRIDABLE = {"instructions", "voice", "speed", "format", "model", "prefix"}
print_lock = Lock()


def safe_print(*args, **kwargs):
    with print_lock:
        print(*args, **kwargs, flush=True)


def strip_comments(text: str) -> str:
    return COMMENT_RE.sub("", text)


def split_segments(text: str) -> list[str]:
    segments, current = [], []
    for line in text.splitlines():
        if line.strip() == "---":
            chunk = "\n".join(current).strip()
            if chunk:
                segments.append(chunk)
            current = []
        else:
            current.append(line)
    chunk = "\n".join(current).strip()
    if chunk:
        segments.append(chunk)
    return segments


def parse_meta(segment: str) -> tuple[dict, str]:
    meta = {}
    lines = segment.splitlines()
    idx = 0
    for line in lines:
        m = META_RE.match(line.strip())
        if not m:
            break
        meta[m.group(1)] = m.group(2).strip()
        idx += 1
    body = "\n".join(lines[idx:]).strip()
    return meta, body


def generate_one(
    client: OpenAI,
    idx: int,
    total: int,
    raw: str,
    defaults: dict,
    output_dir: Path,
    width: int,
) -> bool:
    meta, body = parse_meta(raw)
    if not body:
        safe_print(f"[{idx}/{total}] skipped: empty body", file=sys.stderr)
        return True

    cfg = {**defaults, **{k: v for k, v in meta.items() if k in OVERRIDABLE}}
    cfg["speed"] = float(cfg["speed"])

    out_path = output_dir / f"{cfg['prefix']}_{idx:0{width}d}.{cfg['format']}"
    preview = body.replace("\n", " ")[:40]
    safe_print(
        f"[{idx}/{total}] voice={cfg['voice']} -> {out_path.name}  ({preview}...)"
    )

    try:
        kwargs = dict(
            model=cfg["model"],
            voice=cfg["voice"],
            input=body,
            response_format=cfg["format"],
            speed=cfg["speed"],
        )
        if cfg.get("instructions"):
            kwargs["instructions"] = cfg["instructions"]
        with client.audio.speech.with_streaming_response.create(**kwargs) as resp:
            resp.stream_to_file(out_path)
        safe_print(f"[{idx}/{total}] done -> {out_path.name}")
        return True
    except Exception as e:
        safe_print(f"[{idx}/{total}] failed: {e}", file=sys.stderr)
        return False


def main() -> int:
    p = argparse.ArgumentParser(description="Read my Markdown file(s) aloud")
    p.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Specify the location of the Markdown file to be read",
    )
    p.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Specify the save location for the output audio file (default: current working directory)",
    )
    p.add_argument(
        "-u",
        "--api-url",
        required=True,
        help="Specify the Base URL for the OpenAI-compatible API format",
    )
    p.add_argument(
        "-k",
        "--api-key",
        required=True,
        help="Specify the API key to use when calling the API",
    )
    p.add_argument(
        "-m",
        "--model",
        required=True,
        help="Specify the model to use when calling the API",
    )
    p.add_argument(
        "--voice",
        default="alloy",
        help="Specify the sound used when calling the API (default: alloy).",
    )
    p.add_argument(
        "--format",
        default="mp3",
        choices=["mp3", "opus", "aac", "flac", "wav", "pcm"],
        help="Specify the format of the saved audio files (supported: mp3 opus aac flac wav pcm) (default: mp3).",
    )
    p.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Specify the reading speed (default: 1.0).",
    )
    p.add_argument(
        "--instructions",
        default="",
        help="Specify style prompts for text-to-speech.",
    )
    p.add_argument(
        "--prefix",
        default="tts",
        help="Specify the prefix for saved audio files.",
    )
    p.add_argument(
        "-w",
        "--workers",
        type=int,
        default=4,
        help="Specify the number of concurrent requests (default: 4).",
    )
    args = p.parse_args()

    if not args.input.is_file():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1
    if args.input.suffix.lower() != ".md":
        print(
            f"Warning: input file is not .md (got {args.input.suffix}); "
            f"continuing anyway, but Markdown comment syntax is expected.",
            file=sys.stderr,
        )
    if args.workers < 1:
        print("error: --workers must be >= 1", file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw_text = args.input.read_text(encoding="utf-8")
    cleaned = strip_comments(raw_text)
    segments = split_segments(cleaned)
    if not segments:
        print("Error: no non-empty segments found", file=sys.stderr)
        return 1

    client = OpenAI(base_url=args.api_url, api_key=args.api_key)
    defaults = {
        "model": args.model,
        "voice": args.voice,
        "speed": args.speed,
        "format": args.format,
        "prefix": args.prefix,
        "instructions": args.instructions,
    }

    total = len(segments)
    width = len(str(total))
    failed = 0

    safe_print(f"start: {total} segments, {args.workers} workers")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(
                generate_one, client, idx, total, raw, defaults, args.output_dir, width
            )
            for idx, raw in enumerate(segments, start=1)
        ]
        for fut in as_completed(futures):
            if not fut.result():
                failed += 1

    safe_print(f"done. success={total - failed} failed={failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
