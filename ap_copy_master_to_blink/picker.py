"""
Interactive date picker for flexible flat frame matching.

Displays older and newer candidate flat dates relative to the light frame
date, with a centered "None of these (rig changed)" option that is
pre-selected. The user navigates with arrow keys and selects with Enter.

Fallback: if terminal raw mode is unavailable, uses numbered input.
"""

import sys
import logging
from datetime import date
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

NONE_LABEL = "None of these (rig changed)"
SEPARATOR = "\u2500" * 28  # ────────────────────────────


def _day_diff_label(candidate: date, light_date: date) -> str:
    """Format the day-difference label for a candidate date."""
    diff = (candidate - light_date).days
    abs_diff = abs(diff)
    unit = "day" if abs_diff == 1 else "days"
    if diff < 0:
        return f"({abs_diff} {unit} older)"
    elif diff > 0:
        return f"({abs_diff} {unit} newer)"
    return "(same day)"


def build_picker_items(
    light_date: date,
    older_dates: List[date],
    newer_dates: List[date],
    picker_limit: int,
) -> Tuple[List[str], List[Optional[date]], int, Optional[str], Optional[str]]:
    """
    Build the list of display items and corresponding date values.

    Args:
        light_date: The light frame date
        older_dates: Older candidate dates, sorted ascending (oldest first)
        newer_dates: Newer candidate dates, sorted ascending (oldest first)
        picker_limit: Max older/newer dates to show

    Returns:
        Tuple of:
        - display_lines: List of display strings for each selectable item
        - date_values: List of date objects (or None for the "none" option)
        - none_index: Index of the "None of these" option
        - older_overflow_msg: Message about hidden older dates, or None
        - newer_overflow_msg: Message about hidden newer dates, or None
    """
    display_lines: List[str] = []
    date_values: List[Optional[date]] = []

    # Older dates: show most recent N (tail of sorted list)
    older_overflow_msg = None
    if len(older_dates) > picker_limit:
        hidden = len(older_dates) - picker_limit
        older_overflow_msg = f"... {hidden} more older flats not shown"
        visible_older = older_dates[-picker_limit:]
    else:
        visible_older = older_dates

    for d in visible_older:
        label = f"{d.isoformat()}  {_day_diff_label(d, light_date)}"
        display_lines.append(label)
        date_values.append(d)

    # "None" option
    none_index = len(display_lines)
    display_lines.append(NONE_LABEL)
    date_values.append(None)

    # Newer dates: show oldest N (head of sorted list)
    newer_overflow_msg = None
    if len(newer_dates) > picker_limit:
        hidden = len(newer_dates) - picker_limit
        newer_overflow_msg = f"... {hidden} more newer flats not shown"
        visible_newer = newer_dates[:picker_limit]
    else:
        visible_newer = newer_dates

    for d in visible_newer:
        label = f"{d.isoformat()}  {_day_diff_label(d, light_date)}"
        display_lines.append(label)
        date_values.append(d)

    return (
        display_lines,
        date_values,
        none_index,
        older_overflow_msg,
        newer_overflow_msg,
    )


def _render_picker(
    header: str,
    display_lines: List[str],
    selected: int,
    none_index: int,
    older_overflow_msg: Optional[str],
    newer_overflow_msg: Optional[str],
) -> str:
    """Render the picker display as a string."""
    lines = []
    lines.append(header)
    lines.append("")

    if older_overflow_msg:
        lines.append(f"  {older_overflow_msg}")

    for i, item in enumerate(display_lines):
        if i == none_index:
            # Separator before "none"
            lines.append(f"  {SEPARATOR}")

        prefix = "\u25b8 " if i == selected else "  "
        lines.append(f"{prefix}{item}")

        if i == none_index:
            # Separator after "none"
            lines.append(f"  {SEPARATOR}")

    if newer_overflow_msg:
        lines.append(f"  {newer_overflow_msg}")

    lines.append("")
    lines.append("\u2191/\u2193 to move, Enter to select")
    return "\n".join(lines)


