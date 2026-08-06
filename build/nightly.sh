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
python3 witness_statelaw.py || exit 2   # T7: the state-law counter

# v2: the forecast breathes — classify the day's record, update the weights
# (tiered impacts, attributed), re-ground, re-emit the distribution
cd "$ROOT/Research/timelines" || exit 2
python3 nightly_update.py || exit 2
python3 wiki_grounding.py || exit 2
python3 forecast_emit.py || exit 2
cd "$ROOT/Research/modeling" || exit 2

cd "$ROOT" || exit 2
python3 build/build_site.py || exit 1          # the gate lives in here

git add -A
git commit -q -m "Nightly emit $(date +%F)" || true   # no-op commit is fine
git push -q origin main || exit 3

# Verify the LIVE artefact. Two things can go wrong and they need different
# answers, which is why this is no longer a fixed sleep and a stamp compare.
# On 2026-08-06 the deploy FAILED on a GitHub-side OIDC token error while the
# chain reported only "live != want", and the real cause took a `gh run view`
# to find. A slow deploy wants patience; a failed one wants reporting.
WANT=$(grep -o 'DATA_V = "[^"]*"' web/index.html | head -1)
SHA=$(git rev-parse HEAD)
for i in $(seq 1 40); do                        # up to ~10 min
  LIVE=$(curl -s -H 'Cache-Control: no-cache' \
         https://augustg97.github.io/ai-atlas/ \
         | grep -o 'DATA_V = "[^"]*"' | head -1)
  [ "$LIVE" = "$WANT" ] && { echo "live: $LIVE / want: $WANT"
                             echo "nightly OK $(date +%F-%H%M)"; exit 0; }
  CONC=$(gh run list --limit 20 --json headSha,conclusion,status,databaseId \
         --jq "[.[]|select(.headSha==\"$SHA\")][0]
               |\"\(.status)/\(.conclusion//\"-\")/\(.databaseId)\"" \
         2>/dev/null)
  case "$CONC" in
    completed/failure/*|completed/cancelled/*|completed/timed_out/*)
      echo "live: $LIVE / want: $WANT"
      echo "DEPLOY FAILED for $SHA — run ${CONC##*/}"
      gh run view "${CONC##*/}" --log-failed 2>/dev/null | tail -12
      echo "the build is correct and pushed; the hosting step is not."
      exit 3;;
  esac
  sleep 15
done
echo "live: $LIVE / want: $WANT"
echo "DEPLOY PENDING after 10 min for $SHA (last seen: ${CONC:-unknown})"
exit 3
