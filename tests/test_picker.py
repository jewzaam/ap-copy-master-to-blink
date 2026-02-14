"""
Tests for interactive date picker.
"""

import unittest
from datetime import date
from unittest.mock import patch

from ap_copy_master_to_blink.picker import (
    build_picker_items,
    pick_flat_date,
    _day_diff_label,
    NONE_LABEL,
)


class TestDayDiffLabel(unittest.TestCase):
    """Tests for _day_diff_label helper."""

    def test_older_singular(self):
        """1 day older uses singular form."""
        result = _day_diff_label(date(2025, 8, 19), date(2025, 8, 20))
        self.assertEqual(result, "(1 day older)")

    def test_older_plural(self):
        """Multiple days older uses plural form."""
        result = _day_diff_label(date(2025, 8, 10), date(2025, 8, 20))
        self.assertEqual(result, "(10 days older)")

    def test_newer_singular(self):
        """1 day newer uses singular form."""
        result = _day_diff_label(date(2025, 8, 21), date(2025, 8, 20))
        self.assertEqual(result, "(1 day newer)")

    def test_newer_plural(self):
        """Multiple days newer uses plural form."""
        result = _day_diff_label(date(2025, 8, 25), date(2025, 8, 20))
        self.assertEqual(result, "(5 days newer)")

    def test_same_day(self):
        """Same day returns appropriate label."""
        result = _day_diff_label(date(2025, 8, 20), date(2025, 8, 20))
        self.assertEqual(result, "(same day)")


class TestBuildPickerItems(unittest.TestCase):
    """Tests for build_picker_items function."""

    def test_basic_older_and_newer(self):
        """Build picker with both older and newer dates."""
        light_date = date(2025, 8, 20)
        older = [date(2025, 8, 10), date(2025, 8, 17)]
        newer = [date(2025, 8, 25), date(2025, 9, 1)]

        lines, values, none_idx, older_msg, newer_msg = build_picker_items(
            light_date, older, newer, picker_limit=5
        )

        # 2 older + 1 none + 2 newer = 5 items
        self.assertEqual(len(lines), 5)
        self.assertEqual(len(values), 5)
        self.assertEqual(none_idx, 2)

        # None option
        self.assertEqual(lines[none_idx], NONE_LABEL)
        self.assertIsNone(values[none_idx])

        # Older dates
        self.assertEqual(values[0], date(2025, 8, 10))
        self.assertEqual(values[1], date(2025, 8, 17))

        # Newer dates
        self.assertEqual(values[3], date(2025, 8, 25))
        self.assertEqual(values[4], date(2025, 9, 1))

        # No overflow
        self.assertIsNone(older_msg)
        self.assertIsNone(newer_msg)

    def test_picker_limit_truncates_older(self):
        """Picker limit truncates older dates, showing most recent."""
        light_date = date(2025, 8, 20)
        older = [
            date(2025, 7, 1),
            date(2025, 7, 15),
            date(2025, 8, 1),
            date(2025, 8, 10),
            date(2025, 8, 17),
        ]
        newer = []

        lines, values, none_idx, older_msg, newer_msg = build_picker_items(
            light_date, older, newer, picker_limit=3
        )

        # 3 visible older + 1 none = 4 items
        self.assertEqual(len(lines), 4)
        self.assertEqual(none_idx, 3)

        # Should show most recent 3 (tail of sorted list)
        self.assertEqual(values[0], date(2025, 8, 1))
        self.assertEqual(values[1], date(2025, 8, 10))
        self.assertEqual(values[2], date(2025, 8, 17))

        # Overflow message
        self.assertIsNotNone(older_msg)
        self.assertIn("2", older_msg)  # 2 more hidden

        self.assertIsNone(newer_msg)

    def test_picker_limit_truncates_newer(self):
        """Picker limit truncates newer dates, showing oldest."""
        light_date = date(2025, 8, 20)
        older = []
        newer = [
            date(2025, 8, 25),
            date(2025, 9, 1),
            date(2025, 9, 10),
            date(2025, 9, 20),
            date(2025, 10, 1),
        ]

        lines, values, none_idx, older_msg, newer_msg = build_picker_items(
            light_date, older, newer, picker_limit=3
        )

        # 1 none + 3 visible newer = 4 items
        self.assertEqual(len(lines), 4)
        self.assertEqual(none_idx, 0)

        # Should show oldest 3 (head of sorted list)
        self.assertEqual(values[1], date(2025, 8, 25))
        self.assertEqual(values[2], date(2025, 9, 1))
        self.assertEqual(values[3], date(2025, 9, 10))

        # Overflow message
        self.assertIsNone(older_msg)
        self.assertIsNotNone(newer_msg)
        self.assertIn("2", newer_msg)  # 2 more hidden

    def test_empty_older_and_newer(self):
        """Build picker with no candidates."""
        light_date = date(2025, 8, 20)

        lines, values, none_idx, older_msg, newer_msg = build_picker_items(
            light_date, [], [], picker_limit=5
        )

        # Only the none option
        self.assertEqual(len(lines), 1)
        self.assertEqual(none_idx, 0)
        self.assertEqual(lines[0], NONE_LABEL)

    def test_only_older_dates(self):
        """Build picker with only older dates."""
        light_date = date(2025, 8, 20)
        older = [date(2025, 8, 10), date(2025, 8, 17)]

        lines, values, none_idx, older_msg, newer_msg = build_picker_items(
            light_date, older, [], picker_limit=5
        )

        self.assertEqual(len(lines), 3)  # 2 older + 1 none
        self.assertEqual(none_idx, 2)

    def test_only_newer_dates(self):
        """Build picker with only newer dates."""
        light_date = date(2025, 8, 20)
        newer = [date(2025, 8, 25)]

        lines, values, none_idx, older_msg, newer_msg = build_picker_items(
            light_date, [], newer, picker_limit=5
        )

        self.assertEqual(len(lines), 2)  # 1 none + 1 newer
        self.assertEqual(none_idx, 0)

    def test_day_diff_in_display_lines(self):
        """Display lines include day difference labels."""
        light_date = date(2025, 8, 20)
        older = [date(2025, 8, 17)]
        newer = [date(2025, 8, 25)]

        lines, _, _, _, _ = build_picker_items(light_date, older, newer, picker_limit=5)

        self.assertIn("3 days older", lines[0])
        self.assertIn("5 days newer", lines[2])


