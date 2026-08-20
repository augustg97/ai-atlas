"""The definitive check: full enumeration of the real r8 registry against the fast one.

120,960,000 cells at 19,722 a second is about 102 minutes. It is worth spending once, because
every other test in equiv.py is on a sub-registry, and the line this returns is the one the
document actually draws.
"""
import json, sys, time
sys.path.insert(0, 'Research/timelines'); sys.path.insert(0, 'Research/modeling')
import axes, worldlines as W
reg = json.loads(json.dumps(axes.REGISTRY))
t = time.time(); b_line, b_p = W.mainline(reg); tb = time.time() - t
print("branch and bound: %.3fs" % tb, flush=True)
print("  ", b_line, "%.12g" % b_p, flush=True)
t = time.time(); e_line, e_p = W.mainline_enumerate(reg); te = time.time() - t
print("full enumeration: %.1fs (%.1f min)" % (te, te / 60), flush=True)
print("  ", e_line, "%.12g" % e_p, flush=True)
same = e_line == b_line and abs(e_p - b_p) <= 1e-15 * max(1.0, abs(e_p))
print("IDENTICAL" if same else "*** DIFFERENT ***", flush=True)
print("speedup: %.0fx" % (te / max(tb, 1e-9)), flush=True)
