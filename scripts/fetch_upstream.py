"""Developer helper for fetching the supported ORAEC source snapshot."""

from __future__ import annotations

import argparse

from oraec_tf.source import DEFAULT_SOURCE_REVISION, fetch_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination")
    parser.add_argument("--revision", default=DEFAULT_SOURCE_REVISION)
    args = parser.parse_args()

    snapshot = fetch_source(args.destination, revision=args.revision)
    print(f"{snapshot.revision}\t{snapshot.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
