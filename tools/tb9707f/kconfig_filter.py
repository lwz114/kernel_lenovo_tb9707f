#!/usr/bin/env python3
"""Static defconfig filter for the TB-9707F (Legion Y700) port.

Takes the stock device config (/proc/config.gz) and drops every symbol that
has no Kconfig definition in this source tree.  The published SM8250 tree is
missing the out-of-tree vendor directories (arch/arm64/boot/dts/vendor is a
dangling symlink), so Lenovo private CONFIG_* symbols would otherwise be
silently dropped - or worse, abort `make defconfig` on some Kconfig versions.

Usage:
    tools/tb9707f/kconfig_filter.py <stock_config> <out_defconfig> [--report FILE]

Exit codes: 0 ok, 1 usage error, 2 no Kconfig files found.
"""
import os
import re
import sys

SKIP_DIRS = {".git", "out", "build", "ccache"}

# Symbols computed by Kconfig from the toolchain at build time; never valid in a
# defconfig (they get recomputed, keeping them only obfuscates diffs).
GENERATED = {
    "CC_VERSION_TEXT", "CC_IS_CLANG", "CC_IS_GCC", "GCC_VERSION", "CLANG_VERSION",
    "LD_IS_BFD", "LD_IS_LLD", "LLD_VERSION", "AS_IS_GNU", "AS_IS_LLVM", "AS_VERSION",
    "CC_HAS_ASM_GOTO", "CC_HAS_ASM_GOTO_OUTPUT", "CC_HAS_ASM_GOTO_TIED_OUTPUT",
    "CC_HAS_ASM_INLINE", "CC_HAS_NO_PROFILE_FN_ATTR", "CC_HAS_SANE_STACKPROTECTOR",
    "CC_CAN_LINK", "CC_CAN_LINK_STATIC", "CC_HAS_SLS", "CC_HAS_RETURN_THUNK",
    "RUSTC_VERSION", "PAHOLE_VERSION",
}

RE_CONFIG = re.compile(r"^\s*(?:menu)?config\s+([A-Za-z0-9_]+)\s*$")
RE_SET = re.compile(r"^CONFIG_([A-Za-z0-9_]+)=(.*)$")
RE_UNSET = re.compile(r"^# CONFIG_([A-Za-z0-9_]+) is not set\s*$")


def defined_symbols(root):
    syms = set()
    files = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not (fn == "Kconfig" or fn.startswith("Kconfig.")):
                continue
            files += 1
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        m = RE_CONFIG.match(line)
                        if m:
                            syms.add(m.group(1))
            except OSError as exc:
                print("warn: cannot read %s: %s" % (path, exc), file=sys.stderr)
    return syms, files


def main(argv):
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 1
    src, dst = argv[1], argv[2]
    report = None
    if "--report" in argv:
        report = argv[argv.index("--report") + 1]
    root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

    syms, files = defined_symbols(root)
    if not files:
        print("error: no Kconfig files under %s" % root, file=sys.stderr)
        return 2

    kept, dropped, headings = [], [], []
    with open(src, "r", encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            m = RE_SET.match(line)
            if m:
                sym = m.group(1)
                if sym not in syms or sym in GENERATED:
                    dropped.append(line)
                    continue
                kept.append(line)
                continue
            m = RE_UNSET.match(line)
            if m:
                sym = m.group(1)
                if sym not in syms or sym in GENERATED:
                    dropped.append(line)
                    continue
                kept.append(line)
                continue
            if line.startswith("#"):
                headings.append(line)
            # drop the "Automatically generated" banner and blank separators later

    with open(dst, "w", encoding="utf-8") as fh:
        fh.write("#\n")
        fh.write("# TB-9707F (Legion Y700, kona/SM8250) defconfig\n")
        fh.write("#\n")
        fh.write("# Derived from the running device /proc/config.gz, filtered against every\n")
        fh.write("# Kconfig file present in this tree.  Regenerate with:\n")
        fh.write("#   tools/tb9707f/kconfig_filter.py <stock_config> <this file>\n")
        fh.write("#\n")
        fh.write("# deviating from the stock device config on purpose:\n")
        fh.write("#   CONFIG_LOCALVERSION=\"-perf\"           -> kept as stock; the trailing \"+\" of the\n")
        fh.write("#                                             4.19.157-perf+ vermagic is pinned by\n")
        fh.write("#                                             .scmversion (see PORTING_NOTES.md)\n")
        fh.write("#   # CONFIG_MODULE_SIG_FORCE is not set   -> stock vendor .ko must keep loading\n")
        fh.write("#\n\n")
        fh.write("\n".join(kept))
        fh.write("\n")

    if report:
        with open(report, "w", encoding="utf-8") as fh:
            fh.write("# CONFIG_* present in the stock device config but not defined in this tree\n")
            fh.write("# (dropped from tb9707f_defconfig; %d symbols)\n\n" % len(dropped))
            fh.write("\n".join(dropped))
            fh.write("\n")

    print("kconfig files scanned : %d" % files)
    print("symbols in this tree  : %d" % len(syms))
    print("kept                  : %d" % len(kept))
    print("dropped (no Kconfig)  : %d" % len(dropped))
    if report:
        print("report                : %s" % report)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
