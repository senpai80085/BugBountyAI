import os
import sys

# Ensure the correct local project path has absolute highest priority in sys.path
local_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if local_root in sys.path:
    sys.path.remove(local_root)
sys.path.insert(0, local_root)
