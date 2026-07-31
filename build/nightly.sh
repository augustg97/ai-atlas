#!/bin/bash
# nightly.sh — the AI Atlas daily chain (register D1). Run AFTER the vault's
# 09:22 ingest-reflect cycle. Refuses to publish on any gate regression.
# Exit codes: 0 published+verified · 1 gate refused · 2 emit/bake failed ·
# 3 push/verify failed.
set -u
ROOT="/Users/augustgweon/AI Atlas"
VAULT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/August's Vault"
cd "$ROOT/Research/modeling" || exit 2

# incremental embedding refresh (checksum-gated; seconds for a normal day),
# then project any new pages INTO the frozen datum — never a re-layout
K=$(grep '^export VOYAGE_API_KEY=' ~/.zshrc | tail -1 | cut -d= -f2- | tr -d '"'"'"'')
if [ -n "$K" ]; then
  (cd "$VAULT" && VOYAGE_API_KEY="$K" python3 bin/build-embedding-index.py) \
    || echo "embed refresh failed — continuing with existing index"
  python3 datum_build.py --place-new || echo "place-new failed — gate will say"
else
  echo "no VOYAGE key found — skipping embed refresh (gate will flag unpositioned pages)"
fi

python3 emit.py || exit 2
python3 witness_epoch.py || exit 2
python3 fields_bake.py || exit 2

cd "$ROOT" || exit 2
python3 build/build_site.py || exit 1          # the gate lives in here

git add -A
git commit -q -m "Nightly emit $(date +%F)" || true   # no-op commit is fine
git push -q origin main || exit 3

sleep 90                                        # let Pages build
LIVE=$(curl -s https://augustg97.github.io/ai-atlas/ | grep -o 'DATA_V = "[^"]*"' | head -1)
WANT=$(grep -o 'DATA_V = "[^"]*"' web/index.html | head -1)
echo "live: $LIVE / want: $WANT"
[ "$LIVE" = "$WANT" ] || exit 3
echo "nightly OK $(date +%F-%H%M)"
