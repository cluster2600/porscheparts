#!/bin/sh
set -eu
# Destination must be a new directory: never overwrite a source checkout.
test "$#" -eq 1 || { echo 'Usage: bootstrap.sh NEW_DIRECTORY' >&2; exit 2; }
target=$1
test ! -e "$target" || { echo 'Destination already exists' >&2; exit 2; }
mkdir -p "$target"
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
while read -r repository commit rest; do
    case "$repository" in ''|'#'*) continue ;; esac
    git init -q "$target/$repository"
    git -C "$target/$repository" remote add origin "https://github.com/leap71/$repository.git"
    git -C "$target/$repository" fetch -q --depth 1 origin "$commit"
    git -C "$target/$repository" checkout -q --detach FETCH_HEAD
    test "$(git -C "$target/$repository" rev-parse HEAD)" = "$commit"
    test -f "$target/$repository/LICENSE"
done < "$base/sources.lock"
echo 'Pinned sources fetched. Native runtime has not been built or tested.'
