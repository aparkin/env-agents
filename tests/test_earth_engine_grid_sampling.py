"""
Tests for Earth Engine Grid Sampling Implementation

Tests spatial sampling functionality for capturing environmental gradients.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from env_agents.core.models import RequestSpec, Geometry
from env_agents.adapters.earth_engine.spatial_sampling import (
    calculate_bbox_dimensions,
    calculate_sample_count,
    generate_sample_grid,
    should_use_grid_sampling
)


class TestBboxDimensions:
    """Test bbox dimension calculations"""

    def test_small_bbox_equator(self):
        """Test small bbox at equator"""
        # 0.1° × 0.1° at equator ≈ 11km × 11km
        bbox = [0.0, 0.0, 0.1, 0.1]
        width_m, height_m = calculate_bbox_dimensions(bbox)

        assert 10000 < width_m < 12000  # ~11km
        assert 10000 < height_m < 12000  # ~11km

    def test_large_bbox(self):
        """Test large bbox"""
        # 10° × 10° ≈ 1100km × 1100km
        bbox = [0.0, 0.0, 10.0, 10.0]
        width_m, height_m = calculate_bbox_dimensions(bbox)

        assert 1000000 < width_m < 1200000  # ~1100km
        assert 1000000 < height_m < 1200000  # ~1100km

    def test_bbox_san_francisco(self):
        """Test bbox in San Francisco (37°N)"""
        # At 37°N, longitude spacing is ~88km per degree (cos(37°) ≈ 0.8)
        # 1° × 1° ≈ 88km × 111km
        bbox = [-122.5, 37.5, -121.5, 38.5]
        width_m, height_m = calculate_bbox_dimensions(bbox)

        assert 80000 < width_m < 95000   # ~88km (longitude compressed at 37°N)
        assert 105000 < height_m < 115000  # ~111km (latitude constant)


class TestSampleCount:
    """Test adaptive sample count calculation"""

    def test_undersized_bbox_small_scale(self):
        """Test bbox smaller than data resolution"""
        # 20m bbox with 250m data (MODIS)
        bbox = [-122.0, 37.0, -122.0002, 37.0002]  # ~20m × 20m
        n_samples, n_side, metadata = calculate_sample_count(
            bbox, data_scale_m=250, resolution="medium"
        )

        assert n_samples == 1
        assert n_side == 1
        assert metadata["strategy"] == "undersized_bbox"
        assert "warning" in metadata

    def test_small_bbox_medium_resolution(self):
        """Test small bbox (10km) with medium resolution"""
        # 10km × 10km bbox (corrected: west < east)
        bbox = [-122.1, 37.0, -122.0, 37.1]
        n_samples, n_side, metadata = calculate_sample_count(
            bbox, data_scale_m=250, resolution="medium"
        )

        assert n_samples == 9  # 3×3 grid
        assert n_side == 3
        assert metadata["strategy"] == "fixed"
        assert not metadata.get("capped", False)

    def test_large_bbox_adaptive_scaling(self):
        """Test large bbox (300km) with adaptive scaling"""
        # 300km × 300km ≈ 90,000 km²
        bbox = [-122.0, 37.0, -119.0, 40.0]
        n_samples, n_side, metadata = calculate_sample_count(
            bbox, data_scale_m=250, resolution="medium"
        )

        # Should scale up from 9 (base medium)
        assert n_samples > 9
        assert n_samples <= 100  # Capped at max
        assert metadata["strategy"] == "adaptive_scaled"
        assert metadata["scale_factor"] > 1

    def test_huge_bbox_capped(self):
        """Test huge bbox (1000km) gets capped"""
        # 1000km × 1000km = 1M km²
        bbox = [-122.0, 30.0, -112.0, 40.0]
        n_samples, n_side, metadata = calculate_sample_count(
            bbox, data_scale_m=250, resolution="high", max_samples=50
        )

        # Should hit cap
        assert n_samples <= 50
        assert metadata.get("capped", False)

    def test_resolution_levels(self):
        """Test different resolution levels"""
        bbox = [-122.1, 37.0, -122.0, 37.1]  # 10km bbox (corrected: west < east)

        # Low resolution
        n_low, _, _ = calculate_sample_count(
            bbox, data_scale_m=250, resolution="low"
        )

        # Medium resolution
        n_med, _, _ = calculate_sample_count(
            bbox, data_scale_m=250, resolution="medium"
        )

        # High resolution
        n_high, _, _ = calculate_sample_count(
            bbox, data_scale_m=250, resolution="high"
        )

        assert n_low == 1
        assert n_med == 9
        assert n_high == 25
        assert n_low < n_med < n_high


class TestSampleGrid:
    """Test sample grid generation"""

    def test_grid_3x3(self):
        """Test 3×3 grid generation"""
        bbox = [-122.0, 37.0, -121.0, 38.0]
        sample_points = generate_sample_grid(bbox, n_side=3)

        assert len(sample_points) == 9

        # Check corners
        assert sample_points[0] == (37.0, -122.0)  # SW corner
        assert sample_points[2] == (37.0, -121.0)  # SE corner
        assert sample_points[6] == (38.0, -122.0)  # NW corner
        assert sample_points[8] == (38.0, -121.0)  # NE corner

        # Check center
        center = sample_points[4]
        assert abs(center[0] - 37.5) < 0.01  # lat
        assert abs(center[1] - -121.5) < 0.01  # lon

    def test_grid_5x5(self):
        """Test 5×5 grid generation"""
        bbox = [0.0, 0.0, 1.0, 1.0]
        sample_points = generate_sample_grid(bbox, n_side=5)

        assert len(sample_points) == 25

        # Check spacing
        lats = [p[0] for p in sample_points]
        lons = [p[1] for p in sample_points]

        assert min(lats) == 0.0
        assert max(lats) == 1.0
        assert min(lons) == 0.0
        assert max(lons) == 1.0


class TestGridSamplingDecision:
    """Test when grid sampling should be used"""

    def test_default_enabled(self):
        """Test grid sampling enabled by default"""
        spec = RequestSpec(geometry=Geometry("bbox", [-122, 37, -121, 38]))

        assert should_use_grid_sampling(spec) == True

    def test_resolution_low_disables(self):
        """Test resolution='low' disables grid sampling"""
        spec = RequestSpec(
            geometry=Geometry("bbox", [-122, 37, -121, 38]),
            resolution="low"
        )

        assert should_use_grid_sampling(spec) == False

    def test_explicit_disable(self):
        """Test explicit disable via extra params"""
        spec = RequestSpec(
            geometry=Geometry("bbox", [-122, 37, -121, 38]),
            extra={"grid_sampling": False}
        )

        assert should_use_grid_sampling(spec) == False

    def test_max_samples_one(self):
        """Test max_samples=1 disables grid sampling"""
        spec = RequestSpec(
            geometry=Geometry("bbox", [-122, 37, -121, 38]),
            extra={"max_samples": 1}
        )

        assert should_use_grid_sampling(spec) == False


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_tiny_bbox(self):
        """Test very tiny bbox (1m × 1m)"""
        # 0.00001° ≈ 1m
        bbox = [-122.0, 37.0, -122.00001, 37.00001]
        n_samples, _, metadata = calculate_sample_count(
            bbox, data_scale_m=30, resolution="high"
        )

        # Should return 1 sample with warning (too small for 30m SRTM)
        assert n_samples == 1
        assert "warning" in metadata

    def test_extreme_longitude(self):
        """Test bbox crossing date line"""
        # 179°E to -179°W (crossing date line)
        bbox = [179.0, 0.0, -179.0, 1.0]
        width_m, height_m = calculate_bbox_dimensions(bbox)

        # Should handle correctly (2° span = ~222km)
        assert width_m > 0  # Positive width
        assert 200000 < width_m < 250000

    def test_polar_region(self):
        """Test bbox near pole (80°N)"""
        # At 80°N, longitude spacing is very compressed
        bbox = [0.0, 80.0, 1.0, 81.0]
        width_m, height_m = calculate_bbox_dimensions(bbox)

        # Width should be much less than at equator
        assert width_m < 30000  # ~19km (cos(80°) ≈ 0.17)
        assert 100000 < height_m < 120000  # Height still ~111km


# Integration test examples (commented out - require Earth Engine auth)
"""
class TestEarthEngineIntegration:
    '''Integration tests with real Earth Engine queries'''

    def test_srtm_elevation_gradient(self):
        '''Test SRTM elevation capturing mountain gradient'''
        from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter

        adapter = ProductionEarthEngineAdapter(
            asset_id="USGS/SRTMGL1_003",
            scale=30
        )

        # San Francisco Bay Area (coast to hills)
        bbox = [-122.5, 37.5, -122.3, 37.7]
        spec = RequestSpec(
            geometry=Geometry("bbox", bbox),
            resolution="medium"
        )

        result = adapter.fetch(spec)

        # Should get 9 samples with varying elevations
        elevations = [r['value'] for r in result if r['variable'] == 'ee:elevation']
        assert len(elevations) == 9

        # Should show gradient (low at coast, high in hills)
        assert max(elevations) - min(elevations) > 100  # >100m elevation change

    def test_modis_ndvi_comparison(self):
        '''Test MODIS NDVI comparing aggregated vs grid'''
        from env_agents.adapters.earth_engine.production_adapter import ProductionEarthEngineAdapter

        adapter = ProductionEarthEngineAdapter(
            asset_id="MODIS/061/MOD13Q1",
            scale=250
        )

        bbox = [-122.0, 37.0, -121.0, 38.0]
        time_range = ("2023-01-01", "2023-12-31")

        # Query with aggregation (low resolution)
        spec_agg = RequestSpec(
            geometry=Geometry("bbox", bbox),
            time_range=time_range,
            resolution="low"
        )
        result_agg = adapter.fetch(spec_agg)

        # Query with grid sampling (medium resolution)
        spec_grid = RequestSpec(
            geometry=Geometry("bbox", bbox),
            time_range=time_range,
            resolution="medium"
        )
        result_grid = adapter.fetch(spec_grid)

        # Aggregated should return 1 value per variable
        ndvi_agg = [r for r in result_agg if 'NDVI' in r['variable']]
        assert len(ndvi_agg) == 1

        # Grid should return 9 values per variable (per date)
        ndvi_grid = [r for r in result_grid if 'NDVI' in r['variable']]
        assert len(ndvi_grid) >= 9  # At least 9 (may be more with time series)
"""


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
