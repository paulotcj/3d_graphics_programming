"""Mirror of ``test/main.c`` — a minimal multi-file C program used to sanity-check
the build toolchain (one translation unit calling a function defined in another).

In Python the equivalent exercise is a module import: ``main.py`` imports
``testheader.py`` and calls its function. Note that the C file included
``testheader.h`` four times — harmless there thanks to the include guard, and
equally harmless here because Python caches modules after the first import.
"""

from testheader import testheader_function


def main() -> None:
    """Entry point: mirrors ``int main(void)`` in ``test/main.c``."""
    print("hello")
    testheader_function()


if __name__ == "__main__":
    main()
