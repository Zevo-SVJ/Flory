#!/bin/bash
# one command: updates the code, installs what draws the picture, and starts Claude in Chrome on POSTER.md,
# every hour; it posts once a day at 9:30am New York time (posts.py decides), and does nothing the other hours
cd "$(dirname "$0")" || exit 1
git -C .. pull -q || true
python3 -m pip install -q --user pillow 2>/dev/null || pip3 install -q pillow
python3 posts.py 168 --today | head -1
exec claude --chrome "/loop 1h Lis POSTER.md et fais un passage."
