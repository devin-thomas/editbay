# EditBay showcase and MCP

Canonical showcase: `https://editbay.uppercut-labs.com`

Streamable HTTP MCP: `https://editbay.uppercut-labs.com/mcp`

The MCP is read-only and unauthenticated. It serves documentation and the Python scripts as source text; it cannot run them, operate an editor, upload or render media, read a user's files, or call a paid provider.

## Build and verify

Use Node 24+, Python 3.10+, and Git. Start from a clean standalone public checkout with a committed `PUBLIC_RELEASE.json` and explicit `public-documents.json`.

```bash
npm ci
npm run check
npm run preview
# From another terminal, with the local preview running:
npm run test:browser -- http://127.0.0.1:8793
```

`npm run check` builds the approved corpus, checks the entire release tree and the served document bytes, typechecks, runs SDK handshake/resource tests, and creates a dry-run Worker bundle. It does not deploy. Browser acceptance is a separate command against a running preview.

After checks and release approval, `npm run deploy` repeats the checks and deploys the combined site and guidance service. Deployment credentials stay in the operator's environment. There is no runtime credential or database binding and no Cloudflare Access dependency.

The Worker name is intentionally stable. Deploying the reviewed package updates the existing service as well as its custom domain, avoiding a second live copy of an outdated documentation corpus. Verify both entry points during a migration; do not roll back to a revision that predates the privacy boundary.

The page uses no recorded media. Add a recorded showcase only after approving its media rights, visible information, and metadata.
