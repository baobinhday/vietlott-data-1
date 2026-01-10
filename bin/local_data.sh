#!/usr/bin/env bash
# generate data file locally without pushing to git

VENV=".venv"

make requirements-dev

# Activate virtual environment if it exists
if [ -n "$VENV" ]; then
  source "$VENV/bin/activate"
fi

# generate data file
echo "pwd $(pwd)"

export PYTHONPATH="src"
export LOGURU_LEVEL="INFO"

python src/vietlott/cli/crawl.py keno
python src/vietlott/cli/missing.py keno
python src/vietlott/cli/crawl.py power_655
python src/vietlott/cli/missing.py power_655
python src/vietlott/cli/crawl.py power_645
python src/vietlott/cli/missing.py power_645
python src/vietlott/cli/crawl.py power_535
python src/vietlott/cli/missing.py power_535
python src/vietlott/cli/crawl.py 3d
python src/vietlott/cli/missing.py 3d
python src/vietlott/cli/crawl.py 3d_pro
python src/vietlott/cli/missing.py 3d_pro
python src/vietlott/cli/crawl.py bingo18
python src/vietlott/cli/missing.py bingo18

python src/render_readme.py
