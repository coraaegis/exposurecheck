#!/usr/bin/env sh
# Commit with a timezone-neutralised date so this PUBLIC repo never leaks the
# author's timezone or daily work rhythm. Every commit is normalised to noon UTC
# on its calendar date (offset +0000, fixed time-of-day).
# Usage: scripts/git-commit-utc.sh "commit message"
set -e
D="$(date -u +%Y-%m-%dT12:00:00+0000)"
GIT_AUTHOR_DATE="$D" GIT_COMMITTER_DATE="$D" TZ=UTC git commit -m "$1"
