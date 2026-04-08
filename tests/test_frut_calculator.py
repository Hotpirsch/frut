"""
test_frut_calculator.py – Unit tests for the core frutidx algorithm.

Run with:
  cd backend && pip install pytest
  pytest ../tests/test_frut_calculator.py -v
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Make the backend package importable without installing it.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from frut_calculator import (
    absolute_bearing_difference,
    adjacent_bearing_differences,
    calculate_bearing,
    calculate_frut_idx,
    frut_score,
    section_bearings,
)


# ── calculate_bearing ────────────────────────────────────────────────────────


class TestCalculateBearing:
    def test_north(self):
        """Moving due north → bearing 0°."""
        b = calculate_bearing(0.0, 0.0, 1.0, 0.0)
        assert abs(b) < 0.01 or abs(b - 360) < 0.01

    def test_east(self):
        """Moving due east → bearing 90°."""
        b = calculate_bearing(0.0, 0.0, 0.0, 1.0)
        assert abs(b - 90.0) < 0.01

    def test_south(self):
        """Moving due south → bearing 180°."""
        b = calculate_bearing(1.0, 0.0, 0.0, 0.0)
        assert abs(b - 180.0) < 0.01

    def test_west(self):
        """Moving due west → bearing 270°."""
        b = calculate_bearing(0.0, 1.0, 0.0, 0.0)
        assert abs(b - 270.0) < 0.01

    def test_range(self):
        """Result must always be in [0, 360)."""
        for lat1, lon1, lat2, lon2 in [
            (48.1, 11.6, 47.5, 12.3),
            (-33.9, 151.2, 35.7, 139.7),
            (51.5, -0.1, 40.7, -74.0),
        ]:
            b = calculate_bearing(lat1, lon1, lat2, lon2)
            assert 0.0 <= b < 360.0


# ── absolute_bearing_difference ──────────────────────────────────────────────


class TestAbsoluteBearingDifference:
    def test_zero_difference(self):
        assert absolute_bearing_difference(90.0, 90.0) == 0.0

    def test_90_degrees(self):
        assert abs(absolute_bearing_difference(0.0, 90.0) - 90.0) < 1e-9

    def test_180_degrees(self):
        assert abs(absolute_bearing_difference(0.0, 180.0) - 180.0) < 1e-9

    def test_wrap_around(self):
        """Difference between 10° and 350° should be 20°, not 340°."""
        assert abs(absolute_bearing_difference(10.0, 350.0) - 20.0) < 1e-9

    def test_symmetry(self):
        """Bearing difference must be symmetric."""
        b1, b2 = 45.0, 200.0
        assert absolute_bearing_difference(b1, b2) == absolute_bearing_difference(b2, b1)

    def test_result_in_range(self):
        """Result must always be in [0, 180]."""
        for b1, b2 in [(0, 0), (0, 90), (0, 180), (359, 1), (270, 90)]:
            d = absolute_bearing_difference(b1, b2)
            assert 0.0 <= d <= 180.0


# ── section_bearings ─────────────────────────────────────────────────────────


class TestSectionBearings:
    def test_single_section(self):
        coords = [(0.0, 0.0), (1.0, 0.0)]
        bearings = section_bearings(coords)
        assert len(bearings) == 1
        # Moving north
        assert abs(bearings[0]) < 0.01 or abs(bearings[0] - 360) < 0.01

    def test_two_sections(self):
        # North then East
        coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
        bearings = section_bearings(coords)
        assert len(bearings) == 2
        assert abs(bearings[0]) < 0.01 or abs(bearings[0] - 360) < 0.01  # north
        assert abs(bearings[1] - 90.0) < 0.1                             # east

    def test_degenerate_section(self):
        """Identical consecutive coordinates should not raise."""
        coords = [(0.0, 0.0), (0.0, 0.0), (1.0, 0.0)]
        bearings = section_bearings(coords)
        assert len(bearings) == 2


# ── adjacent_bearing_differences ─────────────────────────────────────────────


class TestAdjacentBearingDifferences:
    def test_length(self):
        bearings = [0.0, 90.0, 180.0, 270.0]
        diffs = adjacent_bearing_differences(bearings)
        assert len(diffs) == len(bearings) - 1

    def test_right_angle_turn(self):
        # North → East: 90° difference
        diffs = adjacent_bearing_differences([0.0, 90.0])
        assert abs(diffs[0] - 90.0) < 1e-9

    def test_u_turn(self):
        # North → South: 180° difference
        diffs = adjacent_bearing_differences([0.0, 180.0])
        assert abs(diffs[0] - 180.0) < 1e-9

    def test_straight(self):
        diffs = adjacent_bearing_differences([45.0, 45.0])
        assert abs(diffs[0]) < 1e-9


# ── calculate_frut_idx ────────────────────────────────────────────────────────


class TestCalculateFrutIdx:
    def test_empty_coords(self):
        sections, total = calculate_frut_idx([])
        assert sections == []
        assert total == 0.0

    def test_single_coord(self):
        sections, total = calculate_frut_idx([(0.0, 0.0)])
        assert sections == []
        assert total == 0.0

    def test_two_coords_one_section(self):
        """Single section → no adjacent sections → frutidx = 0."""
        sections, total = calculate_frut_idx([(0.0, 0.0), (1.0, 0.0)])
        assert len(sections) == 1
        assert sections[0] == 0.0
        assert total == 0.0

    def test_three_coords_right_angle(self):
        """
        North then East: one 90° corner.
        - Section 0 (north): following diff = 90° → frutidx = 90
        - Section 1 (east) : leading  diff = 90° → frutidx = 90
        Total = 180°
        """
        coords = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)]
        sections, total = calculate_frut_idx(coords)
        assert len(sections) == 2
        assert abs(sections[0] - 90.0) < 0.1
        assert abs(sections[1] - 90.0) < 0.1
        assert abs(total - 180.0) < 0.2

    def test_four_coords_two_corners(self):
        """
        North → East → South: two 90° corners.
        - Section 0: frutidx = diff(0,1)            = 90°
        - Section 1: frutidx = (diff(0,1)+diff(1,2))/2 = (90+90)/2 = 90°
        - Section 2: frutidx = diff(1,2)            = 90°
        Total = 270°
        """
        coords = [
            (0.0, 0.0),  # start
            (1.0, 0.0),  # north
            (1.0, 1.0),  # east
            (0.0, 1.0),  # south
        ]
        sections, total = calculate_frut_idx(coords)
        assert len(sections) == 3
        assert abs(sections[0] - 90.0) < 0.5
        assert abs(sections[1] - 90.0) < 0.5
        assert abs(sections[2] - 90.0) < 0.5
        assert abs(total - 270.0) < 1.5

    def test_straight_route(self):
        """A perfectly straight route should have frutidx = 0."""
        coords = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]
        sections, total = calculate_frut_idx(coords)
        assert all(abs(v) < 1e-6 for v in sections)
        assert abs(total) < 1e-6

    def test_total_equals_sum_of_sections(self):
        coords = [(48.0, 11.0), (48.5, 11.5), (48.2, 12.0), (49.0, 11.8)]
        sections, total = calculate_frut_idx(coords)
        assert abs(total - sum(sections)) < 1e-9


# ── frut_score ────────────────────────────────────────────────────────────────


class TestFrutScore:
    def test_zero_distance(self):
        assert frut_score(100.0, 0.0) == 0.0

    def test_negative_distance(self):
        assert frut_score(100.0, -1.0) == 0.0

    def test_proportional_to_frut_idx(self):
        """Doubling frutidx should double the score."""
        s1 = frut_score(100.0, 1000.0)
        s2 = frut_score(200.0, 1000.0)
        assert abs(s2 - 2 * s1) < 1e-9

    def test_weight_scaling(self):
        """Score should scale linearly with weight."""
        s1 = frut_score(100.0, 1000.0, weight=1.0)
        s2 = frut_score(100.0, 1000.0, weight=3.0)
        assert abs(s2 - 3 * s1) < 1e-9

    def test_higher_distance_lower_score(self):
        """Same frutidx over a longer route → lower score."""
        s_short = frut_score(100.0, 1000.0)
        s_long  = frut_score(100.0, 5000.0)
        assert s_short > s_long
