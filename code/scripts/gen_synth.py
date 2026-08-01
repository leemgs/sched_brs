"""Synthetic AI-inference token-length dataset generator (Section V-C).

Reproduces the dataset described in the paper's Dataset Details:

    "The AI benchmark uses a synthetic 500,000-token dataset produced by the
     released gen_synth.py (token lengths drawn from a log-normal distribution
     with mean 512 and standard deviation 128 tokens, fixed random seed 42)."

We interpret the stated mean (512) and standard deviation (128) as the moments
of the *token-length* distribution itself (not of the underlying normal), and
solve for the log-normal parameters (mu, sigma) that yield those moments:

    mean = exp(mu + sigma^2 / 2)
    var  = (exp(sigma^2) - 1) * exp(2 mu + sigma^2)

so that sigma^2 = ln(1 + (sd/mean)^2) and mu = ln(mean) - sigma^2 / 2.

The generator is pure-Python (stdlib `random`) so the artifact stays
dependency-free and the seed makes it exactly reproducible. Sampling continues
until the cumulative token count reaches TARGET_TOKENS; each drawn value is a
request length (clamped to >= 1 token). Output is written as a simple text file
of one integer length per line plus a small JSON summary of the realised
moments, so downstream harnesses can replay the exact request stream.
"""

import argparse
import json
import math
import os
import random

TARGET_TOKENS = 500_000
MEAN_TOKENS = 512.0
SD_TOKENS = 128.0
SEED = 42


def lognormal_params(mean, sd):
    """(mu, sigma) of the underlying normal for a log-normal with given moments."""
    sigma2 = math.log(1.0 + (sd / mean) ** 2)
    mu = math.log(mean) - 0.5 * sigma2
    return mu, math.sqrt(sigma2)


def generate(target_tokens=TARGET_TOKENS, mean=MEAN_TOKENS, sd=SD_TOKENS, seed=SEED):
    """Draw request lengths until the cumulative token budget is reached."""
    rng = random.Random(seed)
    mu, sigma = lognormal_params(mean, sd)
    lengths = []
    total = 0
    while total < target_tokens:
        # Clamp to at least one token; a length longer than the remaining
        # budget is trimmed so the realised total lands exactly on target.
        length = max(1, int(round(rng.lognormvariate(mu, sigma))))
        if total + length > target_tokens:
            length = target_tokens - total
        lengths.append(length)
        total += length
    return lengths, (mu, sigma)


def _summary(lengths):
    n = len(lengths)
    mean = sum(lengths) / n
    var = sum((x - mean) ** 2 for x in lengths) / n
    return {
        "num_requests": n,
        "total_tokens": sum(lengths),
        "realized_mean": mean,
        "realized_sd": math.sqrt(var),
        "min": min(lengths),
        "max": max(lengths),
    }


def main():
    ap = argparse.ArgumentParser(description="Generate the synthetic AI-inference dataset (Sec V-C).")
    ap.add_argument("--tokens", type=int, default=TARGET_TOKENS)
    ap.add_argument("--mean", type=float, default=MEAN_TOKENS)
    ap.add_argument("--sd", type=float, default=SD_TOKENS)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default="results/synth_tokens.txt")
    args = ap.parse_args()

    lengths, (mu, sigma) = generate(args.tokens, args.mean, args.sd, args.seed)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(str(x) for x in lengths) + "\n")

    summ = _summary(lengths)
    summ.update({"target_mean": args.mean, "target_sd": args.sd,
                 "lognormal_mu": mu, "lognormal_sigma": sigma, "seed": args.seed})
    with open(os.path.splitext(args.out)[0] + "_summary.json", "w") as f:
        json.dump(summ, f, indent=2)

    print(f"Generated {summ['num_requests']} requests, {summ['total_tokens']} tokens "
          f"(seed={args.seed}).")
    print(f"  target mean/sd = {args.mean:.1f}/{args.sd:.1f} tokens; "
          f"realized = {summ['realized_mean']:.1f}/{summ['realized_sd']:.1f}")
    print(f"  log-normal mu={mu:.4f}, sigma={sigma:.4f}; range [{summ['min']}, {summ['max']}]")
    print(f"  wrote {args.out} and its _summary.json")


if __name__ == "__main__":
    main()
