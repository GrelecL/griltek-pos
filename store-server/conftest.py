import os
import sys

# Make store-server/app importable when running pytest from monorepo root
sys.path.insert(0, os.path.dirname(__file__))
