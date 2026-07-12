"""Mirror of ``test/testheader.c`` / ``test/testheader.h``.

In C, the pair ``testheader.h`` (declaration) + ``testheader.c`` (definition)
exists so other translation units can call the function. In Python a single
module plays both roles: importing it gives you the declaration *and* the
definition — no header files or include guards needed.
"""


def testheader_function() -> None:
    """Mirrors ``void testheader_function(void)``."""
    print("inside testheader_function")
