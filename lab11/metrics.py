"""Part A: read a rollout. TODO 1, 2 and 9 live here; the helpers below them are given."""
from __future__ import annotations

import numpy as np

from avsim import core

G = 9.81
HALF_EGO = core.CAR[0] / 2   # 2.3 m: half the ego's length


def ego_events(R: core.Rollout, k: int) -> list[dict]:
    """Failure events involving the ego in scenario k, earliest first (given).

    event["kind"] is "contact" (the boxes touched) or "block" (the ego's body stopped the pedestrian P1 on the
    crosswalk: pedestrians never walk into a car, so this is how a planner that stops too late fails them)."""
    return [e for e in R.events[k] if e["a"] == "ego" or e["b"] == "ego"]


def min_ttc(R: core.Rollout, cap: float = 10.0) -> np.ndarray:
    """TODO 1. (K,) smallest time-to-collision between the ego and whatever it is following, capped at `cap` s.

    - The ego's leader at frame f is R.EGO[k, f, 3] (an actor index, -1 = nothing ahead).
    - Gap is bumper to bumper along the ego's heading: lon - 2.3 - (leader length / 2), where
      lon = (x_leader - x_ego) * hx_ego + (z_leader - z_ego) * hz_ego (the leader's position seen from the ego) and
      2.3 is half the ego's length. Leader length: core.LEN[j] for actor j; use 0.3 m as the half-length of a
      pedestrian. Clip the gap at 0.
    - TTC = gap / (v_ego - v_leader), only while the ego is closing in by more than 0.1 m/s.
    - A scenario where the ego crashed (see ego_events) returns 0.
    Shapes: R.F is (K, NF, N, 7) with x, z, hx, hz, v, a, d; core.IX["ego"] is the ego's actor index.
    Vectorise over frames (a Python loop over 481 frames x K scenarios is too slow for Part C).
    """
    K = R.F.shape[0]
    if K == 0:
        return np.empty((0,), dtype=float)

    ego_i = core.IX["ego"]
    ego = R.F[:, :, ego_i]
    x_ego, z_ego = ego[..., 0], ego[..., 1]
    hx_ego, hz_ego = ego[..., 2], ego[..., 3]
    v_ego = ego[..., 4]

    ldr_idx = R.EGO[..., 3].astype(int)
    valid_ldr = (ldr_idx >= 0) & (ldr_idx < core.N)
    safe_ldr = np.where(valid_ldr, ldr_idx, 0)

    k_idx = np.arange(K)[:, None]
    f_idx = np.arange(R.F.shape[1])[None, :]
    ldr = R.F[k_idx, f_idx, safe_ldr]
    x_ldr, z_ldr = ldr[..., 0], ldr[..., 1]
    v_ldr = ldr[..., 4]
    ldr_len = core.LEN[safe_ldr]

    rx = x_ldr - x_ego
    rz = z_ldr - z_ego
    lon = rx * hx_ego + rz * hz_ego
    gap = np.maximum(0.0, lon - HALF_EGO - ldr_len / 2.0)
    dv = v_ego - v_ldr

    closing = valid_ldr & (dv > 0.1)
    safe_dv = np.where(closing, dv, 1.0)
    ttc = np.where(closing, gap / safe_dv, np.inf)
    min_val = np.minimum(cap, ttc.min(axis=1))

    crashed = np.array([len(ego_events(R, k)) > 0 for k in range(K)], dtype=bool)
    return np.where(crashed, 0.0, min_val)


def contact_type(R: core.Rollout, k: int, event: dict) -> str:
    """TODO 2. 'front' (the ego ran into it), 'rear' (it ran into the ego) or 'side', at the contact frame.

    Put the other actor in the ego's frame: lon = r . h, lat = -r_x h_z + r_z h_x with h = (hx, hz) of the ego.
    'front' if lon > 2.3 and |lat| < 1.6; 'rear' if lon < -2.3 and |lat| < 1.6; otherwise 'side'.
    """
    f = event["f"]
    other_name = event["b"] if event["a"] == "ego" else event["a"]
    ego_i = core.IX["ego"]
    other_i = core.IX[other_name]

    ego_state = R.F[k, f, ego_i]
    other_state = R.F[k, f, other_i]

    rx = other_state[0] - ego_state[0]
    rz = other_state[1] - ego_state[1]
    hx = ego_state[2]
    hz = ego_state[3]

    lon = rx * hx + rz * hz
    lat = -rx * hz + rz * hx

    if lon > 2.3 and abs(lat) < 1.6:
        return "front"
    elif lon < -2.3 and abs(lat) < 1.6:
        return "rear"
    else:
        return "side"


def progress_metrics(R: core.Rollout) -> tuple[np.ndarray, np.ndarray]:
    """TODO 9. Two (K,) arrays: the distance the ego covers in the 24 s (sum of frame-to-frame steps, metres),
    and the number of frames where the ego brakes harder than 3 m/s^2 (acceleration column < -3)."""
    ego_i = core.IX["ego"]
    ego = R.F[:, :, ego_i]
    dx = np.diff(ego[..., 0], axis=1)
    dz = np.diff(ego[..., 1], axis=1)
    dist = np.sum(np.hypot(dx, dz), axis=1)
    harsh = np.sum(ego[..., 5] < -3.0, axis=1)
    return dist, harsh


# ---------------------------------------------------------------- given helpers

def pair_min_ttc(R, follower, leader, cap=10.0, lat_max=2.2, leader_vmin=-1.0):
    """(K,) smallest TTC of `follower` running into `leader` while they share a corridor."""
    F = R.F
    a, b = F[:, :, core.IX[follower]], F[:, :, core.IX[leader]]
    rx, rz = b[..., 0] - a[..., 0], b[..., 1] - a[..., 1]
    lon = rx * a[..., 2] + rz * a[..., 3]
    lat = -rx * a[..., 3] + rz * a[..., 2]
    gap = np.maximum(lon - core.LEN[core.IX[follower]] / 2 - core.LEN[core.IX[leader]] / 2, 0.0)
    dv = a[..., 4] - b[..., 4]
    ok = (lon > 0) & (np.abs(lat) < lat_max) & (dv > 0.1) & (b[..., 4] >= leader_vmin)
    ttc = np.where(ok, gap / np.maximum(dv, 1e-6), np.inf)
    return np.minimum(cap, ttc.min(1))


def ped_room(R, cap=30.0):
    """(K,) smallest stopping room [m] left while the crossing pedestrian is in the ego's lane
    (distance to them minus the ego's braking distance at mu*g). Negative = could not have stopped."""
    e, p = R.F[:, :, core.IX["ego"]], R.F[:, :, core.IX["P1"]]
    mu = np.asarray(R.params["mu"])[:, None]
    inlane = np.abs(p[..., 1] - e[..., 1]) < 1.9
    ahead = p[..., 0] - e[..., 0] - HALF_EGO
    room = np.where(inlane & (ahead > -1.0), ahead - e[..., 4] ** 2 / (2 * mu * G), cap)
    return np.clip(room.min(1), -cap, cap)
