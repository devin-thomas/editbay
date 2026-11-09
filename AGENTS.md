# EditBay contributor contract

This is the public, portable editing toolkit. Skills describe workflows; Python tools perform local operations; the hosted MCP serves an explicit list of documentation only.

Keep personal profiles, credentials, voice assets, provider logs, recordings, generated productions, and workstation configuration outside this repository. Use local configuration and neutral placeholders. Never add a production artifact as a test fixture without a privacy and rights review.

Run `python3 scripts/check_public.py` and `python3 scripts/validate.py` after changes. Run the full MCP checks for service changes. Test negative controls; mark any checks not actually run as pending. Do not claim media or device acceptance from static analysis.

Publishing a new document requires an explicit change to `mcp/public-documents.json`. The content build reads committed public bytes, refuses a dirty or nested checkout, and records the public commit and document hashes.

The hosted service must never gain local filesystem, SSH, shell, upload, GPU, model, or credential capabilities. Paid services and persistent settings changes require the user's authorization.
