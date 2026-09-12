# Review Patterns

## What to capture from each skill run

Capture these fields whenever possible:

- `skill`: the skill name used
- `request`: what the user asked for
- `result`: what happened
- `worked`: what was effective
- `failed`: what caused friction
- `change`: what should be changed next
- `tags`: short labels like `missing-example`, `bad-trigger`, `too-verbose`, `needs-script`

## What counts as a strong improvement signal

Treat these as high signal:

- the same failure appears in three or more runs
- the user has to restate the same intent repeatedly
- the skill triggers too late or not at all
- the skill keeps requiring the same manual steps
- the skill needs the same explanation every time

Treat these as weaker signals:

- a single vague complaint
- taste-only preferences with no effect on success
- requests that are outside the skill's intended scope

## Preferred order of fixes

1. Fix trigger description in frontmatter
2. Add or tighten workflow steps in `SKILL.md`
3. Add a reusable script when manual work repeats
4. Add a focused reference file when context is missing
5. Split a bloated skill into clearer sections only if needed

## Good review questions

Ask these when preparing a patch:

- Did the skill fail to trigger, or fail after triggering?
- Did it lack an example, a script, or a decision rule?
- Was the user blocked by setup, by wording, or by missing automation?
- Would one small edit solve this for future runs?
