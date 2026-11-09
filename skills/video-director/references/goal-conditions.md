# Goal conditions for long runs

Claude Code's `/goal` keeps a session working until a condition holds. A small model checks the condition after
each turn by reading the transcript only: it runs no tools. So a goal must name evidence the run prints.

Good:

```
/goal The edit in <folder> is done when all of these lines have been printed in this session, in this order:
(1) verify_report.py output ending "report: qa/REPORT.md" with no FAIL line; (2) a loudness.py line for every file
in deliver/ ending "OK"; (3) deliver.py output "delivered N files to deliver"; (4) the path to deliver/DELIVERY.md.
Stop and report if the same gate fails three times, or after 60 turns.
```

Weak: "make it look great", "until the video is perfect", "verify everything" (nothing printed can prove them).

- Put the turn cap and the failure stop in the condition itself.
- Keep human boundaries outside the goal: a goal never authorises spending, publishing, or a voice clone.
- In an unattended session, also set the permission mode you intend; the goal does not change it.