def _read_key() -> str:
    """
    Read a single keypress from the terminal.

    Returns:
        "up", "down", "enter", or the raw character.
    """
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\r" or ch == "\n":
            return "enter"
        if ch == "\x1b":
            # Escape sequence
            seq = sys.stdin.read(2)
            if seq == "[A":
                return "up"
            if seq == "[B":
                return "down"
            return "escape"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def _interactive_pick(
    header: str,
    display_lines: List[str],
    none_index: int,
    older_overflow_msg: Optional[str],
    newer_overflow_msg: Optional[str],
) -> int:
    """
    Run the interactive picker using terminal raw mode.

    Returns:
        Index of the selected item.
    """
    selected = none_index
    total = len(display_lines)

    while True:
        # Clear screen area and render
        output = _render_picker(
            header,
            display_lines,
            selected,
            none_index,
            older_overflow_msg,
            newer_overflow_msg,
        )
        # Move cursor up to overwrite previous render
        line_count = output.count("\n") + 1
        sys.stdout.write(f"\033[{line_count}A\033[J")
        sys.stdout.write(output + "\n")
        sys.stdout.flush()

        key = _read_key()
        if key == "up" and selected > 0:
            selected -= 1
        elif key == "down" and selected < total - 1:
            selected += 1
        elif key == "enter":
            return selected


def _fallback_pick(
    header: str,
    display_lines: List[str],
    none_index: int,
    older_overflow_msg: Optional[str],
    newer_overflow_msg: Optional[str],
) -> int:
    """
    Fallback picker using numbered input when terminal raw mode unavailable.

    Returns:
        Index of the selected item.
    """
    print(header)
    print()

    if older_overflow_msg:
        print(f"  {older_overflow_msg}")

    for i, item in enumerate(display_lines):
        if i == none_index:
            print(f"  {SEPARATOR}")

        marker = "*" if i == none_index else " "
        print(f"  {marker} [{i + 1}] {item}")

        if i == none_index:
            print(f"  {SEPARATOR}")

    if newer_overflow_msg:
        print(f"  {newer_overflow_msg}")

    print()
    default = none_index + 1
    while True:
        try:
            raw = input(f"Select [1-{len(display_lines)}] (default: {default}): ")
            if not raw.strip():
                return none_index
            choice = int(raw.strip())
            if 1 <= choice <= len(display_lines):
                return choice - 1
            print(f"Please enter a number between 1 and {len(display_lines)}")
        except ValueError:
            print("Please enter a valid number")
        except EOFError:
            return none_index


def pick_flat_date(
    light_date_str: str,
    filter_name: str,
    older_dates: List[date],
    newer_dates: List[date],
    picker_limit: int = 5,
) -> Optional[date]:
    """
    Display interactive picker for flat frame date selection.

    Args:
        light_date_str: Light frame date as string (YYYY-MM-DD)
        filter_name: Filter name for display
        older_dates: Older candidate dates, sorted ascending
        newer_dates: Newer candidate dates, sorted ascending
        picker_limit: Max older/newer dates to show

    Returns:
        Selected date, or None if user chose "None of these (rig changed)"
    """
    light_date = date.fromisoformat(light_date_str)

    display_lines, date_values, none_index, older_msg, newer_msg = build_picker_items(
        light_date, older_dates, newer_dates, picker_limit
    )

    if not older_dates and not newer_dates:
        logger.debug("No candidate flat dates to display")
        return None

    header = f"No exact flat for {light_date_str} (filter: {filter_name})"

    # Try interactive mode, fall back to numbered input
    try:
        # Pre-print blank lines so cursor-up works on first render
        output = _render_picker(
            header, display_lines, none_index, none_index, older_msg, newer_msg
        )
        line_count = output.count("\n") + 1
        sys.stdout.write("\n" * line_count)
        sys.stdout.flush()

        selected_idx = _interactive_pick(
            header, display_lines, none_index, older_msg, newer_msg
        )
    except (ImportError, OSError, AttributeError):
        # Terminal raw mode not available (e.g., Windows without curses,
        # or non-interactive terminal)
        selected_idx = _fallback_pick(
            header, display_lines, none_index, older_msg, newer_msg
        )

    selected_date = date_values[selected_idx]

    if selected_date is None:
        logger.info(
            f"User selected 'rig changed' for {light_date_str} "
            f"(filter: {filter_name})"
        )
    else:
        logger.info(
            f"User selected flat date {selected_date.isoformat()} "
            f"for {light_date_str} (filter: {filter_name})"
        )

    return selected_date
