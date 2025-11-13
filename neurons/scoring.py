"""
WAHOOPREDICT - Scoring system for validators.

Validators use this to score miners based on WAHOO API performance data.
Ranks miners by spending and volume, then combines rankings into final weights.
"""

from typing import List, Dict, Any, Tuple


def rank_miners_by_metric(
    validation_data: List[Dict[str, Any]], metric_key: str
) -> Dict[str, float]:
    """
    Rank miners by a specific metric (spending, volume, etc.).

    Returns a dictionary mapping hotkey to rank (0.0 to 1.0, where 1.0 is best).

    Args:
        validation_data: List of validation data from WAHOO API
        metric_key: Key to extract from performance dict (e.g., 'total_volume_usd')

    Returns:
        Dictionary mapping hotkey to normalized rank (0.0 = worst, 1.0 = best)
    """
    # Extract metric values for all miners
    miner_metrics = {}
    for item in validation_data:
        hotkey = item.get("hotkey")
        if not hotkey:
            continue

        performance = item.get("performance", {})
        metric_value = float(performance.get(metric_key, 0.0))

        if metric_value > 0:  # Only include miners with positive metric
            miner_metrics[hotkey] = metric_value

    if not miner_metrics:
        return {}

    # Sort by metric value (descending - highest first)
    sorted_miners = sorted(miner_metrics.items(), key=lambda x: x[1], reverse=True)

    # Assign ranks (1.0 for best, decreasing to 0.0 for worst)
    # Use percentile ranking: best miner gets 1.0, worst gets 0.0
    num_miners = len(sorted_miners)
    ranks = {}

    for idx, (hotkey, value) in enumerate(sorted_miners):
        # Percentile rank: (num_miners - idx) / num_miners
        # This gives best miner rank of 1.0, worst miner rank of 1/num_miners
        rank = (num_miners - idx) / num_miners
        ranks[hotkey] = rank

    return ranks


def compute_spending(performance: Dict[str, Any]) -> float:
    """
    Compute total spending from performance data.

    Spending = total_volume_usd (money spent on trades)

    Args:
        performance: Performance dictionary from WAHOO API

    Returns:
        Total spending in USD
    """
    return float(performance.get("total_volume_usd", 0.0))


def compute_volume(performance: Dict[str, Any]) -> float:
    """
    Compute trading volume from performance data.

    Volume = total_volume_usd (same as spending for now, but can be extended)

    Args:
        performance: Performance dictionary from WAHOO API

    Returns:
        Total volume in USD
    """
    return float(performance.get("total_volume_usd", 0.0))


def compute_final_weights(
    validation_data: List[Dict[str, Any]],
    spending_weight: float = 0.5,
    volume_weight: float = 0.5,
    min_spending: float = 0.0,
    min_volume: float = 0.0,
) -> Dict[str, float]:
    """
    Compute final normalized weights from WAHOO validation data.

    This is the main function validators should use.

    Process:
    1. Rank miners by spending (money spent on WAHOO)
    2. Rank miners by volume (trading volume)
    3. Combine rankings with weighted average
    4. Normalize to sum to 1.0

    Args:
        validation_data: List of validation data from WAHOO API
        spending_weight: Weight for spending ranking (default: 0.5)
        volume_weight: Weight for volume ranking (default: 0.5)
        min_spending: Minimum spending to be considered (default: 0.0)
        min_volume: Minimum volume to be considered (default: 0.0)

    Returns:
        Dictionary mapping hotkey to normalized weight (sums to 1.0)
    """
    if not validation_data:
        return {}

    # Filter miners by minimum thresholds
    filtered_data = []
    for item in validation_data:
        hotkey = item.get("hotkey")
        if not hotkey:
            continue

        performance = item.get("performance", {})
        spending = compute_spending(performance)
        volume = compute_volume(performance)

        # Only include miners meeting minimum thresholds
        if spending >= min_spending and volume >= min_volume:
            filtered_data.append(item)

    if not filtered_data:
        return {}

    # Rank miners by spending
    spending_ranks = rank_miners_by_metric(filtered_data, "total_volume_usd")

    # Rank miners by volume (same metric for now, but can be extended)
    volume_ranks = rank_miners_by_metric(filtered_data, "total_volume_usd")

    # Combine rankings with weighted average
    combined_scores = {}
    all_hotkeys = set(spending_ranks.keys()) | set(volume_ranks.keys())

    for hotkey in all_hotkeys:
        spending_rank = spending_ranks.get(hotkey, 0.0)
        volume_rank = volume_ranks.get(hotkey, 0.0)

        # Weighted combination
        combined_score = (spending_weight * spending_rank) + (
            volume_weight * volume_rank
        )
        combined_scores[hotkey] = combined_score

    # Normalize to sum to 1.0
    total = sum(combined_scores.values())
    if total == 0:
        # If all scores are zero, return equal weights
        if combined_scores:
            equal_weight = 1.0 / len(combined_scores)
            return {hotkey: equal_weight for hotkey in combined_scores.keys()}
        return {}

    normalized = {hotkey: score / total for hotkey, score in combined_scores.items()}
    return normalized


def get_miner_rankings(validation_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get ranked list of miners with their metrics and ranks.

    Useful for logging/debugging to see how miners are ranked.

    Args:
        validation_data: List of validation data from WAHOO API

    Returns:
        List of dictionaries with hotkey, spending, volume, and combined rank
    """
    if not validation_data:
        return []

    # Extract metrics
    miners = []
    for item in validation_data:
        hotkey = item.get("hotkey")
        if not hotkey:
            continue

        performance = item.get("performance", {})
        spending = compute_spending(performance)
        volume = compute_volume(performance)

        miners.append({"hotkey": hotkey, "spending": spending, "volume": volume})

    # Sort by spending + volume (combined metric)
    miners.sort(key=lambda x: x["spending"] + x["volume"], reverse=True)

    # Add rank
    for idx, miner in enumerate(miners):
        miner["rank"] = idx + 1

    return miners
