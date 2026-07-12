# test — multi-file "hello" sanity check

The C `test/` folder is a toolchain sanity check: a `main.c` that calls a
function defined in a second translation unit (`testheader.c`, declared in
`testheader.h`). Its only job is to prove that compiling and linking multiple
files works.

The Python mirror proves the equivalent thing — that one module can import and
call another:

```
py -3.12 main.py
```

Expected output:

```
hello
inside testheader_function
```

## File map

| C file                        | Python file     | Notes                                                    |
|-------------------------------|-----------------|----------------------------------------------------------|
| `main.c`                      | `main.py`       | entry point                                              |
| `testheader.c` + `testheader.h` | `testheader.py` | one module replaces the header/source pair               |
| `Makefile`                    | —               | not needed; Python has no compile/link step              |

Fun detail: the C `main.c` includes `testheader.h` **four times**. The include
guard (`#ifndef TESTHEADER_H`) makes the repeats harmless. Python gets the same
protection for free — a module is executed once on first import and cached in
`sys.modules` afterwards.
