#!/usr/bin/env bash
set -e
git add -A
git commit -m "$1" || echo "Nothing to commit"
