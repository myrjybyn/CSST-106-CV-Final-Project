# Guided exercise sessions

This is the simplified desktop flow for the school demonstration. It uses fixed
2D geometry checks and presents an estimate, without claiming a new accuracy score.

## Use the app

1. Run `python app.py` from the project folder.
2. Choose Squat, Push-up, Lunge, or Jumping jack.
3. Enter a target between 1 and 100 repetitions.
4. Press **Start Session**. Use the 3-second countdown to get into position.
5. Complete your exercise. The screen shows the counted reps against the target.
6. At the target, recording stops automatically. The result screen shows **Good**,
   **Bad — needs improvement**, or **Unable to assess — try again**, plus tips.

Use a side view for squat, push-up and lunge, and a front view for jumping jacks.
Keep the required joints and your whole body visible throughout the movement.
**End Session** or Escape finishes early and assesses the available movement.
The result marks an early finish separately from reaching the target. Every new
session starts with a fresh count. Sessions also stop after 10 minutes.

## Simple exercise criteria

The assessment uses the 10th and 90th percentiles of usable measurements to reduce
the influence of a single noisy frame. These are projected image angles and fixed
project rules, not universal coaching targets.

| Exercise | Checks used for the overall estimate |
| --- | --- |
| Squat | Knee angle reaches 100° or less and returns to at least 145°; active trunk lean stays at 60° or less. |
| Push-up | Elbow angle reaches 100° or less and returns to at least 150°; shoulder–hip–ankle alignment stays at least 155°. |
| Lunge | The smaller knee angle reaches 110° or less and returns to at least 145°; active trunk lean stays at 45° or less. |
| Jumping jack | Arms reach at least 140° and return to 40° or less; ankle spacing opens to at least 1.8 shoulder widths and closes to 1.3 or less; large left/right arm differences do not persist through more than 20% of usable frames. |

For jumping jacks, a large arm difference means more than 35° while at least one
arm is above 60°. Active trunk lean is measured during lowered positions.
**Good** means none of the configured checks flagged the observed session.
**Bad** means at least one check flagged it; the result gives a tip for each issue.

At least 10 usable frames, 50% usable pose coverage, and 20° of observed joint
movement are required. Otherwise the app asks for another attempt. Initial
standing/setup time is excluded from the form summary, retaining a short lead-in
to preserve the starting position. Repetition counting remains separate from the
form checks: counting a rep does not mean that its form passed.
The guided counter uses broader movement endpoints than the form criteria so a
shallow attempt can still count and receive a depth tip afterward. Its squat and
lunge endpoints are 150°/130°; push-ups use 145°/125°. Jumping jacks use 55°/110°
arm endpoints and 1.4/1.6 shoulder-width foot spacing. Dwell, missing-pose reset
and hysteresis checks remain active. The CLI keeps its original counting limits.

## Saved files

Each recording gets its own folder under `outputs/sessions/`:

- `recording.mp4`: the session video, in the original camera orientation, without
  the preview skeleton or audio. Mirroring changes only the on-screen preview.
- `summary.json`: exercise, target and counted reps, duration, end reason,
  overall estimate, measured values, and improvement tips.

Video is paced at 20 FPS using elapsed time, repeating or skipping frames when
processing cadence varies. Form assessment uses the actual processed frames.
Cancelling during the countdown creates no recording. A camera/encoder failure
shows an error; any partial recording stays in its session folder.

## Demonstrate and check it

For a classroom demonstration, try a short target such as 3–5 reps. Check that
the count starts at zero, the recording ends at the target, the saved video opens,
and the summary names the selected exercise and achieved count. Also demonstrate
an early finish and a missing-pose retry. Use previously recorded examples to
illustrate flagged movement rather than asking someone to force unsafe technique.

The guided GUI does not use `config/form_rules.json` for its final result.
Historical calibration reports and the CLI evaluation remain separate evidence;
their accuracy figures do not validate these new session rules. For the school
report, describe this as **pose estimation, repetition counting, and rule-based
whole-session form estimation**. Report demonstrated behavior and limitations
without inventing an accuracy percentage.
