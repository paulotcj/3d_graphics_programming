"""Step 1 — Hello World (mirrors src/main.c).

The very first step of the 3D software renderer course: a console-only
program that prints a greeting and exits. Its purpose in the C original was
to verify the compiler toolchain and Makefile before any SDL code was
written; here it verifies the Python interpreter the same way. No pygame,
no numpy — those enter in the step that opens an SDL window.
"""


def main() -> None:
    """Mirrors main() in main.c: print the greeting and return."""
    print("Hello World!")


if __name__ == "__main__":
    main()