class TestPickFlatDate(unittest.TestCase):
    """Tests for pick_flat_date function."""

    def test_no_candidates_returns_none(self):
        """No candidates returns None without prompting."""
        result = pick_flat_date("2025-08-20", "Ha", [], [], picker_limit=5)
        self.assertIsNone(result)

    @patch("ap_copy_master_to_blink.picker._interactive_pick")
    def test_user_selects_none(self, mock_pick):
        """User selecting 'None' returns None."""
        older = [date(2025, 8, 17)]
        newer = [date(2025, 8, 25)]

        # "None" is at index 1 (after 1 older date)
        mock_pick.return_value = 1

        result = pick_flat_date("2025-08-20", "Ha", older, newer, picker_limit=5)
        self.assertIsNone(result)

    @patch("ap_copy_master_to_blink.picker._interactive_pick")
    def test_user_selects_older_date(self, mock_pick):
        """User selecting an older date returns that date."""
        older = [date(2025, 8, 17)]
        newer = [date(2025, 8, 25)]

        # Select first item (the older date)
        mock_pick.return_value = 0

        result = pick_flat_date("2025-08-20", "Ha", older, newer, picker_limit=5)
        self.assertEqual(result, date(2025, 8, 17))

    @patch("ap_copy_master_to_blink.picker._interactive_pick")
    def test_user_selects_newer_date(self, mock_pick):
        """User selecting a newer date returns that date."""
        older = [date(2025, 8, 17)]
        newer = [date(2025, 8, 25)]

        # Select last item (the newer date, at index 2)
        mock_pick.return_value = 2

        result = pick_flat_date("2025-08-20", "Ha", older, newer, picker_limit=5)
        self.assertEqual(result, date(2025, 8, 25))

    @patch(
        "ap_copy_master_to_blink.picker._interactive_pick",
        side_effect=ImportError,
    )
    @patch("ap_copy_master_to_blink.picker._fallback_pick")
    def test_fallback_on_import_error(self, mock_fallback, mock_interactive):
        """Falls back to numbered input when terminal unavailable."""
        older = [date(2025, 8, 17)]
        newer = [date(2025, 8, 25)]

        # Fallback selects "None" (index 1)
        mock_fallback.return_value = 1

        result = pick_flat_date("2025-08-20", "Ha", older, newer, picker_limit=5)
        self.assertIsNone(result)
        mock_fallback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
