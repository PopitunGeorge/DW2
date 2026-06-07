from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from typing import Any

def get_spark_session():
    """Creates and returns a Spark session."""
    return SparkSession.builder.appName("AuroraVaultAnalytics").getOrCreate()

def _create_df_from_points(spark: SparkSession, points: list[dict[str, Any]]) -> DataFrame:
    """Create a Spark DataFrame from a list of time-series points."""
    flat_data = []
    for p in points:
        flat_data.append({
            "timestamp": p["data"]["timestamp"],
            "close": float(p["data"]["closePrice"]),
            "open": float(p["data"]["openPrice"]),
            "high": float(p["data"]["highPrice"]),
            "low": float(p["data"]["lowPrice"]),
            "volume": float(p["data"].get("volume", 0.0)),
        })
    
    return spark.createDataFrame(flat_data)

def summarize_points_spark(points: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Analyzes time-series data using Spark to generate a summary of metrics,
    trends, and forecasts.
    """
    if not points:
        return {"count": 0, "message": "No time-series points available."}

    spark = get_spark_session()
    df = _create_df_from_points(spark, points)
    df = df.withColumn("timestamp", F.to_timestamp("timestamp"))
    df = df.orderBy("timestamp")

    # Add row number for slope calculation
    window_spec = Window.orderBy("timestamp")
    df = df.withColumn("index", F.row_number().over(window_spec) - 1)

    # Calculate statistics
    summary = df.agg(
        F.count("*").alias("count"),
        F.first("timestamp").alias("firstTimestamp"),
        F.last("timestamp").alias("lastTimestamp"),
        F.first("open").alias("openFirst"),
        F.last("close").alias("closeLast"),
        F.max("high").alias("highMax"),
        F.min("low").alias("lowMin"),
        F.sum("volume").alias("volumeTotal"),
        F.avg("close").alias("closeAverage"),
        F.min("close").alias("closeMin"),
        F.max("close").alias("closeMax"),
        F.stddev_pop("close").alias("volatility")
    ).collect()[0].asDict()

    # Slope calculation
    n = summary["count"]
    if n > 1:
        x_mean = (n - 1) / 2
        y_mean = summary["closeAverage"]
        
        df_slope = df.withColumn("xy", (F.col("index") - x_mean) * (F.col("close") - y_mean))
        df_slope = df_slope.withColumn("x_sq", (F.col("index") - x_mean) ** 2)
        
        slope_agg = df_slope.agg(
            F.sum("xy").alias("numerator"),
            F.sum("x_sq").alias("denominator")
        ).collect()[0]

        slope = 0.0 if slope_agg["denominator"] == 0 else slope_agg["numerator"] / slope_agg["denominator"]
    else:
        slope = 0.0

    first_close = df.select("close").first()[0]
    last_close = summary["closeLast"]
    percent_change = 0.0 if first_close == 0 else ((last_close - first_close) / first_close) * 100.0
    
    average_close = summary["closeAverage"]
    relative_volatility = 0.0 if average_close == 0 else (summary["volatility"] / average_close) * 100.0
    
    risk_signal = "HIGH_VOLATILITY" if relative_volatility >= 5.0 else "STABLE"
    momentum = "UP" if slope > 0 else "DOWN" if slope < 0 else "FLAT"
    forecast = last_close + slope

    return {
        "count": summary["count"],
        "firstTimestamp": str(summary["firstTimestamp"]),
        "lastTimestamp": str(summary["lastTimestamp"]),
        "openFirst": summary["openFirst"],
        "closeLast": summary["closeLast"],
        "highMax": summary["highMax"],
        "lowMin": summary["lowMin"],
        "volumeTotal": summary["volumeTotal"],
        "closeAverage": average_close,
        "closeMin": summary["closeMin"],
        "closeMax": summary["closeMax"],
        "closeChangePct": percent_change,
        "volatility": summary["volatility"],
        "relativeVolatilityPct": relative_volatility,
        "trendSlope": slope,
        "nextCloseForecast": forecast,
        "momentum": momentum,
        "riskSignal": risk_signal,
        "insight": f"{momentum} trend with {risk_signal.lower().replace('_', ' ')}.",
    }

def compare_series_spark(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_summary = summarize_points_spark(left["points"])
    right_summary = summarize_points_spark(right["points"])
    
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
