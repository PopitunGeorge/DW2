from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any


def _closes(points: list[dict[str, Any]]) -> list[float]:
    return [float(point["data"]["closePrice"]) for point in points]


def _open_prices(points: list[dict[str, Any]]) -> list[float]:
    return [float(point["data"]["openPrice"]) for point in points]


def _high_prices(points: list[dict[str, Any]]) -> list[float]:
    return [float(point["data"]["highPrice"]) for point in points]


def _low_prices(points: list[dict[str, Any]]) -> list[float]:
    return [float(point["data"]["lowPrice"]) for point in points]


def _volumes(points: list[dict[str, Any]]) -> list[float]:
    return [float(point["data"].get("volume", 0.0)) for point in points]


def _slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    xs = list(range(len(values)))
    x_mean = mean(xs)
    y_mean = mean(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    return 0.0 if denominator == 0 else numerator / denominator


def _rolling_window(values: list[float], window: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(len(values)):
        start = max(0, index - window + 1)
        window_values = values[start : index + 1]
        average = mean(window_values)
        volatility = pstdev(window_values) if len(window_values) > 1 else 0.0
        rows.append(
            {
                "index": index,
                "window": window,
                "count": len(window_values),
                "mean": average,
                "stddev": volatility,
                "upperBand": average + (2 * volatility),
                "lowerBand": average - (2 * volatility),
            }
        )
    return rows


def _max_drawdown(values: list[float]) -> list[dict[str, Any]]:
    peak = values[0]
    rows: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        peak = max(peak, value)
        drawdown = 0.0 if peak == 0 else ((value - peak) / peak) * 100.0
        rows.append(
            {
                "index": index,
                "price": value,
                "runningPeak": peak,
                "drawdownPct": drawdown,
                "isNewPeak": value == peak,
            }
        )
    return rows


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


def build_derived_series(points: list[dict[str, Any]], windows: list[int] | None = None) -> dict[str, Any]:
    windows = windows or [3, 5]
    timestamps = [point["data"]["timestamp"] for point in points]
    closes = _closes(points)
    volumes = _volumes(points)
    moving_averages = {
        f"w{window}": [
            {"timestamp": timestamps[row["index"]], **row}
            for row in _rolling_window(closes, window)
        ]
        for window in windows
    }
    volatility_bands = {
        f"w{window}": [
            {"timestamp": timestamps[row["index"]], **row}
            for row in _rolling_window(closes, window)
        ]
        for window in windows
    }
    drawdown = [
        {"timestamp": timestamps[row["index"]], **row}
        for row in _max_drawdown(closes)
    ]
    anomaly_flags = []
    for index, close in enumerate(closes):
        flags: list[str] = []
        if index > 0:
            previous_close = closes[index - 1]
            change_pct = _pct_change(close, previous_close)
            if abs(change_pct) >= 8.0:
                flags.append(f"price_jump_{'up' if change_pct > 0 else 'down'}")
        if index > 0 and volumes[index - 1] > 0:
            volume_ratio = volumes[index] / volumes[index - 1]
            if volume_ratio >= 1.5:
                flags.append("volume_spike")
        if index >= 2:
            recent = closes[max(0, index - 2) : index + 1]
            recent_mean = mean(recent)
            recent_std = pstdev(recent) if len(recent) > 1 else 0.0
            if recent_std > 0 and abs(close - recent_mean) / recent_std >= 2.5:
                flags.append("price_outlier")
        anomaly_flags.append(
            {
                "timestamp": timestamps[index],
                "closePrice": close,
                "volume": volumes[index],
                "flags": flags,
                "isAnomaly": bool(flags),
            }
        )
    return {
        "count": len(points),
        "timestamps": timestamps,
        "movingAverages": moving_averages,
        "volatilityBands": volatility_bands,
        "drawdown": drawdown,
        "anomalyFlags": anomaly_flags,
        "hasAnomalies": any(item["isAnomaly"] for item in anomaly_flags),
    }


def correlation_matrix(series_points: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    aligned_close_values: dict[str, list[float]] = {series_id: _closes(points) for series_id, points in series_points.items() if len(points) >= 2}
    series_ids = sorted(aligned_close_values)
    matrix: dict[str, dict[str, float]] = {series_id: {} for series_id in series_ids}
    for left_id in series_ids:
        for right_id in series_ids:
            left = aligned_close_values[left_id]
            right = aligned_close_values[right_id]
            length = min(len(left), len(right))
            if length < 2:
                coefficient = 1.0 if left_id == right_id else 0.0
            else:
                x = left[:length]
                y = right[:length]
                x_mean = mean(x)
                y_mean = mean(y)
                numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))
                denominator = math.sqrt(sum((a - x_mean) ** 2 for a in x) * sum((b - y_mean) ** 2 for b in y))
                coefficient = 1.0 if left_id == right_id else 0.0 if denominator == 0 else numerator / denominator
            matrix[left_id][right_id] = round(coefficient, 6)
    return {
        "seriesIds": series_ids,
        "matrix": matrix,
    }


def summarize_points(points: list[dict[str, Any]]) -> dict[str, Any]:
    if not points:
        return {"count": 0, "message": "No time-series points available."}
    closes = _closes(points)
    opens = _open_prices(points)
    highs = _high_prices(points)
    lows = _low_prices(points)
    volumes = _volumes(points)
    first_close = closes[0]
    last_close = closes[-1]
    percent_change = 0.0 if first_close == 0 else ((last_close - first_close) / first_close) * 100.0
    slope = _slope(closes)
    volatility = pstdev(closes) if len(closes) > 1 else 0.0
    average_close = mean(closes)
    relative_volatility = 0.0 if average_close == 0 else (volatility / average_close) * 100.0
    risk_signal = "HIGH_VOLATILITY" if relative_volatility >= 5.0 else "STABLE"
    momentum = "UP" if slope > 0 else "DOWN" if slope < 0 else "FLAT"
    forecast = last_close + slope
    return {
        "count": len(points),
        "firstTimestamp": points[0]["data"]["timestamp"],
        "lastTimestamp": points[-1]["data"]["timestamp"],
        "openFirst": opens[0],
        "closeLast": last_close,
        "highMax": max(highs),
        "lowMin": min(lows),
        "volumeTotal": sum(volumes),
        "closeAverage": average_close,
        "closeMin": min(closes),
        "closeMax": max(closes),
        "closeChangePct": percent_change,
        "volatility": volatility,
        "relativeVolatilityPct": relative_volatility,
        "trendSlope": slope,
        "nextCloseForecast": forecast,
        "momentum": momentum,
        "riskSignal": risk_signal,
        "insight": f"{momentum} trend with {risk_signal.lower().replace('_', ' ')}.",
    }


def compare_series(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_summary = summarize_points(left["points"])
    right_summary = summarize_points(right["points"])
    return {
        "leftSeriesId": left["seriesId"],
        "rightSeriesId": right["seriesId"],
        "closeAverageGap": left_summary["closeAverage"] - right_summary["closeAverage"],
        "lastCloseGap": left_summary["closeLast"] - right_summary["closeLast"],
        "volatilityGap": left_summary["volatility"] - right_summary["volatility"],
        "higherVolatility": left["seriesId"] if left_summary["volatility"] > right_summary["volatility"] else right["seriesId"],
        "left": left_summary,
        "right": right_summary,
    }


def explain_change(series: dict[str, Any]) -> str:
    summary = summarize_points(series["points"])
    direction = "increased" if summary["trendSlope"] > 0 else "decreased" if summary["trendSlope"] < 0 else "moved sideways"
    return (
        f"{series['seriesId']} {direction} from {summary['firstTimestamp']} to {summary['lastTimestamp']}. "
        f"The last close was {summary['closeLast']:.2f}, the average close was {summary['closeAverage']:.2f}, "
        f"and the risk signal was {summary['riskSignal'].lower().replace('_', ' ')}."
    )
