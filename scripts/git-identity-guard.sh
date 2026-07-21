#!/bin/sh
set -eu

EXPECTED_NAME='aiwenjie777'
EXPECTED_EMAIL='kevinhh284@gmail.com'

fail() {
  printf 'Git identity guard: %s\n' "$1" >&2
  exit 1
}

assert_repository() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail 'not inside a Git repository'
}

assert_identity() {
  name=$(git config --local --get user.name || true)
  email=$(git config --local --get user.email || true)
  [ "$name" = "$EXPECTED_NAME" ] || fail "expected user.name=$EXPECTED_NAME, got ${name:-<unset>}"
  [ "$email" = "$EXPECTED_EMAIL" ] || fail "expected user.email=$EXPECTED_EMAIL, got ${email:-<unset>}"
}

check_commit() {
  author_name=$(git show -s --format='%an' "$1")
  author_email=$(git show -s --format='%ae' "$1")
  committer_name=$(git show -s --format='%cn' "$1")
  committer_email=$(git show -s --format='%ce' "$1")
  message=$(git show -s --format='%B' "$1")
  [ "$author_name" = "$EXPECTED_NAME" ] || fail "unexpected author in commit $1"
  [ "$author_email" = "$EXPECTED_EMAIL" ] || fail "unexpected author email in commit $1"
  [ "$committer_name" = "$EXPECTED_NAME" ] || fail "unexpected committer in commit $1"
  [ "$committer_email" = "$EXPECTED_EMAIL" ] || fail "unexpected committer email in commit $1"
  if printf '%s\n' "$message" | grep -Eiq '^Co-authored-by:'; then
    fail "co-author trailer found in commit $1"
  fi
}

check_unpublished() {
  assert_identity
  commits=$(git rev-list HEAD --not --remotes 2>/dev/null || true)
  for commit in $commits; do
    check_commit "$commit"
  done
  printf 'Git identity guard: OK (%s <%s>)\n' "$EXPECTED_NAME" "$EXPECTED_EMAIL"
}

check_message() {
  assert_identity
  [ -f "$1" ] || fail 'commit message file is missing'
  if grep -Eiq '^Co-authored-by:' "$1"; then
    fail 'co-author trailers are not allowed'
  fi
}

check_push() {
  assert_identity
  zero='0000000000000000000000000000000000000000'
  while read -r local_ref local_sha remote_ref remote_sha; do
    [ -n "${local_sha:-}" ] || continue
    [ "$local_sha" = "$zero" ] && continue
    if [ "$remote_sha" = "$zero" ]; then
      commits=$(git rev-list "$local_sha" --not --remotes)
    else
      commits=$(git rev-list "$remote_sha..$local_sha")
    fi
    for commit in $commits; do
      check_commit "$commit"
    done
  done
  printf 'Git identity guard: push check passed\n'
}

setup() {
  git config --local user.name "$EXPECTED_NAME"
  git config --local user.email "$EXPECTED_EMAIL"
  git config --local core.hooksPath .githooks
  assert_identity
  printf 'Git identity guard: installed for this repository\n'
}

assert_repository
case "${1:-check}" in
  setup) setup ;;
  check) check_unpublished ;;
  check-message)
    [ "$#" -eq 2 ] || fail 'usage: check-message MESSAGE_FILE'
    check_message "$2"
    ;;
  check-push) check_push ;;
  *) fail 'usage: git-identity-guard.sh [setup|check|check-message FILE|check-push]' ;;
esac
