"""
utils.py — Subsurface Observatory notebook utilities
=====================================================
Post-processing helpers shared across observatory notebooks.
FDSN queries are written explicitly in each notebook — see 01_fdsn_access.
"""

from __future__ import annotations

import re
from typing import List, Optional

import matplotlib.pyplot as plt
import pandas as pd
from obspy import Stream, UTCDateTime
from obspy.core.event import (Catalog, Comment, Event, Origin, OriginQuality,
                               Pick)
from obspy.core.event.base import WaveformStreamID
from obspy.core.event.magnitude import Magnitude

# ---------------------------------------------------------------------------
# FDSN endpoint constants
# ---------------------------------------------------------------------------

FDSN_UOM     = "https://subsurface.science.unimelb.edu.au"   # VW, VX, Z1
FDSN_AUSPASS = "https://auspass.edu.au"                       # OZ, AU, national archive
FDSN_RS      = "https://data.raspberryshake.org"              # AM (RaspberryShake)
FDSN_IRIS    = "https://service.iris.edu"                     # global fallback


# ---------------------------------------------------------------------------
# Catalog conversion
# ---------------------------------------------------------------------------

def convert_to_catalog(
    events: pd.DataFrame,
    assignments: pd.DataFrame,
    algorithm_name: str = "SeisBench-PyOcto",
) -> Catalog:
    """
    Convert SeisBench-style events + assignments DataFrames to an ObsPy Catalog.

    Parameters
    ----------
    events : pd.DataFrame
        Must include: idx, time (UNIX epoch s), latitude, longitude, depth (km).
    assignments : pd.DataFrame
        Must include: event_idx, station (NET.STA.LOC), phase, time, residual.
    algorithm_name : str
        Appended as a Comment to each origin.
    """
    cat = Catalog()

    for _, ev in events.iterrows():
        origin = Origin(
            time=UTCDateTime(float(ev["time"])),
            latitude=float(ev["latitude"]),
            longitude=float(ev["longitude"]),
            depth=float(ev["depth"]) * 1000.0,
            depth_type="from location",
            evaluation_mode="automatic",
            evaluation_status="preliminary",
            quality=OriginQuality(used_phase_count=0),
            comments=[Comment(text=f"Localized by: {algorithm_name}",
                              force_resource_id=False)],
        )
        mag   = Magnitude(mag=99.0, magnitude_type="ML")  # placeholder
        event = Event(origins=[origin], magnitudes=[mag])

        these_picks = assignments[assignments["event_idx"] == ev["idx"]]
        origin.quality.used_phase_count = len(these_picks)

        for _, p in these_picks.iterrows():
            parts = str(p["station"]).split(".")
            net, sta, loc = (parts + ["", "", ""])[:3]
            pick = Pick(
                time=UTCDateTime(float(p["time"])),
                waveform_id=WaveformStreamID(
                    network_code=net, station_code=sta,
                    location_code=loc, channel_code=p["phase"],
                ),
                phase_hint=p["phase"],
                evaluation_mode="automatic",
                evaluation_status="preliminary",
                comments=[Comment(text=f"residual={p['residual']:.3f} s")],
            )
            event.picks.append(pick)

        cat.append(event)

    return cat


# ---------------------------------------------------------------------------
# Velocity model parsing
# ---------------------------------------------------------------------------

def SRC_velocity_format(
    file: str,
    surface_Vp: Optional[float] = None,
    surface_Vs: Optional[float] = None,
) -> pd.DataFrame:
    """Parse SRC/Eqlocl-style 1-D velocity model → DataFrame (depth, vp, vs)."""
    def is_comment_or_blank(line: str) -> bool:
        s = line.strip()
        return (not s) or s.startswith("#")

    def first_floats(line: str, n: int) -> list:
        nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", line)
        return [float(x) for x in nums[:n]]

    with open(file, encoding="utf-8", errors="ignore") as f:
        text = f.read().replace("\r\n", "\n").replace("\r", "\n")

    lines = [ln for ln in text.split("\n") if not is_comment_or_blank(ln)]
    if len(lines) < 3:
        raise ValueError("Velocity model file too short.")

    n_layers = int(round(first_floats(lines[1], 1)[0]))
    start_idx, end_idx = 2, 2 + n_layers
    if end_idx > len(lines):
        raise ValueError(f"Layer count {n_layers} exceeds available lines.")

    depths, vps, vss = [], [], []
    for i in range(start_idx, end_idx):
        d, vp, vs = first_floats(lines[i], 3)
        depths.append(d); vps.append(vp); vss.append(vs)

    df = (
        pd.DataFrame({"depth": depths, "vp": vps, "vs": vss})
        .sort_values("depth")
        .reset_index(drop=True)
    )

    has_zero = len(df) and abs(df.iloc[0]["depth"]) < 1e-9
    if surface_Vp is not None and surface_Vs is not None:
        surf = pd.DataFrame([{"depth": 0.0, "vp": float(surface_Vp),
                               "vs": float(surface_Vs)}])
    else:
        surf = pd.DataFrame([{"depth": 0.0, "vp": float(df.iloc[0]["vp"]),
                               "vs": float(df.iloc[0]["vs"])}])

    if has_zero:
        df.iloc[0] = surf.iloc[0]
    else:
        df = pd.concat([surf, df], ignore_index=True)

    return df


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

