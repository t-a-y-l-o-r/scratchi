#!/usr/bin/env python3
"""Generate random samples from out.txt file.

Creates n samples of 100 lines each from an existing out.txt file.
Each sample starts at a random position in the file.

Usage:
    python scripts/generate_samples.py [--num-samples N] [--sample-size SIZE]
"""

import argparse
import random
import sys
from pathlib import Path


def generate_samples(
    input_file: Path,
    output_dir: Path,
    num_samples: int,
    sample_size: int = 100,
) -> None:
    """Generate random samples from input file.

    Args:
        input_file: Path to input file (out.txt)
        output_dir: Directory to write sample files
        num_samples: Number of samples to generate
        sample_size: Number of lines per sample
    """
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # Read all lines from input file
    with input_file.open(encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)
    print(f"Input file has {total_lines} lines")

    if total_lines < sample_size:
        print(
            f"Error: Input file has {total_lines} lines, but sample size is {sample_size}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Calculate maximum start position
    max_start = total_lines - sample_size

    # Generate samples
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, num_samples + 1):
        # Choose random start position
        start_pos = random.randint(0, max_start)
        end_pos = start_pos + sample_size

        # Extract sample lines
        sample_lines = lines[start_pos:end_pos]

        # Write to output file
        output_file = output_dir / f"sample{i}-out.txt"
        with output_file.open("w", encoding="utf-8") as f:
            f.writelines(sample_lines)

        print(f"Created {output_file.name} (lines {start_pos + 1}-{end_pos})")

    print(f"\nGenerated {num_samples} sample files in {output_dir}")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate random samples from out.txt file",
    )
    parser.add_argument(
        "--num-samples",
        type=int,
        default=5,
        help="Number of samples to generate (default: 5)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=100,
        help="Number of lines per sample (default: 100)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/out.txt"),
        help="Input file path (default: data/out.txt)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for samples (default: data)",
    )

    args = parser.parse_args()

    generate_samples(
        input_file=args.input,
        output_dir=args.output_dir,
        num_samples=args.num_samples,
        sample_size=args.sample_size,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
