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

When a rig change occurs, all flats taken before that date are invalid for lights taken after that date. All flats taken after that date remain valid for lights taken after that date.

A **rig** is identified by the combination of camera + optic + focallen -- the equipment parameters that define the optical path. A rig change invalidates flats for ALL filters on that rig, not just one.

## State File: `flat-state.yaml`

A YAML file tracks rig change history. The CLI accepts `--flat-state <path>` pointing to this file. The file is both read and written by the tool (interactive decisions are persisted).

### Format

```yaml
# Rig change history for ap-copy-master-to-blink
# Each entry records when an imaging train change invalidated prior flats.
# Managed automatically by the tool; can also be edited by hand.
rig_changes:
  - camera: "ASI2600MM"
    optic: "RedCat51"
    focallen: "250"
    date: "2025-06-15"
    reason: "Replaced filter wheel"

  - camera: "ASI2600MM"
    optic: "RedCat51"
    focallen: "250"
    date: "2026-01-20"
    reason: "Adjusted back-focus spacing"
```

### Semantics

For a given rig (camera + optic + focallen), the most recent `rig_changes` entry with `date <= light_date` defines the **cutoff date**. Only flats with `flat_date >= cutoff_date` are valid for that light.

If no rig change entry exists for a rig, there is no cutoff -- any old flat is a candidate (subject to user confirmation; see interactive flow below).

### File Lifecycle

- Created automatically on first interactive "no" response if it does not exist
- Appended to when the user records a new rig change
- Can be hand-edited (add entries for known historical changes)
- If the file path is not provided via CLI, the tool falls back to exact-date matching only (current behavior preserved)

## CLI Changes

```
--flat-state <path>   Path to flat state file (YAML). Enables flexible flat
                      matching with rig change tracking. The file is read for
                      existing rig change dates and written when the user
                      records new changes interactively.
```

No other flat-related flags are needed. The `--flat-state` flag is the single entry point for the entire feature.

## Matching Algorithm

For each light frame configuration that needs a flat:

### Step 1: Exact Date Match

Search for a flat matching all criteria including exact DATE. If found, use it. Done.

### Step 2: Find Candidate Old Flats

If no exact match, search for flats matching all non-date criteria. From those, collect flats with `flat_date < light_date`, sorted most-recent-first.

### Step 3: Apply Rig Change Cutoff

Look up the rig (camera + optic + focallen) in the state file. Find the most recent rig change entry with `change_date <= light_date`. This is the **cutoff date**.

- If a cutoff date exists: discard any candidate flat with `flat_date < cutoff_date`. Only flats from on-or-after the cutoff survive.
- If no cutoff date exists: all candidate old flats survive (proceed to Step 4).

If no candidates survive the cutoff, check for newer flats (Step 5).

### Step 4: Interactive Confirmation (Old Flats)

If running interactively (terminal attached, not `--quiet`), and candidate old flats exist but no rig change entry covers this situation:

```
No exact flat for filter=Ha on 2025-08-20.
Best available: flat from 2025-08-03 (17 days older).

Use old flats for this rig? [y/n]
  y = use old flats (no rig change occurred)
  n = record rig change (old flats invalid from this date forward)
```

**If "y"**: Use the most recent old flat. Continue processing. No state file change. Future runs with the same or older light dates will find the same flat without prompting (because the flat pre-dates the light and no cutoff blocks it).

**If "n"**: Record a new rig change entry in the state file:

```yaml
  - camera: "ASI2600MM"
    optic: "RedCat51"
    focallen: "250"
    date: "2025-08-20"
    reason: "User indicated rig change (recorded automatically)"
```

The light date becomes the cutoff. This flat (and all older flats) are now invalid for this light and all future lights on this rig from this date onward. Mark flat as missing. Continue processing.

**If `--quiet` or non-interactive**: Skip old flats entirely. Mark as missing. (Conservative default -- never silently use a potentially invalid flat.)

### Step 5: Try Newer Flats

If no valid old flat was found or usable, search for flats with `flat_date > light_date` that are on-or-after the cutoff date. Use the oldest one (closest to the light date). This handles the case where the user took new flats after a rig change but is processing older light data.

### Step 6: No Match

If no flat found at any step, mark as missing and log a warning (current behavior).

## Decision Flowchart

```
Exact date flat exists?
  |
  +-- YES --> use it
  |
  +-- NO --> --flat-state provided?
              |
              +-- NO --> mark missing (current behavior)
              |
              +-- YES --> find old flats (date < light date)
                          |
                          +-- apply rig change cutoff from state file
                          |
                          +-- candidates remain?
                              |
                              +-- YES --> cutoff was applied?
                              |           |
                              |           +-- YES --> use most recent valid flat
                              |           |
                              |           +-- NO --> interactive?
                              |                       |
                              |                       +-- YES --> prompt user
                              |                       |           |
                              |                       |           +-- "y" --> use flat
                              |                       |           |
                              |                       |           +-- "n" --> record rig
                              |                       |                       change, try
                              |                       |                       newer flats
                              |                       |
                              |                       +-- NO --> mark missing
                              |
                              +-- NO --> try newer flats (after cutoff)
                                          |
                                          +-- found --> use oldest newer flat
                                          |
                                          +-- none --> mark missing
```

