# Flat Frame Matching: Design Document

**Status**: Proposal
**Issue**: [#5](https://github.com/jewzaam/ap-copy-master-to-blink/issues/5)
**Date**: 2026-02-14

## Problem

The tool requires exact DATE match for flats. This is too strict. Flats remain valid until the imaging train physically changes. Calendar proximity is irrelevant; equipment continuity is what matters.

## Solution Overview

When no exact-date flat exists:

1. Find all candidate flat dates
2. Remove any that are too old (before a recorded cutoff)
3. Present remaining dates to the user
4. User selects which flat to use
5. Record the selection to avoid re-prompting

## State File

A YAML file keyed by blink directory path. Tracks the oldest valid flat date for each directory.

```yaml
# Oldest valid flat date per blink directory
# Flats from this date or later are usable; older flats are rejected

"/mnt/data/RedCat51@f4.9+ASI2600MM/10_Blink": "2025-09-01"
"/mnt/data/Askar80PHQ@f6+ASI533MC/10_Blink": "2025-06-15"
```

**No entry** = no cutoff = all flat dates are candidates (treated as cutoff of epoch).

**Entry exists** = only flats with `date >= entry` are candidates.

## CLI

```
--flat-state <path>   Path to flat state file (YAML). Enables flexible flat
                      matching. File is read and written by the tool.
                      Required; no default location.
```

Without `--flat-state`: exact date match only (current behavior).

## Algorithm

### Step 1: Exact Match

Search for flat matching all criteria including exact DATE. If found, use it. Done.

### Step 2: Gather Candidates

If `--flat-state` not provided, mark missing. Stop.

Otherwise, find all flats matching non-date criteria (camera, optic, filter, gain, offset, settemp, readoutmode, focallen). Collect their dates.

### Step 3: Apply Cutoff

Look up blink directory in state file.

- **Entry exists**: Remove any flat dates older than the cutoff.
- **No entry**: All dates remain candidates.

### Step 4: Categorize

Split remaining candidates into:

- **Older**: `flat_date < light_date`, sorted newest-first
- **Newer**: `flat_date > light_date`, sorted oldest-first

### Step 5: Present to User

If running interactively (not `--quiet`):

```
No exact flat for light date 2025-08-20.

Available flat dates:
  [1] 2025-08-15  (5 days older) ← recommended
  [2] 2025-08-03  (17 days older)
  [3] 2025-08-25  (5 days newer)
  [4] 2025-09-01  (12 days newer)
  [0] None of these work (record rig change)

Select [1]:
```

Default recommendation: newest older flat, or oldest newer flat if no older candidates.

### Step 6: Handle Selection

**User selects a flat date**:
- Use that flat
- Update state file: set cutoff to the selected date (flats from this date onward are valid)
- Future runs with `flat_date >= cutoff` proceed without prompting

**User selects "none work" (0)**:
- Record the light date as the new cutoff
- This means: "rig changed, need flats from this date or later"
- Mark flat as missing
- Future runs will only consider flats >= light_date

**`--quiet` or non-interactive**:
- If state file has a cutoff and valid candidates exist: use newest older (or oldest newer)
- Otherwise: mark missing

## Examples

### Example 1: First Run, No State Entry

Light date: 2025-08-20
Available flats: 2025-08-03, 2025-08-15, 2025-09-01
State file: no entry for this blink directory

1. No cutoff → all three dates are candidates
2. Prompt user with list
3. User selects 2025-08-15
4. State file updated: `"/path/to/blink": "2025-08-15"`
5. Flat from 2025-08-15 used

### Example 2: Subsequent Run, State Entry Exists

Light date: 2025-09-10
Available flats: 2025-08-03, 2025-08-15, 2025-09-01
State file: `"/path/to/blink": "2025-08-15"`

1. Cutoff is 2025-08-15 → reject 2025-08-03
2. Remaining: 2025-08-15, 2025-09-01
3. Both are older than light (2025-09-10)
4. Newest older is 2025-09-01 → use automatically (no prompt needed, cutoff confirms validity)

### Example 3: User Indicates Rig Change

Light date: 2025-10-01
Available flats: 2025-08-15, 2025-09-01
State file: `"/path/to/blink": "2025-08-15"`

1. Cutoff 2025-08-15 → both candidates valid
2. Prompt user (both are older than light)
3. User selects "0" (none work - rig changed)
4. State file updated: `"/path/to/blink": "2025-10-01"`
5. Flat marked missing

Later: user takes new flats on 2025-10-05. Next run finds 2025-10-05 >= cutoff 2025-10-01. Used automatically.

### Example 4: Only Newer Flats Available

Light date: 2025-07-01
Available flats: 2025-08-15, 2025-09-01
State file: `"/path/to/blink": "2025-08-15"`

1. Both flats are newer than light date
2. Oldest newer is 2025-08-15
3. Prompt user (or auto-select in quiet mode since cutoff confirms 2025-08-15 is valid)

### Example 5: Quiet Mode

Running with `--quiet`. State file has cutoff 2025-08-15.

1. Find candidates >= cutoff
2. If any exist: use newest older than light (or oldest newer)
3. If none: mark missing

No prompting. Cutoff from state file determines validity.

## State File Semantics

The stored date means: **"Flats from this date or later are valid for this blink directory."**

- When user selects a flat, the state is updated to that flat's date
- When user says "none work", the state is updated to the light's date
- Subsequent runs auto-accept flats >= stored date without prompting

This accumulates trust: once a flat date is validated, it stays validated. If the user later changes the rig, they select "none work" and the cutoff advances.

## Prompt Frequency

Once per blink directory per run. The decision applies to all lights in that directory.

## Backwards Compatibility

- Without `--flat-state`: exact match only (no change)
- State file is opt-in
- No changes to library structure

## Implementation Notes

### Files to Modify

- `__main__.py` – add `--flat-state` arg
- `copy_masters.py` – prompt logic, state file I/O
- `matching.py` – return candidate flat dates, accept cutoff filter
- New: `flat_state.py` – state file read/write helpers

### Dependencies

- PyYAML (already available via astropy)