def plot_station_picks_panel(
    st: Stream,
    stations: List[str],
    pick_dict=None,
    assignments=None,
    event_idx: int = 0,
    channel: str = "*Z",
    window_pre_p: float = 5.0,
    window_post_s: float = 5.0,
    fallback_post_p: float = 10.0,
    sharex: bool = True,
) -> None:
    """
    Plot one waveform per station with P (pink) and S (navy) pick lines.

    Stations are sorted by P arrival and all panels share the same time axis,
    referenced to the earliest P pick.

    Parameters
    ----------
    st : obspy.Stream
    stations : list of str
        Station codes to plot.
    pick_dict : dict, optional
        {sta: {"P": Pick, "S": Pick}} where picks have a .datetime attribute.
    assignments : pd.DataFrame, optional
        SeisBench-style with columns: event_idx, station, phase, time.
    event_idx : int
        Which event to use from assignments.
    channel : str
        Channel selector passed to Stream.select() (default "*Z").
    window_pre_p : float
        Seconds before earliest P to start each panel.
    window_post_s : float
        Seconds after each S pick to end that panel.
    fallback_post_p : float
        Seconds after P when no S pick exists.
    """
    if (pick_dict is None) == (assignments is None):
        raise ValueError("Provide exactly one of pick_dict or assignments.")

    def get_picks(sta):
        if pick_dict is not None:
            P = getattr(pick_dict.get(sta, {}).get("P"), "datetime", None)
            S = getattr(pick_dict.get(sta, {}).get("S"), "datetime", None)
            return P, S
        df = assignments.copy()
        if "event_idx" in df.columns:
            df = df[df["event_idx"] == event_idx]
        df["sta_code"] = df["station"].map(
            lambda s: str(s).split(".")[1] if "." in str(s) else str(s)
        )
        df_sta = df[df["sta_code"] == sta]

        def _pick(phase):
            sub = df_sta[df_sta["phase"].astype(str).str.upper() == phase]
            if sub.empty:
                return None
            if "probability" in sub.columns:
                sub = sub.sort_values("probability", ascending=False)
            return UTCDateTime(float(sub.iloc[0]["time"]))

        return _pick("P"), _pick("S")

    picked = [(sta, *get_picks(sta)) for sta in stations]
    picked = [(sta, P, S) for sta, P, S in picked if P is not None]
    if not picked:
        raise ValueError("No P picks available for the requested stations.")
    picked.sort(key=lambda x: x[1])

    P0 = picked[0][1]
    t0 = P0 - window_pre_p
    t_end_global = max(
        (S + window_post_s) if S is not None else (P + fallback_post_p)
        for _, P, S in picked
    )

    n = len(picked)
    fig, axes = plt.subplots(n, 1, figsize=(10, 2.2 * n), sharex=sharex)
    if n == 1:
        axes = [axes]

    for ax, (sta, P_time, S_time) in zip(axes, picked):
        trs = st.select(station=sta, channel=channel)
        if not trs:
            ax.set_title(f"{sta} (no trace for channel='{channel}')")
            ax.axis("off")
            continue

        tr = trs[0].copy().trim(starttime=t0, endtime=t_end_global)
        ax.plot(tr.times(reftime=t0), tr.data, "k", lw=0.8)
        ax.axvline(P_time - t0, color="#E5007D", lw=2, label="P")
        if S_time is not None:
            ax.axvline(S_time - t0, color="#000F46", lw=2, label="S")
        ax.set_ylabel(sta, rotation=0, ha="right", fontsize=9)
        ax.set_title(tr.id, fontsize=8)

    axes[0].legend(loc="upper right", fontsize=8)
    axes[-1].set_xlabel(f"Time since (first P − {window_pre_p:.0f} s)  [s]")
    plt.tight_layout()
    plt.show()