## Examples

### Example 1: Normal Operation, No Rig Changes

User images M31 on 2025-08-20 with Ha filter. Library has a flat from 2025-08-03. No state file entry for this rig.

1. Exact match for 2025-08-20: not found
2. Old flat from 2025-08-03: found
3. No rig change cutoff: all old flats valid
4. Prompt: "Use old flats for this rig? [y/n]"
5. User says "y": flat from 2025-08-03 is used

Next run with same or older data: flat from 2025-08-03 is used again without prompting (no cutoff blocks it, exact match still fails, old flat still valid).

### Example 2: Rig Change Recorded

User changed their filter wheel on 2025-09-01. They process lights from 2025-09-05. State file has:

```yaml
rig_changes:
  - camera: "ASI2600MM"
    optic: "RedCat51"
    focallen: "250"
    date: "2025-09-01"
    reason: "Replaced filter wheel"
```

1. Exact match for 2025-09-05: not found
2. Old flat candidates: flat from 2025-08-03
3. Cutoff date is 2025-09-01. Flat from 2025-08-03 < cutoff. Discarded.
4. No valid old flats. Try newer flats.
5. Newer flat from 2025-09-10 exists and is >= cutoff. Use it.

### Example 3: Interactive "No" Creates Cutoff

User processes lights from 2025-11-15. Old flat from 2025-10-01 is found. No state file entry.

1. Prompt: "Use old flats for this rig? [y/n]"
2. User says "n" (they know they changed something)
3. State file updated with cutoff 2025-11-15
4. Flat from 2025-10-01 is now blocked. Try newer flats.
5. No newer flats found. Mark missing.

Later: user takes new flats on 2025-11-20. Next run finds flat from 2025-11-20 >= cutoff 2025-11-15. Used without prompting.

### Example 4: Processing Old Data After Rig Change

State file has cutoff 2025-09-01. User processes old lights from 2025-07-10 (before the rig change).

1. Cutoff for this rig: 2025-09-01. But light date 2025-07-10 < cutoff date.
2. Most recent rig change with `change_date <= 2025-07-10`: none.
3. No cutoff applies. Old flat from 2025-07-01 is valid. Use it (with prompt if no prior confirmation).

### Example 5: Quiet/Non-Interactive Mode

Running with `--quiet`. No exact flat match. Old flats exist but no rig change cutoff covers them.

1. Old flat found, but no cutoff confirms validity
2. Non-interactive: cannot prompt. Skip.
3. Mark missing.

This is intentionally conservative. In batch/automated contexts, silently using a potentially invalid flat is worse than reporting it missing.

## Stats and Summary Output

When flexible matching is active, the summary could distinguish between exact and flexible matches:

```
Flats:  3 found (2 exact, 1 older match)
```

This is optional polish. The core stats (`flats_present`, `flats_needed`) remain unchanged.

## Backwards Compatibility

- Without `--flat-state`: behavior is identical to current (exact date only)
- State file is opt-in; existing scripts and workflows are unaffected
- The removed `--flat-date-tolerance` flag (from initial implementation) is replaced entirely
- No changes to library structure or metadata format

## Implementation Notes

### Dependencies

- PyYAML (for state file read/write) -- already an indirect dependency via astropy
- No new external dependencies expected

### Files to Modify

- `ap_copy_master_to_blink/__main__.py` -- add `--flat-state` CLI arg, pass to processing
- `ap_copy_master_to_blink/matching.py` -- update `find_matching_flat()` to accept state data, implement cutoff logic
- `ap_copy_master_to_blink/copy_masters.py` -- pass state data through, handle interactive prompting in orchestration layer
- New: `ap_copy_master_to_blink/flat_state.py` -- state file read/write/query logic

### Testing Strategy

- Unit tests for state file parsing and rig change lookup
- Unit tests for cutoff filtering in flat matching
- Unit tests for interactive prompt flow (mocked stdin)
- Integration test for full flow with state file
- Ensure all existing tests pass unchanged when `--flat-state` is not provided

### Open Questions

1. **Prompt grouping**: Should the tool prompt once per rig per run, or once per filter? Since rig changes affect all filters, prompting once per rig seems right. If user says "n" for Ha, it should apply to OIII and SII on the same rig too.

2. **State file location**: Should the tool suggest a default location (e.g., `~/.config/ap-copy-master-to-blink/flat-state.yaml`) or always require explicit `--flat-state`? Explicit is simpler and more predictable.

3. **Reason field**: The `reason` field in rig change entries is informational. Should the interactive prompt ask for a reason, or auto-populate with "User indicated rig change"?

4. **Multiple rig changes same date**: The design handles this naturally -- multiple entries for the same rig with different dates are fine. The most recent one <= light date wins.
