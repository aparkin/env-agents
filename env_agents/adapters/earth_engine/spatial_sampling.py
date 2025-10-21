"""
Spatial Sampling Utilities for Earth Engine

Provides grid sampling functionality to capture environmental gradients
within bounding boxes instead of aggregating to single centroid values.
"""

import numpy as np
from typing import Tuple, List, Dict, Any
import math


def calculate_bbox_dimensions(bbox: List[float]) -> Tuple[float, float]:
    """
    Calculate bbox dimensions in meters (approximate).

    Args:
        bbox: [minlon, minlat, maxlon, maxlat]

    Returns:
        (width_m, height_m): Bbox dimensions in meters
    """
    minlon, minlat, maxlon, maxlat = bbox

    # Haversine distance approximation
    # At equator: 1° ≈ 111km
    # Adjust for latitude (longitude spacing decreases toward poles)
    center_lat = (minlat + maxlat) / 2

    # Height (N-S): constant across longitudes
    height_deg = maxlat - minlat
    height_m = height_deg * 111000  # 111km per degree

    # Width (E-W): adjusted for latitude
    width_deg = maxlon - minlon

    # Handle dateline crossing (e.g., bbox from 179°E to -179°W)
    if width_deg < 0:
        width_deg += 360

    width_m = width_deg * 111000 * math.cos(math.radians(center_lat))

    return abs(width_m), abs(height_m)


def calculate_sample_count(
    bbox: List[float],
    data_scale_m: int,
    resolution: str = "medium",
    max_samples: int = 100
) -> Tuple[int, int, Dict[str, Any]]:
    """
    Calculate appropriate sample count considering bbox size and data scale.

    Implements adaptive strategy:
    - Small bboxes: Reduce samples if smaller than data resolution
    - Large bboxes: Scale up samples to capture regional variation
    - Always capped at max_samples for performance

    Args:
        bbox: [minlon, minlat, maxlon, maxlat]
        data_scale_m: Native resolution of data source (meters)
        resolution: "low", "medium", "high", or None (treated as "medium")
        max_samples: Maximum samples to prevent overwhelming queries

    Returns:
        (n_samples, n_side, metadata_dict)
            n_samples: Total number of samples
            n_side: Grid dimension (n_side × n_side)
            metadata_dict: Information about sampling strategy
    """
    # Calculate bbox dimensions
    bbox_width_m, bbox_height_m = calculate_bbox_dimensions(bbox)
    bbox_area_km2 = (bbox_width_m * bbox_height_m) / 1e6

    # Base sample counts for each resolution level
    base_counts = {
        "low": 1,
        "medium": 9,
        "high": 25,
        None: 9  # Default to medium
    }
    base_samples = base_counts.get(resolution, 9)

    # Check if bbox is smaller than data scale
    # Need at least 2× data scale for meaningful gradients
    min_dimension_m = min(bbox_width_m, bbox_height_m)
    if min_dimension_m < data_scale_m * 2:
        # Bbox too small for data resolution
        return (1, 1, {
            "strategy": "undersized_bbox",
            "requested_resolution": resolution,
            "requested_samples": base_samples,
            "actual_samples": 1,
            "grid_size": "1×1",
            "warning": f"Bbox ({min_dimension_m:.0f}m) smaller than 2× data scale ({data_scale_m}m)",
            "recommendation": f"Increase bbox to >{data_scale_m * 2}m for meaningful gradients",
            "bbox_width_m": bbox_width_m,
            "bbox_height_m": bbox_height_m,
            "bbox_area_km2": bbox_area_km2,
            "data_scale_m": data_scale_m
        })

    # Adaptive scaling for large bboxes
    # Scale up sampling for areas > 100km × 100km (10,000 km²)
    if bbox_area_km2 > 10000:
        # Square root scaling: 10× area → ~3× samples
        scale_factor = math.sqrt(bbox_area_km2 / 10000)
        # Cap scale factor at 5× to avoid excessive sampling
        scale_factor = min(scale_factor, 5.0)
        scaled_samples = int(base_samples * scale_factor)
        strategy = "adaptive_scaled"
    else:
        scaled_samples = base_samples
        scale_factor = 1.0
        strategy = "fixed"

    # Apply maximum cap
    final_samples = min(scaled_samples, max_samples)
    was_capped = final_samples < scaled_samples

    # Calculate grid dimensions (nearest square)
    # Use floor to ensure we don't exceed max_samples
    n_side = int(math.sqrt(final_samples))
    actual_samples = n_side * n_side

    # If actual_samples is too small, try n_side + 1 but only if it doesn't exceed cap
    if actual_samples < final_samples:
        next_size = (n_side + 1) ** 2
        if next_size <= max_samples:
            n_side += 1
            actual_samples = next_size

    # Calculate sample spacing
    sample_spacing_m = min(bbox_width_m, bbox_height_m) / n_side

    # Build metadata
    metadata = {
        "strategy": strategy,
        "requested_resolution": resolution,
        "requested_samples": base_samples,
        "actual_samples": actual_samples,
        "grid_size": f"{n_side}×{n_side}",
        "sample_spacing_m": sample_spacing_m,
        "sample_spacing_km": sample_spacing_m / 1000,
        "bbox_width_m": bbox_width_m,
        "bbox_height_m": bbox_height_m,
        "bbox_area_km2": bbox_area_km2,
        "data_scale_m": data_scale_m,
        "scale_factor": scale_factor,
        "capped": was_capped
    }

    if was_capped:
        metadata["capped_from"] = scaled_samples
        metadata["cap_reason"] = f"Performance limit (max {max_samples} samples)"

    return (actual_samples, n_side, metadata)


def generate_sample_grid(bbox: List[float], n_side: int) -> List[Tuple[float, float]]:
    """
    Generate regular grid of sample points within bbox.

    Args:
        bbox: [minlon, minlat, maxlon, maxlat]
        n_side: Number of samples per side (creates n_side × n_side grid)

    Returns:
        List of (lat, lon) tuples for each sample point
    """
    minlon, minlat, maxlon, maxlat = bbox

    # Generate linearly spaced coordinates
    lons = np.linspace(minlon, maxlon, n_side)
    lats = np.linspace(minlat, maxlat, n_side)

    # Create grid (row-major order: west to east, south to north)
    sample_points = []
    for lat in lats:
        for lon in lons:
            sample_points.append((lat, lon))

    return sample_points


def should_use_grid_sampling(
    spec,
    default_enabled: bool = True
) -> bool:
    """
    Determine if grid sampling should be used for this request.

    Args:
        spec: RequestSpec
        default_enabled: Default behavior if not specified

    Returns:
        True if grid sampling should be used
    """
    # Check if explicitly disabled via extra params
    if spec.extra:
        # Explicit disable
        if spec.extra.get("grid_sampling") is False:
            return False

        # Resolution="low" means single sample (old behavior)
        if spec.resolution == "low":
            return False

        # max_samples=1 means single sample
        if spec.extra.get("max_samples") == 1:
            return False

    # Resolution="low" always means single sample
    if spec.resolution == "low":
        return False

    # Otherwise use default
    return default_enabled
