"""Launch the desktop utilities with ``python -m windows_apps``."""

import sys

from windows_apps.app import main


if __name__ == "__main__":
    main(sys.argv[1:])
