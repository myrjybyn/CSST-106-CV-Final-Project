# Laptop benchmark — complete

Completed 30 October 2026, 01:09 AM (Asia/Manila). All eight baseline/main runs succeeded; all 3,400 annotated output frames decoded with the expected counts. Aggregates were independently recalculated from the uploaded log.

Hardware: AMD Athlon Silver 3050U with Radeon Graphics; 2 reported logical CPUs; 5.94 GiB reported RAM; Windows 11 Home Single Language; Balanced power mode. Python 3.13.0 differs from cloud Python 3.12.14; installed dependency parity is unverified.

| Method | Processing FPS | Processing ms/frame | Full-run FPS |
| --- | ---: | ---: | ---: |
| Baseline | 13.32 | 75.08 | 6.81 |
| Main | 12.83 | 77.93 | 7.84 |

Processing throughput is total frames divided by summed processing time across all four clips. It excludes startup, decoding, drawing and encoding; full-run throughput includes those costs. These are single sequential measurements, baseline before main per clip. Timing variability and startup costs prevent a speed-improvement claim. Main throughput is below the input clips' 30–50 FPS.

Form predictions and repetition counts match the cloud results: correct for push-up, squat and lunge; abstention for jumping-jack form. Main counts are 2, 4, 0 and 1 versus user references 4, 4, 3 and 10. Count MAE remains 3.50 reps/clip; form agreement remains 75% counting abstention as a miss. All four references are correct, so incorrect-form detection remains unmeasured.

The editable Phase3_Testing_Report_Editable.docx now includes laptop throughput and hardware. Per-exercise timings are in laptop_comparison.csv; the original uploaded log is preserved as laptop_test_log.json. Original cloud measurements remain unchanged.
