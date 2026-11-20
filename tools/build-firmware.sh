#!/usr/bin/env bash
# Build the firmware locally, in the same Docker image GitHub Actions uses.
#
#   tools/build-firmware.sh                  build every target in build.yaml
#   tools/build-firmware.sh kibard_v2_left   build only the named targets
#   tools/build-firmware.sh --update ...     fetch the latest ZMK main first
#
# Results land in firmware/<artifact-name>.uf2, named like the GitHub
# artifacts. The west workspace (ZMK, Zephyr, modules: about 4 GB) lives in
# $KIBARD_ZMK_WS, default ~/.cache/kibard-zmk, and is fetched once. After that,
# `west update` runs only when config/west.yml changes or --update is given.
# config/west.yml tracks ZMK main, so without --update a local build uses the
# ZMK revision from the last fetch, where GitHub always builds the newest.
set -euo pipefail

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
ws=${KIBARD_ZMK_WS:-$HOME/.cache/kibard-zmk}
image=zmkfirmware/zmk-build-arm:stable
out=$repo/firmware

update=0
wanted=()
for arg in "$@"; do
    case $arg in
        --update) update=1 ;;
        -h|--help) sed -n '2,13s/^# \{0,1\}//p' "$0"; exit 0 ;;
        -*) echo "unknown option: $arg" >&2; exit 2 ;;
        *) wanted+=("$arg") ;;
    esac
done

# build.yaml -> "artifact|board|shield" lines.
mapfile -t targets < <(awk '
    function flush() { if (name != "") print name "|" board "|" shield; name = board = shield = "" }
    /^[[:space:]]*-[[:space:]]*board:/ { flush() }
    {
        line = $0; sub(/^[[:space:]]*-?[[:space:]]*/, "", line)
        key = line; sub(/:.*/, "", key)
        val = line; sub(/^[^:]*:[[:space:]]*/, "", val)
        if (key == "board") board = val
        else if (key == "shield") shield = val
        else if (key == "artifact-name") name = val
    }
    END { flush() }
' "$repo/build.yaml")

if ((${#wanted[@]})); then
    selected=()
    for w in "${wanted[@]}"; do
        match=
        for t in "${targets[@]}"; do [[ ${t%%|*} == "$w" ]] && match=$t; done
        if [[ -z $match ]]; then
            echo "no target '$w' in build.yaml; known: $(printf '%s ' "${targets[@]%%|*}")" >&2
            exit 2
        fi
        selected+=("$match")
    done
    targets=("${selected[@]}")
fi

docker_run() {
    docker run --rm --user "$(id -u):$(id -g)" -e HOME=/ws/home \
        -v "$ws:/ws" -v "$repo:/repo:ro" -w /ws "$image" bash -c "$1"
}

mkdir -p "$ws/config" "$ws/home" "$out"
if [[ ! -d $ws/.west ]]; then
    echo "==> Creating the west workspace in $ws (first run downloads about 4 GB)"
    cp "$repo/config/west.yml" "$ws/config/west.yml"
    docker_run 'west init -l config'
    update=1
elif ! cmp -s "$repo/config/west.yml" "$ws/config/west.yml"; then
    echo "==> config/west.yml changed; updating the workspace"
    cp "$repo/config/west.yml" "$ws/config/west.yml"
    update=1
fi
if ((update)); then
    echo "==> west update"
    docker_run 'west update -n && west zephyr-export'
fi

failed=()
for t in "${targets[@]}"; do
    IFS='|' read -r name board shield <<<"$t"
    echo "==> Building $name ($shield)"
    rm -f "$ws/build/$name/zephyr/zmk.uf2"
    if docker_run "west build -p auto -s zmk/app -d build/$name -b $board -- \
            -DSHIELD='$shield' -DZMK_CONFIG=/repo/config -DZMK_EXTRA_MODULES=/repo" \
        && [[ -f $ws/build/$name/zephyr/zmk.uf2 ]]; then
        cp "$ws/build/$name/zephyr/zmk.uf2" "$out/$name.uf2"
    else
        failed+=("$name")
    fi
done

echo
for t in "${targets[@]}"; do
    name=${t%%|*}
    if [[ " ${failed[*]-} " == *" $name "* ]]; then
        echo "  FAILED  $name"
    else
        echo "  ok      firmware/$name.uf2"
    fi
done
((${#failed[@]} == 0))
