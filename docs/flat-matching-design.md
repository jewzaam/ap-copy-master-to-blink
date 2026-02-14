# Flat Frame Matching: Design Document

**Status**: Proposal
**Issue**: [#5 - Add flexible flat date matching with configurable tolerance](https://github.com/jewzaam/ap-copy-master-to-blink/issues/5)
**Date**: 2026-02-14

## Problem

The tool currently requires an exact DATE match between light frames and flat frames. This is too strict. Flats are valid until the imaging train physically changes (e.g., filter wheel replaced, camera rotated, optical train adjusted). A flat taken three weeks before a light session is perfectly fine if nothing changed. A flat taken yesterday is useless if the filter wheel was replaced today.

The real constraint is not calendar proximity -- it is **equipment continuity**. A simple `--flat-date-tolerance N` days parameter does not model this correctly.

## Core Concept: Rig Change Tracking

A **rig change** is any physical modification to the imaging train that invalidates existing flat frames. Common examples:

- Replaced or repositioned filter wheel
- Changed camera orientation or spacing
- Swapped optical elements (reducer, flattener)
- Adjusted focuser back-focus

When a rig change occurs, all flats taken before that date are invalid for lights taken after that date.

## State File: `flat-state.yaml`

A YAML file tracks rig change dates, **keyed by blink directory path**. This eliminates any guesswork about equipment matching -- the directory the user is processing defines the scope.

The CLI accepts `--flat-state <path>` pointing to this file. The path must be explicitly provided; there is no default location. The file is both read and written by the tool.

### Format

```yaml
# Rig change dates for ap-copy-master-to-blink
# Key: blink directory path (as provided to CLI)
# Value: cutoff date (flats must be from this date or later)

"/mnt/data/RedCat51@f4.9+ASI2600MM/10_Blink": "2025-09-01"
"/mnt/data/Askar80PHQ@f6+ASI533MC/10_Blink": "2025-06-15"
```

### Semantics

For a given blink directory, if an entry exists in the state file, only flats with `flat_date >= cutoff_date` are valid. Flats from before the cutoff are automatically rejected without prompting.

If no entry exists for a blink directory, any old flat is a candidate (subject to user confirmation on first use).

### File Lifecycle

- Created automatically on first interactive "no" response if it does not exist
- Updated when the user records a new rig change
- Can be hand-edited
- If `--flat-state` is not provided, the tool falls back to exact-date matching only (current behavior preserved)

## CLI

```
--flat-state <path>   Path to flat state file (YAML). Enables flexible flat
                      matching with rig change tracking. Required for non-exact
                      flat matching. File is read and written by the tool.
```

No other flat-related flags are needed.

## Matching Algorithm

### Step 1: Exact Date Match

Search for a flat matching all criteria including exact DATE. If found, use it. Done.

### Step 2: Check for `--flat-state`

If `--flat-state` not provided, mark as missing (current behavior). Stop.

### Step 3: Find Candidate Old Flats

Search for flats matching all non-date criteria with `flat_date < light_date`, sorted most-recent-first.

### Step 4: Apply Cutoff from State File

Look up the blink directory in the state file.

- **Cutoff exists**: Discard any flat with `flat_date < cutoff_date`. If candidates remain, use the most recent valid flat. Done.
- **No cutoff**: Proceed to interactive prompt.

### Step 5: Interactive Prompt (Once Per Blink Directory)

If running interactively (terminal attached, not `--quiet`):

```
No exact flat match. Oldest light: 2025-08-20, newest flat: 2025-08-03.

Use old flats for this blink directory? [y/n]
```

**"y"**: Use old flats for this run. No state file change. Future runs will prompt again unless a cutoff is recorded.

**"n"**: Record the oldest light date as the cutoff in the state file:

```yaml
"/mnt/data/RedCat51@f4.9+ASI2600MM/10_Blink": "2025-08-20"
```

Old flats are now blocked. Try newer flats (Step 6).

**`--quiet` or non-interactive**: Skip old flats. Mark as missing.

### Step 6: Try Newer Flats

If no valid old flat, search for flats with `flat_date > light_date` and `flat_date >= cutoff_date` (if cutoff exists). Use the oldest one.

### Step 7: No Match

If no flat found, mark as missing and log a warning.

## Decision Flowchart

```
Exact date flat exists?
  |
  +-- YES --> use it
  |
  +-- NO --> --flat-state provided?
              |
              +-- NO --> mark missing
              |
              +-- YES --> find old flats
                          |
                          +-- cutoff in state file?
                              |
                              +-- YES --> filter by cutoff
                              |           |
                              |           +-- candidates remain? --> use most recent
                              |           |
                              |           +-- none remain --> try newer flats
                              |
                              +-- NO --> interactive?
                                          |
                                          +-- YES --> prompt user (once per blink dir)
                                          |           |
                                          |           +-- "y" --> use old flat
                                          |           |
                                          |           +-- "n" --> record cutoff,
                                          |                       try newer flats
                                          |
                                          +-- NO --> mark missing
```

## Examples

### Example 1: First Run, User Accepts Old Flats

Blink directory: `/data/RedCat51@f4.9+ASI2600MM/10_Blink`
Light date: 2025-08-20, available flat: 2025-08-03
No entry in state file.

1. Exact match: not found
2. Old flat found: 2025-08-03
3. No cutoff in state file
4. Prompt: "Use old flats for this blink directory? [y/n]"
5. User says "y": flat from 2025-08-03 is used

Next run: same prompt (no cutoff was recorded).

### Example 2: User Records Rig Change

Same setup, but user says "n" at the prompt.

1. State file updated: `"/data/RedCat51@f4.9+ASI2600MM/10_Blink": "2025-08-20"`
2. Flat from 2025-08-03 is blocked (before cutoff)
3. Try newer flats: none found
4. Mark missing

Later: user takes new flats on 2025-09-01. Next run finds flat >= cutoff. Used automatically.

### Example 3: Cutoff Already Recorded

State file has cutoff 2025-09-01 for this blink directory.
Processing lights from 2025-09-15.

1. Exact match: not found
2. Old flats: 2025-08-03 (before cutoff), 2025-09-05 (after cutoff)
3. Apply cutoff: only 2025-09-05 survives
4. Use 2025-09-05 automatically (no prompt needed)

### Example 4: Processing Old Data

State file has cutoff 2025-09-01.
Processing old lights from 2025-07-10.

1. Light date 2025-07-10 < cutoff 2025-09-01
2. The cutoff doesn't apply to lights from before the rig change
3. Old flat from 2025-07-01 is valid
4. Prompt user (or use if they previously said "y" for this date range)

Wait -- this is a complication. Does the cutoff apply based on light date or universally?

**Decision**: The cutoff means "for lights from this date onward, flats must be from this date or later." Lights from before the cutoff date can still use older flats. This requires comparing `light_date >= cutoff_date` before applying the cutoff filter.

Updated logic in Step 4:
- If `cutoff exists AND light_date >= cutoff_date`: apply cutoff filter
- Otherwise: no cutoff applies

### Example 5: Quiet Mode

Running with `--quiet`. No exact match. Old flats exist but no cutoff confirms them.

1. Non-interactive: cannot prompt
2. Mark missing

This is intentionally conservative.

## Backwards Compatibility

- Without `--flat-state`: behavior identical to current (exact date only)
- State file is opt-in
- No changes to library structure or metadata format

## Implementation Notes

### State File Key

The key is the blink directory path as provided to the CLI (after environment variable expansion and path resolution). This ensures consistency across runs.

### Prompt Frequency

Prompt once per blink directory per run. If the user says "y" or "n", that decision applies to all filters/dates within that blink directory for the current run.

### Dependencies

- PyYAML for state file I/O (already available via astropy)

### Files to Modify

- `ap_copy_master_to_blink/__main__.py` -- add `--flat-state` arg
- `ap_copy_master_to_blink/matching.py` -- accept cutoff date, implement filtering
- `ap_copy_master_to_blink/copy_masters.py` -- handle prompting, state file I/O
- New: `ap_copy_master_to_blink/flat_state.py` -- state file read/write

### Testing Strategy

- Unit tests for state file parsing
- Unit tests for cutoff filtering logic
- Unit tests for prompt flow (mocked stdin)
- Integration test with state file
- Existing tests unchanged when `--flat-state` not provided
