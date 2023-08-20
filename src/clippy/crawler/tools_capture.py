# ONLY NON ASYNC CODE HERE


def _print_console(*args):
    args = [repr(str(a)) for a in args]
    print("injection=>", *[a if (len(a) < 50) else f"{a[:50]}..." for a in args])
