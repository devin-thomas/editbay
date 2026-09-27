#!/usr/bin/env bash
# Mirror editbay's skills, tools, brands, config example, and docs into a devin-thomas/private-skills checkout.
# editbay is the source of truth: edit here, then run this, review the diff there, commit there.
#   scripts/sync-private-skills.sh [PRIVATE_SKILLS_DIR]   (default: ../private-skills)
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
dest_root="${1:-$here/../private-skills}"
dest="$dest_root/Research/editbay"
[ -d "$dest_root/.git" ] || { echo "not a git checkout: $dest_root" >&2; exit 2; }
mkdir -p "$dest"
for d in skills tools brands config docs .claude-plugin; do
  rsync -a --delete --exclude "__pycache__" --exclude ".DS_Store" "$here/$d/" "$dest/$d/"
done
cp "$here/README.md" "$dest/README.md"
cp "$here/AGENTS.md" "$dest/AGENTS.md"
cp "$here/CHANGELOG.md" "$dest/CHANGELOG.md"
commit="$(git -C "$here" rev-parse --short HEAD)"
dirty="$(git -C "$here" status --porcelain | wc -l | tr -d ' ')"
cat > "$dest/SOURCE.md" <<MD
# Source

Synced from [devin-thomas/editbay](https://github.com/devin-thomas/editbay) at commit \`$commit\`$( [ "$dirty" != "0" ] && echo " plus $dirty uncommitted change(s)" ) on $(date +%Y-%m-%d).
Edit skills in editbay, not here; re-run \`scripts/sync-private-skills.sh\` there to refresh this copy.
Examples (with their records) live only in editbay.
MD
echo "synced editbay@$commit -> $dest"
