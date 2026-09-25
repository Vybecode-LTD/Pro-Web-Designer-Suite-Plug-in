"""Review helper: measure the contrast claims in the three skills against tokens.css (OKLCH -> sRGB -> WCAG)."""
import math

def oklch_to_srgb(L, C, H):
    L = L / 100.0
    h = math.radians(H)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    def enc(x):
        x = min(max(x, 0.0), 1.0)
        return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055
    return tuple(enc(v) for v in (r, g, bb))

def lum(rgb):
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

N = {0: (100, 0, 0), 50: (98.2, 0.003, 75), 100: (96.0, 0.004, 75), 200: (92.2, 0.005, 75),
     300: (86.5, 0.006, 75), 400: (71.5, 0.008, 75), 500: (53.5, 0.009, 75), 600: (47.5, 0.009, 75),
     700: (38.5, 0.008, 75), 800: (28.0, 0.007, 75), 900: (19.5, 0.006, 75), 950: (13.0, 0.005, 75),
     1000: (8.0, 0.004, 75)}
rgb = {k: oklch_to_srgb(*v) for k, v in N.items()}

print("LIGHT theme")
print(" fg-muted (n600) on surface (n0):  %.2f" % ratio(rgb[600], rgb[0]))
print(" fg-muted (n600) on canvas (n50):  %.2f" % ratio(rgb[600], rgb[50]))
print(" fg-muted (n600) on sunken (n100): %.2f" % ratio(rgb[600], rgb[100]))
print(" fg-subtle (n500) on surface (n0): %.2f" % ratio(rgb[500], rgb[0]))
print(" fg-subtle (n500) on sunken (n100): %.2f" % ratio(rgb[500], rgb[100]))
# .cta-block__note: fg-on-inverse (n50) at opacity .85 over bg-inverse (n900)
fg, bg = rgb[50], rgb[900]
comp = tuple(0.85 * f + 0.15 * b for f, b in zip(fg, bg))
print(" cta note: on-inverse n50 on n900 full: %.2f  at opacity .85: %.2f" % (ratio(fg, bg), ratio(comp, bg)))
print("DARK theme")
print(" fg-muted (n300) on canvas (n1000): %.2f" % ratio(rgb[300], rgb[1000]))
print(" fg-subtle (n400) on sunken (n1000): %.2f" % ratio(rgb[400], rgb[1000]))
print(" fg-subtle (n400) on surface (n950): %.2f" % ratio(rgb[400], rgb[950]))
# dark: inverse band is n100 with fg-on-inverse n900
fg, bg = rgb[900], rgb[100]
comp = tuple(0.85 * f + 0.15 * b for f, b in zip(fg, bg))
print(" cta note dark: n900 on n100 full: %.2f  at .85: %.2f" % (ratio(fg, bg), ratio(comp, bg)))
