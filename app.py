# ==========================================
# Lotto Duo Compression (Drop-in Module)
# Upload historical draws (CSV/XLSX) -> build -5/+5/±5 candidates from latest draw
# -> compress into EXACTLY 4 duos (or configurable)
# ==========================================

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Sequence, Set, Dict, Optional

import pandas as pd
import streamlit as st


# ---------------------------
# CONFIG
# ---------------------------
@dataclass(frozen=True)
class CompressionConfig:
    min_num: int = 1
    max_num: int = 49
    duos_count: int = 4          # set to 4 for your request
    prefer_spacing: int = 5      # stabilizer spread preference


# ---------------------------
# DATA LOADING + PARSING
# ---------------------------
def read_uploaded_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith(".xlsx") or name.endswith(".xls"):
        return pd.read_excel(uploaded)
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    raise ValueError("Please upload an .xlsx, .xls, or .csv file.")


def detect_main_number_columns(df: pd.DataFrame) -> List[str]:
    """
    Detect 6 main-number columns.
    Supports:
      - N1..N6, Num1..Num6
      - Otherwise: first 6 columns that are mostly numeric
    """
    cols = list(df.columns)
    lower = [str(c).strip().lower() for c in cols]

    # Prefer explicit names
    preferred_sets = [
        ["n1", "n2", "n3", "n4", "n5", "n6"],
        ["num1", "num2", "num3", "num4", "num5", "num6"],
    ]
    for pref in preferred_sets:
        match = []
        for p in pref:
            if p in lower:
                match.append(cols[lower.index(p)])
        if len(match) == 6:
            return match

    # Fallback: first 6 mostly-numeric columns
    numeric_candidates: List[str] = []
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().mean() >= 0.80:
            numeric_candidates.append(c)

    if len(numeric_candidates) < 6:
        raise ValueError(
            "Could not detect 6 main-number columns. "
            "Ensure your file has 6 main numbers per row (e.g., N1..N6 or Num1..Num6)."
        )

    return numeric_candidates[:6]


def parse_draws(df: pd.DataFrame) -> Tuple[List[List[int]], List[int], List[str]]:
    """
    Returns (all_draws, latest_draw, used_cols)
    all_draws contains only valid rows with 6 integers.
    """
    use_cols = detect_main_number_columns(df)

    draws: List[List[int]] = []
    for _, row in df.iterrows():
        try:
            nums = [int(row[c]) for c in use_cols]
            # basic sanity: within 1..49 (adjust if your game differs)
            draws.append(nums)
        except Exception:
            continue

    if not draws:
        raise ValueError("No valid draw rows found after parsing. Check your file format.")

    return draws, draws[-1], use_cols


# ---------------------------
# TRANSFORM: -5, +5, ±5
# ---------------------------
def transform_candidates(latest_draw: Sequence[int], mode: str, cfg: CompressionConfig) -> List[int]:
    """
    mode in {"-5", "+5", "+/-5"}.
    """
    out: Set[int] = set()
    for n in latest_draw:
        if mode in ("-5", "+/-5"):
            m = n - 5
            if cfg.min_num <= m <= cfg.max_num:
                out.add(m)
        if mode in ("+5", "+/-5"):
            m = n + 5
            if cfg.min_num <= m <= cfg.max_num:
                out.add(m)
    return sorted(out)


# ---------------------------
# COMPRESSION ENGINE (to duos)
# ---------------------------
def _freq_map(all_draws: Sequence[Sequence[int]]) -> Dict[int, int]:
    freq: Dict[int, int] = {}
    for d in all_draws:
        for n in d:
            freq[n] = freq.get(n, 0) + 1
    return freq


def _pick_anchors(candidates: List[int], freq: Dict[int, int]) -> Tuple[int, int]:
    """
    Pick 2 anchors:
    - highest historical frequency
    - second anchor chosen to maximize spread among top candidates
    """
    ranked = sorted(candidates, key=lambda x: (-freq.get(x, 0), x))
    a1 = ranked[0]
    pool = ranked[1:min(len(ranked), 7)] or ranked[1:]
    a2 = max(pool, key=lambda x: (abs(x - a1), freq.get(x, 0), -x))
    return a1, a2


