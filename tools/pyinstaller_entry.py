"""PyInstaller entry shim; running shooty.__main__ as a script breaks imports."""
from shooty.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
