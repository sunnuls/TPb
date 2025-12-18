"""Stub card recognition module."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageOps


def recognize_cards(_image: Image.Image) -> list[str]:
    # TODO: integrate ML model / template matching; return list like ["As","Kd",...]
    return []


@dataclass(frozen=True)
class CardTokenDetection:
    token: str
    x: int
    y: int
    w: int
    h: int
    score: float
    confidence: float


def _load_font(size: int) -> ImageFont.ImageFont:
    _ = size
    return ImageFont.load_default()


def _preprocess_gray(img: Image.Image) -> np.ndarray:
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    g = ImageOps.invert(g)
    arr = np.asarray(g, dtype=np.float32) / 255.0
    return arr


def _integral_image(a: np.ndarray) -> np.ndarray:
    s = np.pad(a, ((1, 0), (1, 0)), mode="constant", constant_values=0.0)
    return s.cumsum(axis=0).cumsum(axis=1)


def _patch_sum(ii: np.ndarray, h: int, w: int) -> np.ndarray:
    return ii[h:, w:] - ii[:-h, w:] - ii[h:, :-w] + ii[:-h, :-w]


def _corr_map_fft(*, f_img: np.ndarray, template0: np.ndarray, out_shape: tuple[int, int]) -> np.ndarray:
    t = template0[::-1, ::-1]
    f_t = np.fft.rfft2(t, out_shape)
    corr_full = np.fft.irfft2(f_img * f_t, out_shape)
    h, w = template0.shape
    return corr_full[h - 1 : out_shape[0] - (h - 1), w - 1 : out_shape[1] - (w - 1)]


def _ncc_map(
    *,
    img: np.ndarray,
    f_img: np.ndarray,
    ii: np.ndarray,
    ii2: np.ndarray,
    template: np.ndarray,
    eps: float = 1e-6,
) -> np.ndarray:
    h, w = template.shape
    n = float(h * w)

    t0 = template - float(template.mean())
    t_norm = float(np.sqrt(np.sum(t0 * t0)))
    if t_norm <= 0:
        return np.zeros((img.shape[0] - h + 1, img.shape[1] - w + 1), dtype=np.float32)

    out_shape = (img.shape[0] + h - 1, img.shape[1] + w - 1)
    num = _corr_map_fft(f_img=f_img, template0=t0, out_shape=out_shape)

    sum_i = _patch_sum(ii, h, w)
    sum_i2 = _patch_sum(ii2, h, w)
    var = sum_i2 - (sum_i * sum_i) / n
    var = np.maximum(var, 0.0)
    denom = np.sqrt(var) * t_norm
    return (num / (denom + eps)).astype(np.float32)


def _render_char_template(*, ch: str, box: int, font_size: int) -> np.ndarray:
    img = Image.new("RGB", (box, box), (255, 255, 255))
    d = ImageDraw.Draw(img)
    font = _load_font(font_size)
    d.text((1, 0), ch, fill=(0, 0, 0), font=font)
    return _preprocess_gray(img)


def _topk_peaks(ncc: np.ndarray, *, k: int, threshold: float) -> list[tuple[int, int, float]]:
    flat = ncc.ravel()
    if flat.size == 0:
        return []
    k = min(k, int(flat.size))
    idxs = np.argpartition(flat, -k)[-k:]
    peaks: list[tuple[int, int, float]] = []
    for idx in idxs:
        s = float(flat[idx])
        if s < threshold:
            continue
        y = int(idx // ncc.shape[1])
        x = int(idx % ncc.shape[1])
        peaks.append((x, y, s))
    peaks.sort(key=lambda t: t[2], reverse=True)
    return peaks


def _nms(peaks: list[tuple[int, int, float]], *, min_dist: int) -> list[tuple[int, int, float]]:
    kept: list[tuple[int, int, float]] = []
    for x, y, s in peaks:
        ok = True
        for x2, y2, _ in kept:
            if abs(x - x2) <= min_dist and abs(y - y2) <= min_dist:
                ok = False
                break
        if ok:
            kept.append((x, y, s))
    return kept


def _nms_token_candidates(
    candidates: list[tuple[str, int, int, float]],
    *,
    min_dist: int,
) -> list[tuple[str, int, int, float]]:
    kept: list[tuple[str, int, int, float]] = []
    for tok, x, y, s in sorted(candidates, key=lambda t: t[3], reverse=True):
        ok = True
        for _, x2, y2, _ in kept:
            if abs(x - x2) <= min_dist and abs(y - y2) <= min_dist:
                ok = False
                break
        if ok:
            kept.append((tok, x, y, s))
    return kept


def _score_to_confidence(score: float, *, threshold: float) -> float:
    if score < threshold:
        return 0.0
    x = (score - threshold) / max(1e-6, (1.0 - threshold))
    x = max(0.0, min(1.0, x))
    return float(0.9 + 0.1 * x)


def detect_card_tokens(
    image: Image.Image,
    *,
    threshold: float = 0.86,
    topk_per_char: int = 25,
) -> tuple[list[CardTokenDetection], list[str]]:
    warnings: list[str] = []

    img = image
    max_dim = max(img.size)
    scale = 1.0
    if max_dim > 1100:
        scale = 1100.0 / float(max_dim)
        img = img.resize((int(img.size[0] * scale), int(img.size[1] * scale)), Image.Resampling.BILINEAR)

    g = _preprocess_gray(img)
    ii = _integral_image(g)
    ii2 = _integral_image(g * g)

    box = 18
    font_size = 14
    ranks = list("23456789TJQKA")
    suits = list("shdc")

    out_shape = (g.shape[0] + box - 1, g.shape[1] + box - 1)
    f_img = np.fft.rfft2(g, out_shape)

    rank_hits: list[tuple[str, int, int, float]] = []
    suit_hits: list[tuple[str, int, int, float]] = []

    for r in ranks:
        t = _render_char_template(ch=r, box=box, font_size=font_size)
        ncc = _ncc_map(img=g, f_img=f_img, ii=ii, ii2=ii2, template=t)
        peaks = _nms(_topk_peaks(ncc, k=topk_per_char, threshold=threshold), min_dist=box // 2)
        for x, y, s in peaks:
            rank_hits.append((r, x, y, float(s)))

    for s_ch in suits:
        t = _render_char_template(ch=s_ch, box=box, font_size=font_size)
        ncc = _ncc_map(img=g, f_img=f_img, ii=ii, ii2=ii2, template=t)
        peaks = _nms(_topk_peaks(ncc, k=topk_per_char, threshold=threshold), min_dist=box // 2)
        for x, y, s in peaks:
            suit_hits.append((s_ch, x, y, float(s)))

    token_candidates: list[tuple[str, int, int, float]] = []
    max_dx = int(box * 2.2)
    max_dy = int(box * 0.8)
    for r, rx, ry, rs in rank_hits:
        best: tuple[str, int, int, float] | None = None
        best_score = 0.0
        for s_ch, sx, sy, ss in suit_hits:
            dx = sx - rx
            if dx <= 0 or dx > max_dx:
                continue
            if abs(sy - ry) > max_dy:
                continue
            sc = min(rs, ss)
            if sc > best_score:
                best_score = sc
                best = (s_ch, sx, sy, ss)
        if best is None:
            continue
        token = f"{r}{best[0]}"
        token_candidates.append((token, rx, ry, float(best_score)))

    token_candidates = _nms_token_candidates(token_candidates, min_dist=box)

    dets: list[CardTokenDetection] = []
    for tok, x, y, s in token_candidates:
        conf = _score_to_confidence(float(s), threshold=threshold)
        dets.append(
            CardTokenDetection(
                token=tok,
                x=int(x / scale),
                y=int(y / scale),
                w=int(box / scale),
                h=int(box / scale),
                score=float(s),
                confidence=conf,
            )
        )

    if dets:
        warnings.append("Распознавание карт работает только по символам ранга/масти и может быть неточным.")
    return dets, warnings