def _pick_stabilizers(
    candidates: List[int],
    anchors: Tuple[int, int],
    freq: Dict[int, int],
    prefer_spacing: int
) -> Tuple[int, int]:
    """
    Choose 2 stabilizers:
    - far from anchors (spread)
    - decent frequency
    - prefer spacing >= prefer_spacing between stabilizers
    """
    a1, a2 = anchors
    remaining = [c for c in candidates if c not in anchors]

    if len(remaining) == 0:
        return a1, a2
    if len(remaining) == 1:
        return remaining[0], a1

    def base_score(x: int) -> Tuple[int, int, int]:
        spread = min(abs(x - a1), abs(x - a2))
        return (spread, freq.get(x, 0), -x)

    ranked = sorted(remaining, key=base_score, reverse=True)
    s1 = ranked[0]

    def s2_score(x: int) -> Tuple[int, int, int, int]:
        spacing_ok = 1 if abs(x - s1) >= prefer_spacing else 0
        return (spacing_ok, abs(x - s1), min(abs(x - a1), abs(x - a2)), freq.get(x, 0))

    s2 = max(ranked[1:], key=s2_score)
    return s1, s2


def compress_to_duos(candidates: List[int], all_draws: Sequence[Sequence[int]], cfg: CompressionConfig) -> List[Tuple[int, int]]:
    """
    EXACTLY 4 duos design (default):
      1) A1 & S1
      2) A1 & S2
      3) A1 & A2
      4) S1 & A2
    This concentrates coverage around strongest anchor while keeping a bridge.
    """
    if len(candidates) < 2:
        return []

    freq = _freq_map(all_draws)
    a1, a2 = _pick_anchors(candidates, freq)
    s1, s2 = _pick_stabilizers(candidates, (a1, a2), freq, cfg.prefer_spacing)

    base = [
        tuple(sorted((a1, s1))),
        tuple(sorted((a1, s2))),
        tuple(sorted((a1, a2))),
        tuple(sorted((s1, a2))),
    ]

    # unique + valid
    duos: List[Tuple[int, int]] = []
    seen: Set[Tuple[int, int]] = set()
    for d in base:
        if d[0] == d[1]:
            continue
        if d not in seen:
            seen.add(d)
            duos.append(d)

    # Ensure exact count (fill if needed)
    if len(duos) < cfg.duos_count:
        # add best remaining pairs by combined frequency + spread
        existing = set(duos)

        def duo_score(p: Tuple[int, int]) -> Tuple[int, int]:
            x, y = p
            return (freq.get(x, 0) + freq.get(y, 0), abs(x - y))

        remaining_pairs: List[Tuple[int, int]] = []
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                p = tuple(sorted((candidates[i], candidates[j])))
                if p not in existing:
                    remaining_pairs.append(p)

        remaining_pairs.sort(key=duo_score, reverse=True)
        for p in remaining_pairs:
            if len(duos) >= cfg.duos_count:
                break
            duos.append(p)

    return duos[:cfg.duos_count]


# ---------------------------
# STREAMLIT UI (drop-in)
# ---------------------------
def render_duo_compression_ui() -> None:
    st.subheader("🎯 Duo Compression (Guided Randomness)")

    uploaded = st.file_uploader("Upload historical draws (.xlsx / .csv)", type=["xlsx", "xls", "csv"])
    if not uploaded:
        st.info("Upload your file to generate compressed duos.")
        return

    mode = st.selectbox("Transform rule", ["-5", "+5", "+/-5"], index=0)
    duos_count = st.number_input("How many duos?", min_value=2, max_value=12, value=4, step=1)
    prefer_spacing = st.slider("Prefer stabilizer spacing", 3, 12, 5, 1)

    cfg = CompressionConfig(duos_count=int(duos_count), prefer_spacing=int(prefer_spacing))

    try:
        df = read_uploaded_file(uploaded)
        draws, latest_draw, used_cols = parse_draws(df)

        st.caption(f"Detected main-number columns: {', '.join(map(str, used_cols))}")
        st.write("Latest draw:", latest_draw)

        candidates = transform_candidates(latest_draw, mode=mode, cfg=cfg)
        st.write(f"Candidate set ({mode}):", candidates)

        if len(candidates) < 2:
            st.warning("Not enough candidates to form duos. Try +5 or +/-5.")
            return

        duos = compress_to_duos(candidates, draws, cfg)

        st.markdown("### ✅ Compressed duos")
        for i, (a, b) in enumerate(duos, start=1):
            st.markdown(f"**{i}. {a} & {b}**")

    except Exception as e:
        st.error(str(e))


# If you want it to run immediately when pasted into app.py:
# render_duo_compression_ui()
