"""Shared charting utilities for backtesting metric tests.

Charts are written to base_dir/charts/ so that daily outputs go to
data/backtesting/<strategy>/ndx/<date>/charts/ and intraday to
data/backtesting/<strategy>/ndx/<date>/intraday/<timeframe>/charts/.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _MATPLOTLIB_AVAILABLE = True
except ImportError:
    _MATPLOTLIB_AVAILABLE = False
    plt = None


def _scalar_metrics(metrics: Dict[str, Any]) -> Dict[str, float]:
    """Return only scalar numeric metrics (no Series)."""
    out = {}
    for k, v in metrics.items():
        if v is None:
            continue
        if isinstance(v, (int, float)):
            out[k] = float(v)
        elif hasattr(v, "item"):
            try:
                out[k] = float(v.item())
            except (ValueError, AttributeError, TypeError):
                pass
    return out


def save_backtest_metrics_charts(
    metrics: Dict[str, Any],
    base_dir: Path,
    label: str = "daily",
    date_str: Optional[str] = None,
) -> List[Path]:
    """
    Plot backtesting metrics (CAGAR, volatility, Sharpe, max drawdown) and save to base_dir/charts/.

    Args:
        metrics: Dict of metric name -> value (scalars only are plotted).
        base_dir: Directory for this run (e.g. .../ndx/20260204 or .../intraday/5min). Charts go in base_dir/charts/.
        label: Suffix for filenames and titles (e.g. "daily", "5min").
        date_str: Optional date string for filename (e.g. "20260204"). If None, not included in filename.

    Returns:
        List of created chart file paths, or empty if matplotlib is not available or no scalar metrics.
    """
    if not _MATPLOTLIB_AVAILABLE:
        print("   Matplotlib not available, skipping chart generation")
        return []

    scalar = _scalar_metrics(metrics)
    if not scalar:
        print("   No scalar metrics to plot, skipping charts")
        return []

    charts_dir = base_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []

    # Sort by key for consistent bar order
    names = sorted(scalar.keys())
    values = [scalar[n] for n in names]
    # Shorten labels for display (e.g. cagar_1y -> cagar_1y)
    labels = [n.replace("_", " ").strip() for n in names]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(names))
    bars = ax.bar(x, values, color="steelblue", edgecolor="navy", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Value")
    ax.set_title(f"NDX Backtest Metrics ({label})")
    ax.axhline(y=0, color="gray", linestyle="-", linewidth=0.5)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()

    fname = f"ndx_backtest_metrics_{label}"
    if date_str:
        fname += f"_{date_str}"
    fname += ".png"
    chart_path = charts_dir / fname
    fig.savefig(chart_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    created.append(chart_path)
    print(f"   Created chart: charts/{chart_path.name}")

    return created
