#!/bin/sh
set -eu
mkdir -p .scratch/browser
# Only first-party app test code and local test credentials enter this test container.
docker run --rm --network component-board_default --cpus 2 --memory 2g --pids-limit 512 --cap-drop ALL --security-opt no-new-privileges --mount type=bind,source="$(pwd)/tests",target=/tests,readonly --mount type=bind,source="$(pwd)/.secrets/deployment.env",target=/test-secrets.env,readonly --mount type=bind,source="$(pwd)/.scratch/browser",target=/output component-board-preview node /tests/browser-smoke.mjs
