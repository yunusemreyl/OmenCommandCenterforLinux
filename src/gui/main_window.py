#!/usr/bin/env python3
"""
OMEN Command Center for Linux - Main Window
Launcher-style home menu with page selection cards.
"""
import sys, os, json, math, subprocess, shutil, threading

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # fallback for Python ≤3.10
    except ImportError:
        tomllib = None  # No TOML support — will use JSON config only

import gi
gi.require_version('Gtk', '4.0')
try:
    gi.require_version('Adw', '1')
    from gi.repository import Adw
    HAS_ADW = True
except ValueError:
    Adw = None
    HAS_ADW = False

from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf, Pango
import cairo

# Add parent path for imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Check relative to source (2 levels up -> src/OmenCommandCenterforLinux)
PROJ_SRC = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# Check relative to installed location (1 level up -> /usr/share/hp-manager)
PROJ_INSTALLED = os.path.abspath(os.path.join(BASE_DIR, ".."))

if os.path.exists(os.path.join(PROJ_SRC, "images", "omenapplogo.png")):
    IMAGES_DIR = os.path.join(PROJ_SRC, "images")
    PROJECT_DIR = PROJ_SRC
elif os.path.exists(os.path.join(PROJ_INSTALLED, "images", "omenapplogo.png")):
    IMAGES_DIR = os.path.join(PROJ_INSTALLED, "images")
    PROJECT_DIR = PROJ_INSTALLED
else:
    IMAGES_DIR = "/usr/share/hp-manager/images"
    PROJECT_DIR = "/usr/share/hp-manager"

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.dirname(BASE_DIR))

from pages.fan_page import FanPage
from pages.lighting_page import LightingPage
from pages.mux_page import MUXPage
from pages.settings_page import SettingsPage
from pages.dashboard_page import DashboardPage
from pages.keyboard_page import KeyboardPage

APP_VERSION = "1.3.0"
CONFIG_FILE      = os.path.expanduser("~/.config/hp-manager.toml")
CONFIG_FILE_JSON = os.path.expanduser("~/.config/hp-manager.json")
_LAUNCHER_REFRESH_MS = 5000

# ── Translations (centralised in i18n.py) ────────────────────────────────────
from i18n import T, set_lang, get_lang


def get_model_branding():
    """Return 'OMEN', 'Victus', or 'HP Laptop' based on DMI product name."""
    try:
        for dmi_file in ("/sys/class/dmi/id/product_name",
                         "/sys/class/dmi/id/product_family"):
            if os.path.exists(dmi_file):
                with open(dmi_file, "r") as f:
                    name = f.read().lower()
                if "omen" in name:
                    return "OMEN"
                if "victus" in name:
                    return "Victus"
    except Exception:
        pass
    return "HP Laptop"


def get_device_model_name():
    """Return concrete device model name from DMI, fallback to branding."""
    invalid = {
        "",
        "to be filled by o.e.m.",
        "not applicable",
        "default string",
        "system product name",
        "unknown",
        "hp laptop",
    }
    try:
        for dmi_file in (
            "/sys/class/dmi/id/product_name",
            "/sys/class/dmi/id/product_family",
            "/sys/class/dmi/id/board_name",
        ):
            if os.path.exists(dmi_file):
                with open(dmi_file, "r") as f:
                    name = " ".join(f.read().strip().split())
                if name.lower() not in invalid:
                    return name
    except Exception:
        pass
    return get_model_branding()


class FixedMenuIcon(Gtk.DrawingArea):
    """Theme-pack-independent line icons for launcher/menu UI."""

    def __init__(self, kind, size=74, rgb=(0.92, 0.94, 0.97), line_width=3.0):
        super().__init__()
        self.kind = kind
        self.rgb = rgb
        self._line_width = line_width
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_draw_func(self._draw)

    def _setup_pen(self, cr, w):
        cr.set_source_rgb(*self.rgb)
        cr.set_line_width(max(1.4, self._line_width))
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def _draw(self, _area, cr, w, h):
        self._setup_pen(cr, w)
        kind = self.kind

        if kind == "dashboard":
            s = min(w, h) * 0.23
            gap = s * 0.34
            start_x = (w - (2 * s + gap)) / 2
            start_y = (h - (2 * s + gap)) / 2
            for r in range(2):
                for c in range(2):
                    x = start_x + c * (s + gap)
                    y = start_y + r * (s + gap)
                    cr.rectangle(x, y, s, s)
                    cr.stroke()
            return

        if kind == "fan":
            cx, cy = w / 2, h / 2
            r = min(w, h) * 0.35
            cr.arc(cx, cy, r, 0, 2 * 3.14159)
            cr.stroke()
            cr.arc(cx, cy, r * 0.18, 0, 2 * 3.14159)
            cr.stroke()
            for a in (0.0, 1.57, 3.14, 4.71):
                x1 = cx + (r * 0.22) * math.cos(a)
                y1 = cy + (r * 0.22) * math.sin(a)
                x2 = cx + (r * 0.82) * math.cos(a + 0.44)
                y2 = cy + (r * 0.82) * math.sin(a + 0.44)
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
                cr.stroke()
            return

        if kind == "lighting":
            cx, cy = w / 2, h / 2
            r = min(w, h) * 0.22
            cr.arc(cx, cy - r * 0.25, r, 0, 2 * 3.14159)
            cr.stroke()
            cr.move_to(cx - r * 0.55, cy + r * 0.9)
            cr.line_to(cx + r * 0.55, cy + r * 0.9)
            cr.stroke()
            cr.move_to(cx - r * 0.34, cy + r * 0.52)
            cr.line_to(cx + r * 0.34, cy + r * 0.52)
            cr.stroke()
            cr.move_to(cx - r * 0.34, cy + r * 0.52)
            cr.line_to(cx - r * 0.34, cy + r * 0.9)
            cr.stroke()
            cr.move_to(cx + r * 0.34, cy + r * 0.52)
            cr.line_to(cx + r * 0.34, cy + r * 0.9)
            cr.stroke()
            return

        if kind == "keyboard":
            x = w * 0.16
            y = h * 0.30
            ww = w * 0.68
            hh = h * 0.38
            cr.rectangle(x, y, ww, hh)
            cr.stroke()
            key_w = ww / 7.5
            key_h = hh / 3.3
            for r in range(2):
                for c in range(6):
                    kx = x + key_w * 0.5 + c * key_w
                    ky = y + key_h * 0.5 + r * key_h
                    cr.rectangle(kx, ky, key_w * 0.64, key_h * 0.55)
                    cr.stroke()
            cr.rectangle(x + ww * 0.22, y + hh * 0.72, ww * 0.56, key_h * 0.35)
            cr.stroke()
            return

        if kind == "mux":
            x = w * 0.2
            y = h * 0.26
            ww = w * 0.6
            hh = h * 0.48
            cr.rectangle(x, y, ww, hh)
            cr.stroke()
            for i in range(4):
                px = x - ww * 0.08
                py = y + hh * 0.15 + i * hh * 0.22
                cr.move_to(px, py)
                cr.line_to(x, py)
                cr.stroke()
            for i in range(4):
                px = x + ww
                py = y + hh * 0.15 + i * hh * 0.22
                cr.move_to(px, py)
                cr.line_to(px + ww * 0.08, py)
                cr.stroke()
            cr.rectangle(x + ww * 0.22, y + hh * 0.22, ww * 0.56, hh * 0.56)
            cr.stroke()
            return

        if kind == "settings":
            cx, cy = w / 2, h / 2
            r = min(w, h) * 0.24
            cr.arc(cx, cy, r, 0, 2 * 3.14159)
            cr.stroke()
            cr.arc(cx, cy, r * 0.42, 0, 2 * 3.14159)
            cr.stroke()
            for i in range(8):
                a = i * (3.14159 / 4)
                x1 = cx + (r * 1.1) * math.cos(a)
                y1 = cy + (r * 1.1) * math.sin(a)
                x2 = cx + (r * 1.38) * math.cos(a)
                y2 = cy + (r * 1.38) * math.sin(a)
                cr.move_to(x1, y1)
                cr.line_to(x2, y2)
                cr.stroke()
            return

        if kind == "back":
            x = w * 0.74
            y = h * 0.5
            cr.move_to(x, y)
            cr.line_to(w * 0.3, y)
            cr.stroke()
            cr.move_to(w * 0.48, h * 0.28)
            cr.line_to(w * 0.3, y)
            cr.line_to(w * 0.48, h * 0.72)
            cr.stroke()
            return


class HPManagerWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Omen Command Center")
        self.set_default_size(1100, 750)
        self.set_decorated(True)
        self.set_resizable(True)

        # Register local icon directory with the theme
        display = Gdk.Display.get_default()
        icon_theme = Gtk.IconTheme.get_for_display(display)
        if IMAGES_DIR not in icon_theme.get_search_path():
            icon_theme.add_search_path(IMAGES_DIR)

        self.set_icon_name("omenapplogo")

        self.app_theme = "dark"
        self.temp_unit = "C"
        self.service    = None
        self.ready      = False
        self._rebuilding = False
        self._launcher_cards = {}
        self._launcher_timer_id = None
        self._launcher_busy = False
        self._launcher_cpu_prev = None
        self._launcher_cpu_smooth = 0.0
        self._nvidia_smi = shutil.which("nvidia-smi") or ""
        self._nvidia_runtime_status_path = None
        self._nvidia_runtime_status_scanned = False
        self.performance_mode = "balanced"
        self._ui_scale_bucket = "normal"
        self._ui_scale_tick_id = 0
        self._ui_last_width = 0
        self._ui_last_height = 0
        self._content_overlay = None
        self._back_button_floating = False
        self._scroll_adjustment = None
        self._scroll_adjustment_handler = 0
        self.page_titles = {
            "dashboard": T("dashboard"),
            "fan": T("fan"),
            "lighting": T("lighting"),
            "keyboard": T("keyboard"),
            "mux": "MUX",
            "settings": T("settings"),
        }

        self._load_config()

        self._apply_theme_preference()

        self._apply_css()
        self._build_ui()
        self._connect_daemon()
        self._start_launcher_metrics()

    @staticmethod
    def _home_title():
        lang = str(get_lang() or "").lower()
        return "Kontrol Merkezi" if lang.startswith("tr") else "Control Center"

    @staticmethod
    def _home_subtitle():
        return T("home_subtitle")

    @staticmethod
    def _build_model_brand_image(model_name, size=20):
        model_low = str(model_name or "").lower()
        image_file = None
        if "omen" in model_low:
            image_file = "omen.png"
        elif "victus" in model_low:
            image_file = "victus.png"

        if image_file:
            image_path = os.path.join(IMAGES_DIR, image_file)
            if os.path.exists(image_path):
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, size, size, True)
                    texture = Gdk.Texture.new_for_pixbuf(pixbuf)
                    image = Gtk.Image.new_from_paintable(texture)
                    image.set_pixel_size(size)
                    return image
                except Exception:
                    pass

        fallback = Gtk.Image.new_from_icon_name("computer-symbolic")
        fallback.set_pixel_size(size)
        return fallback

    @staticmethod
    def _human_storage(value_bytes):
        try:
            val = float(value_bytes)
        except Exception:
            return "N/A"
        if val <= 0:
            return "N/A"
        gib = val / (1024 ** 3)
        if gib >= 1024:
            return f"{gib / 1024:.1f} TB"
        return f"{gib:.0f} GB"

    @staticmethod
    def _trim_hw_text(text, max_len=26):
        txt = " ".join(str(text or "").split())
        if len(txt) <= max_len:
            return txt
        return txt[:max_len - 1].rstrip() + "..."

    def _get_home_hardware_info(self):
        info = {
            "cpu": "N/A",
            "disk": "N/A",
            "gpu": "N/A",
            "ram": "N/A",
        }

        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        info["cpu"] = self._trim_hw_text(line.split(":", 1)[1].strip(), 30)
                        break
        except Exception:
            pass

        try:
            total, _used, _free = shutil.disk_usage("/")
            info["disk"] = self._human_storage(total)
        except Exception:
            pass

        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        gib = kb / (1024 * 1024)
                        info["ram"] = f"{gib:.1f} GB"
                        break
        except Exception:
            pass

        # Prefer nvidia-smi when available, fallback to lspci.
        try:
            if self._nvidia_smi:
                out = subprocess.check_output(
                    [self._nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
                    stderr=subprocess.DEVNULL,
                    timeout=1.5,
                ).decode().strip().splitlines()
                if out and out[0].strip():
                    info["gpu"] = self._trim_hw_text(out[0].strip(), 28)
            if info["gpu"] == "N/A":
                out = subprocess.check_output(["lspci"], stderr=subprocess.DEVNULL, timeout=1.5).decode("utf-8", "ignore")
                for line in out.splitlines():
                    low = line.lower()
                    if "vga compatible controller" in low or "3d controller" in low:
                        info["gpu"] = self._trim_hw_text(line.split(":", 2)[-1].strip(), 28)
                        break
        except Exception:
            pass

        return info

    # ── Config ───────────────────────────────────────────────────────────────

    def _load_config(self):
        try:
            if os.path.exists(CONFIG_FILE) and tomllib is not None:
                with open(CONFIG_FILE, "rb") as f:
                    data = tomllib.load(f)
                self.app_theme = data.get("theme", "dark")
                self.temp_unit = data.get("temp_unit", "C")
                set_lang(data.get("lang", "tr"))
            elif os.path.exists(CONFIG_FILE_JSON):
                with open(CONFIG_FILE_JSON) as f:
                    data = json.load(f)
                self.app_theme = data.get("theme", "dark")
                self.temp_unit = data.get("temp_unit", "C")
                set_lang(data.get("lang", "tr"))
                self._save_config()
            # If only a TOML file exists but tomllib is unavailable, skip silently.
        except Exception:
            pass

    @staticmethod
    def _toml_escape(val):
        """Sanitize a string value for safe TOML embedding."""
        return str(val).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

    def _save_config(self):
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            theme     = self._toml_escape(self.app_theme)
            lang      = self._toml_escape(get_lang())
            temp_unit = self._toml_escape(self.temp_unit)
            with open(CONFIG_FILE, "w") as f:
                f.write(f'theme = "{theme}"\n')
                f.write(f'lang = "{lang}"\n')
                f.write(f'temp_unit = "{temp_unit}"\n')
            # JSON fallback for systems without tomllib
            with open(CONFIG_FILE_JSON, "w") as f:
                json.dump({"theme": self.app_theme, "lang": get_lang(),
                           "temp_unit": self.temp_unit}, f)
        except Exception:
            pass

    # ── Theming helpers ───────────────────────────────────────────────────────

    def _apply_theme_preference(self):
        if HAS_ADW:
            sm = Adw.StyleManager.get_default()
            if self.app_theme == "dark":
                sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            elif self.app_theme == "light":
                sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            else:
                sm.set_color_scheme(Adw.ColorScheme.DEFAULT)
            return

        settings = Gtk.Settings.get_default()
        if settings is not None:
            if self.app_theme == "dark":
                settings.set_property("gtk-application-prefer-dark-theme", True)
            elif self.app_theme == "light":
                settings.set_property("gtk-application-prefer-dark-theme", False)

    def _get_system_accent(self):
        """Return the system/GTK accent colour as a hex string."""
        if not HAS_ADW:
            return "#3584e4"
        try:
            sm   = Adw.StyleManager.get_default()
            ac   = sm.get_accent_color()
            rgba = ac.to_rgba()
            r, g, b = int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255)
            if r or g or b:
                return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            pass
        return "#3584e4"

    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    @staticmethod
    def _lighten(hex_color, amount=30):
        r, g, b = HPManagerWindow._hex_to_rgb(hex_color)
        return f"#{min(255,r+amount):02X}{min(255,g+amount):02X}{min(255,b+amount):02X}"

    @staticmethod
    def _darken(hex_color, amount=30):
        r, g, b = HPManagerWindow._hex_to_rgb(hex_color)
        return f"#{max(0,r-amount):02X}{max(0,g-amount):02X}{max(0,b-amount):02X}"

    def _apply_css(self):
        accent       = self._get_system_accent()
        accent_hover = self._lighten(accent, 20)
        ar, ag, ab   = self._hex_to_rgb(accent)
        accent_dim            = f"rgba({ar}, {ag}, {ab}, 0.15)"
        accent_shadow         = "rgba(255,255,255,0.12)"
        accent_shadow_strong  = "rgba(255,255,255,0.18)"
        accent_glow           = "rgba(255,255,255,0.08)"
        accent_border_hover   = f"rgba({ar}, {ag}, {ab}, 0.3)"
        accent_dark           = self._darken(accent, 60)

        actual_theme = "dark"
        if self.app_theme == "dark":
            actual_theme = "dark"
        elif self.app_theme == "light":
            actual_theme = "light"
        elif HAS_ADW:
            sm = Adw.StyleManager.get_default()
            actual_theme = "dark" if sm.get_dark() else "light"
        else:
            settings = Gtk.Settings.get_default()
            prefers_dark = False
            if settings is not None:
                try:
                    prefers_dark = bool(settings.get_property("gtk-application-prefer-dark-theme"))
                except Exception:
                    prefers_dark = False
            actual_theme = "dark" if prefers_dark else "light"

        if actual_theme == "dark":
            mode_accent_map = {
                "eco": "#56d17a",
                "balanced": "#3ca8ff",
                "performance": "#ef5b4a",
            }
            accent              = mode_accent_map.get(self.performance_mode, "#3ca8ff")
            accent_hover        = self._lighten(accent, 12)
            ar, ag, ab          = self._hex_to_rgb(accent)
            accent_dim          = f"rgba({ar}, {ag}, {ab}, 0.18)"
            accent_shadow       = "rgba(255,255,255,0.14)"
            accent_shadow_strong = "rgba(255,255,255,0.22)"
            accent_glow         = "rgba(255,255,255,0.10)"
            accent_border_hover = f"rgba({ar}, {ag}, {ab}, 0.38)"
            accent_dark         = self._darken(accent, 60)
            bg             = "#121316"
            sidebar_bg     = "rgba(14,15,18,0.56)"
            card_bg        = "rgba(44,45,50,0.92)"
            card_border    = "rgba(220,228,239,0.14)"
            sep_color      = "rgba(255,255,255,0.12)"
            fg             = "#ffffff"
            fg_dim         = "#d0d4dc"
            fg_very_dim    = "#9ea6b4"
            input_bg       = "rgba(255,255,255,0.11)"
            clean_ram_color = "inherit"
            launcher_title_color = "#ffffff"
            launcher_subtitle_color = "#8d96a6"
            launcher_metric_main_color = "#f2f4f7"
            launcher_metric_sub_color = "#a1a7b3"
            launcher_temp_warm_color = "#d4dbe6"
            launcher_mode_badge_color = "#f9e5da"
            launcher_mode_badge_muted_color = "#c7ceda"
            launcher_dimmed_opacity = 0.62
            topbar_bg      = "rgba(28,29,34,0.90)"
            topbar_border  = "rgba(255,255,255,0.14)"
            topbar_shadow  = "rgba(0,0,0,0.48)"
        else:
            bg             = "#f0f0f4"
            sidebar_bg     = "rgba(255,255,255,0.5)"
            card_bg        = "rgba(255,255,255,0.78)"
            card_border    = "rgba(0,0,0,0.08)"
            sep_color      = "rgba(0,0,0,0.12)"
            fg             = "#121212"
            fg_dim         = "#444444"
            fg_very_dim    = "#666666"
            input_bg       = "rgba(0,0,0,0.06)"
            clean_ram_color = "#000000"
            launcher_title_color = "#1a1d24"
            launcher_subtitle_color = "#505a68"
            launcher_metric_main_color = "#232831"
            launcher_metric_sub_color = "#5d6878"
            launcher_temp_warm_color = "#4f6178"
            launcher_mode_badge_color = "#1f2836"
            launcher_mode_badge_muted_color = "#364355"
            launcher_dimmed_opacity = 0.86
            topbar_bg      = "rgba(255,255,255,0.86)"
            topbar_border  = "rgba(0,0,0,0.10)"
            topbar_shadow  = "rgba(0,0,0,0.16)"
            accent              = self._darken(accent, 20)
            accent_hover        = self._darken(accent, 10)
            ar, ag, ab          = self._hex_to_rgb(accent)
            accent_dim          = f"rgba({ar}, {ag}, {ab}, 0.15)"
            accent_shadow       = "rgba(255,255,255,0.12)"
            accent_shadow_strong = "rgba(255,255,255,0.18)"
            accent_glow         = "rgba(255,255,255,0.08)"
            accent_border_hover = f"rgba({ar}, {ag}, {ab}, 0.3)"
            accent_dark         = self._darken(accent, 60)

        presets_css = ""
        surface_radius = 16
        preset_colors = ["#FF0000","#00FF00","#0000FF","#FFFFFF","#FFFF00",
                         "#00FFFF","#FF00FF","#FF6600","#7B00FF"]
        for i, c in enumerate(preset_colors):
            presets_css += f"""
            .preset-{i} {{
                background-color: {c}; border-radius: 50%;
                min-width: 28px; min-height: 28px; padding: 0;
                border: 2px solid rgba(255,255,255,0.1);
                transition: all 0.2s ease;
            }}
            .preset-{i}:hover {{ border-color: white; transform: scale(1.15); }}
            """

        css = f"""
        /* ── Window ── */
        window {{
            background-color: transparent;
            color: {fg};
            font-family: "Geist", "Inter", "Noto Sans", sans-serif;
        }}
        .app-shell {{
            background-color: {bg};
            border-radius: {surface_radius}px;
            border: 1px solid {card_border};
        }}
        .app-scale-compact .card {{
            padding: 16px;
        }}
        .app-scale-compact .inner-panel {{
            padding: 10px;
        }}
        .app-scale-compact .inline-page-header {{
            min-height: 30px;
            margin: 4px 6px 2px 6px;
        }}
        .app-scale-compact .launcher-card {{
            min-width: 200px;
            min-height: 146px;
        }}
        .app-scale-compact .launcher-icon-wrap {{
            min-height: 64px;
            padding: 6px 8px;
        }}
        .app-scale-spacious .card {{
            padding: 24px;
        }}
        .app-scale-spacious .inner-panel {{
            padding: 16px;
        }}
        .app-scale-spacious .launcher-card {{
            min-width: 250px;
            min-height: 186px;
        }}
        .app-scale-spacious .launcher-icon-wrap {{
            min-height: 92px;
            padding: 10px 12px;
        }}

        .floating-topbar {{
            background: {topbar_bg};
            border: 1px solid {topbar_border};
            border-radius: {surface_radius}px;
            padding: 2px 8px;
            box-shadow: 0 12px 28px {topbar_shadow};
        }}
        .floating-page-title {{
            font-size: 12px;
            font-weight: 700;
            color: {fg};
            padding: 2px 8px;
            border-radius: 999px;
            border: 1px solid {card_border};
            background: alpha({fg}, 0.04);
        }}
        .floating-sidebar {{
            background: rgba(19, 20, 24, 0.96);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: {surface_radius}px;
            box-shadow: 0 14px 30px rgba(0,0,0,0.65);
        }}
        .floating-sidebar .nav-label,
        .floating-sidebar .nav-icon {{
            color: #aeb3bf;
        }}
        .floating-sidebar .nav-item:hover {{
            background-color: rgba(255,255,255,0.06);
        }}
        .floating-sidebar .nav-item.active {{
            background-color: rgba(255,255,255,0.09);
        }}
        .floating-sidebar .nav-item.active .nav-label,
        .floating-sidebar .nav-item.active .nav-icon {{
            color: {accent};
        }}
        .content-shell {{
            background: {card_bg};
            border: 1px solid {card_border};
            border-radius: {surface_radius}px;
            box-shadow: 0 8px 22px rgba(0,0,0,0.14);
        }}
        .window-control-btn {{
            min-width: 28px;
            min-height: 28px;
            border-radius: 999px;
            padding: 0;
            border: 1px solid {card_border};
            background: transparent;
            color: {fg_dim};
            transition: all 120ms ease;
        }}
        .window-control-btn:hover {{
            background: {accent_dim};
            color: {fg};
            border-color: {accent_border_hover};
        }}
        .window-control-btn.close-btn:hover {{
            background: rgba(227, 51, 51, 0.22);
            border-color: rgba(227, 51, 51, 0.35);
            color: #ffffff;
        }}
        .menu-back-btn {{
            border-radius: 999px;
            border: 1px solid {card_border};
            background: alpha({fg}, 0.04);
            padding: 0;
            min-width: 32px;
            min-height: 32px;
            box-shadow: none;
        }}
        .menu-back-btn:hover {{
            background: alpha({fg}, 0.08);
            border-color: alpha(#ffffff, 0.32);
            box-shadow: 0 0 10px alpha(#ffffff, 0.14);
        }}
        .menu-back-btn image {{
            color: {fg};
        }}
        .menu-back-btn:disabled {{
            opacity: 0.35;
        }}
        .inline-page-header {{
            min-height: 36px;
            margin: 8px 10px 6px 10px;
        }}
        .inline-page-title {{
            font-size: 14px;
            font-weight: 760;
            color: {fg};
            letter-spacing: 0.2px;
        }}
        .floating-back-btn-active {{
            margin-top: 16px;
            margin-left: 16px;
            background: linear-gradient(180deg, alpha(#ffffff, 0.18), alpha(#ffffff, 0.10));
            border-color: alpha(#ffffff, 0.42);
            box-shadow: 0 10px 24px rgba(0,0,0,0.32);
        }}
        .floating-back-btn-active image {{
            color: #ffffff;
        }}

        .launcher-page-title {{
            font-size: 24px;
            font-weight: 800;
            letter-spacing: 0.3px;
            color: {launcher_title_color};
        }}
        .launcher-page-subtitle {{
            font-size: 11px;
            color: {launcher_subtitle_color};
            font-weight: 500;
            margin-bottom: 2px;
        }}
        .launcher-card {{
            background: alpha({fg}, 0.025);
            border: 1px solid alpha({fg}, 0.06);
            border-radius: 14px;
            padding: 0;
            min-width: 230px;
            min-height: 166px;
            transition: all 180ms ease;
            box-shadow: 0 8px 18px rgba(0,0,0,0.22);
        }}
        .launcher-card:hover {{
            background: alpha({fg}, 0.045);
            border-color: #005a9e;
            box-shadow: 0 12px 24px rgba(0,0,0,0.28), 0 0 14px rgba(0, 90, 158, 0.18);
            transform: translateY(-2px);
        }}
        .launcher-card:active {{
            transform: scale(0.98);
        }}
        .launcher-icon-wrap {{
            background: rgba(152, 156, 166, 0.04);
            border-bottom: 1px solid alpha({fg}, 0.05);
            border-top-left-radius: 14px;
            border-top-right-radius: 14px;
            min-height: 76px;
            padding: 8px 10px;
        }}
        .launcher-icon-wrap image {{
            color: alpha({fg}, 0.9);
        }}
        .launcher-card-title {{
            font-size: 15px;
            font-weight: 760;
            letter-spacing: 0.2px;
            color: {launcher_title_color};
        }}
        .launcher-card-sub {{
            font-size: 10px;
            font-weight: 520;
            color: {launcher_subtitle_color};
        }}
        .launcher-metric-main {{
            font-size: 12px;
            font-weight: 700;
            color: {launcher_metric_main_color};
            font-family: "JetBrains Mono", "Geist", "Inter", monospace;
        }}
        .launcher-metric-sub {{
            font-size: 10px;
            color: {launcher_metric_sub_color};
            font-weight: 520;
            font-family: "JetBrains Mono", "Geist", "Inter", monospace;
        }}
        .launcher-temp-cool {{ color: #57c494; }}
        .launcher-temp-warm {{ color: {launcher_temp_warm_color}; }}
        .launcher-temp-hot {{ color: #ff8a61; }}
        .launcher-mode-badge {{
            border-radius: 999px;
            padding: 3px 9px;
            background: alpha({accent}, 0.18);
            border: 1px solid alpha({accent}, 0.42);
            color: {launcher_mode_badge_color};
            font-size: 10px;
            font-weight: 700;
        }}
        .launcher-mode-badge-muted {{
            background: rgba(122, 128, 140, 0.24);
            border: 1px solid rgba(162, 170, 184, 0.45);
            color: {launcher_mode_badge_muted_color};
        }}
        .launcher-status-badge {{
            border-radius: 999px;
            min-width: 18px;
            min-height: 18px;
            padding: 0;
            background: rgba(224, 58, 58, 0.95);
            border: 1px solid rgba(255, 215, 215, 0.42);
            color: white;
            font-size: 11px;
            font-weight: 900;
        }}
        .launcher-status-badge-critical {{
            min-width: 26px;
            min-height: 26px;
            font-size: 14px;
            background: rgba(224, 58, 58, 1.0);
            border: 1px solid rgba(255, 225, 225, 0.65);
            box-shadow: 0 0 12px rgba(224, 58, 58, 0.35);
        }}
        .launcher-mini-bar {{
            min-height: 5px;
            border-radius: 999px;
            margin-top: 2px;
        }}
        levelbar.launcher-util-bar trough {{
            background: alpha({fg}, 0.14);
            border-radius: 999px;
            min-height: 4px;
        }}
        levelbar.launcher-cpu-bar block {{
            background: #4f97ff;
            border-radius: 999px;
        }}
        levelbar.launcher-gpu-bar block {{
            background: #ff8a61;
            border-radius: 999px;
        }}
        .launcher-card-dimmed {{
            opacity: {launcher_dimmed_opacity};
            border-color: alpha({fg}, 0.03);
            box-shadow: none;
        }}

        /* ── Global text color — override Adw defaults ── */
        label {{
            color: {fg};
        }}
        .heading {{
            color: {fg};
            font-size: 15px;
            font-weight: 800;
            letter-spacing: 0.2px;
        }}
        .title-1, .title-2, .title-3, .title-4 {{
            color: {fg};
            font-family: "JetBrains Mono", "Inter", "Roboto Mono", monospace;
        }}
        .title-1 {{
            font-size: 30px;
            font-weight: 800;
        }}
        .title-2 {{
            font-size: 24px;
            font-weight: 760;
        }}
        .title-3 {{
            font-size: 20px;
            font-weight: 730;
        }}
        .title-4 {{
            font-size: 15px;
            font-weight: 700;
        }}
        .dim-label {{
            color: {fg_dim};
            font-size: 12px;
            font-weight: 520;
        }}
        entry {{
            color: {fg};
        }}
        image {{
            color: {fg_dim};
        }}
        button label {{
            color: inherit;
        }}
        .suggested-action {{
            background: {accent};
            color: white;
            box-shadow: 0px 4px 12px alpha(#ffffff, 0.20);
            border: 1px solid alpha({accent}, 0.5);
            transition: all 250ms cubic-bezier(0.2, 0.8, 0.2, 1);
        }}
        .suggested-action:hover {{
            box-shadow: 0px 6px 16px alpha(#ffffff, 0.30);
            transform: translateY(-2px);
        }}
        .suggested-action label {{
            color: white;
        }}
        .destructive-action {{
            background: #e33;
            color: white;
            box-shadow: 0px 4px 12px rgba(238, 51, 51, 0.3);
            border: 1px solid rgba(238, 51, 51, 0.5);
            transition: all 250ms cubic-bezier(0.2, 0.8, 0.2, 1);
        }}
        .destructive-action:hover {{
            box-shadow: 0px 6px 16px rgba(238, 51, 51, 0.6);
            transform: translateY(-2px);
        }}
        .destructive-action label {{
            color: white;
        }}
        .max-fan-action {{
            background: linear-gradient(160deg, rgba(255,255,255,0.16), rgba(255,255,255,0.10));
            border: 1px solid rgba(255,255,255,0.28);
            box-shadow: 0px 4px 14px rgba(255,255,255,0.16);
        }}
        .max-fan-action:hover {{
            border-color: rgba(255,255,255,0.46);
            box-shadow: 0px 8px 20px rgba(255,255,255,0.22);
            transform: translateY(-1px);
        }}
        .clean-ram-action {{
            background: {card_bg};
            border: 1px solid {sep_color};
            box-shadow: 0px 4px 10px rgba(0,0,0,0.08);
            transition: all 250ms cubic-bezier(0.2, 0.8, 0.2, 1);
        }}
        .clean-ram-action:hover {{
            box-shadow: 0px 6px 16px rgba(0,0,0,0.15);
            border-color: {accent_dim};
            transform: translateY(-2px);
        }}
        .clean-ram-action label {{
            color: {clean_ram_color};
            font-weight: 700;
        }}
        .action-btn-content {{
            margin: 0;
        }}
        .action-btn-content image {{
            color: {fg_dim};
        }}
        .action-btn-label {{
            font-size: 13px;
            font-weight: 760;
            letter-spacing: 0.2px;
        }}
        .dashboard-link-btn {{
            border-radius: 999px;
            padding: 5px 12px;
            min-height: 0;
            background: alpha({accent}, 0.14);
            border: 1px solid alpha({accent}, 0.38);
            color: {fg};
            box-shadow: 0 0 10px alpha(#ffffff, 0.08);
        }}
        .dashboard-link-btn:hover {{
            background: alpha({accent}, 0.22);
            border-color: alpha({accent}, 0.56);
            box-shadow: 0 0 14px alpha(#ffffff, 0.14);
        }}

        /* ── Sidebar ── */
        .sidebar {{
            background-color: transparent;
            border-right: none;
        }}

        separator {{
            background: {sep_color};
            min-width: 1px; min-height: 1px;
        }}
        .sidebar-logo {{
            padding: 15px 0 10px 0;
        }}
        .sidebar-logo image {{
            opacity: 0.9;
        }}
        .logo-img-light {{
            -gtk-icon-filter: brightness(0);
        }}
        .logo-img {{
            margin-bottom: 4px;
        }}

        /* ── Nav Items ── */
        .nav-item {{
            padding: 10px 8px;
            margin: 2px 8px;
            border-radius: 6px;
            border-left: 4px solid transparent;
            transition: all 150ms ease-out;
            background: transparent;
            border-top: none;
            border-right: none;
            border-bottom: none;
            min-height: 0;
        }}
        .nav-item:hover {{
            background-color: {accent_dim};
        }}
        .nav-item.active {{
            background-color: {accent_dim};
            border-left: 4px solid {accent};
        }}
        .nav-item.active image,
        .nav-item.active label {{
            color: {accent};
        }}
        .nav-label {{
            font-size: 10px;
            font-weight: 600;
            color: {fg_dim};
            margin-top: 4px;
        }}
        .nav-item.active .nav-label {{
            color: {accent};
        }}
        .nav-icon {{
            color: {fg_dim};
        }}
        .nav-item.active .nav-icon {{
            color: {accent};
        }}

        /* ── Pages ── */
        .page-title {{
            font-size: 22px;
            font-weight: 800;
            color: {fg};
            margin-bottom: 5px;
        }}
        .section-title {{
            font-size: 11px;
            font-weight: 700;
            color: {fg_dim};
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }}
        .stat-big {{
            font-size: 18px;
            font-weight: 700;
            color: {fg};
        }}
        .stat-lbl {{
            font-size: 12px;
            color: {fg_dim};
            font-weight: 500;
        }}
        .stat-rpm {{
            font-size: 16px;
            color: {fg};
            font-weight: 700;
        }}
        .fan-title {{
            font-size: 14px;
            color: {fg};
            font-weight: 600;
        }}

        /* ── Buttons ── */
        .zone-btn {{
            background: {input_bg};
            color: {fg};
            border: 1px solid {card_border};
            border-radius: 20px;
            padding: 8px 16px;
            font-weight: 600;
            transition: all 0.2s ease;
        }}
        .zone-btn:checked {{
            background: {accent};
            color: white;
            border-color: {accent};
        }}

        .profile-btn {{
            background: {input_bg};
            border: 2px solid {card_border};
            border-radius: 14px;
            transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
            min-width: 124px;
            min-height: 82px;
        }}
        .profile-btn:hover {{
            border-color: {accent_border_hover};
            box-shadow: 0 6px 16px alpha(#ffffff, 0.18);
            transform: translateY(-2px);
        }}
        .profile-btn:checked {{
            background: {accent_dim};
            border-color: {accent};
        }}
        .profile-emoji {{
            font-size: 24px;
        }}
        .profile-label {{
            font-size: 12px;
            font-weight: 600;
            color: {fg};
        }}

        .mux-btn {{
            background: {input_bg};
            border: 2px solid {card_border};
            border-radius: 18px;
            min-width: 140px;
            min-height: 140px;
            transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
            color: {fg};
        }}
        .mux-btn:hover {{
            border-color: {accent_border_hover};
            box-shadow: 0 6px 16px alpha(#ffffff, 0.18);
            transform: translateY(-2px);
        }}
        .mux-btn:checked {{
            background: linear-gradient(135deg, {accent}, {accent_dark});
            border-color: {accent_hover};
            box-shadow: 0 6px 20px {accent_shadow};
            color: white;
        }}

        /* ── Fan mode buttons (pill segmented) ── */
        .mode-selector-strip {{
            background: {input_bg};
            border-radius: 16px;
            border: 1px solid {card_border};
            padding: 0;
        }}
        .fan-mode-btn {{
            background: transparent;
            color: {fg};
            border: none;
            border-radius: 13px;
            padding: 7px 0;
            font-weight: 600;
            font-size: 12px;
            transition: all 0.2s ease;
            min-height: 0;
            min-width: 124px;
        }}
        .fan-mode-btn:hover {{
            background: alpha({fg}, 0.08);
        }}
        .fan-mode-btn:checked {{
            background: {accent};
            color: white;
            box-shadow: 0 4px 12px {accent_shadow_strong};
        }}

        /* ── Rebuilt compact fan controls ── */
        .fan-cyber-panel {{
            padding: 4px 0 2px 0;
        }}
        .fan-control-label {{
            font-size: 11px;
            color: {fg_dim};
            font-weight: 650;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }}
        .power-profile-grid {{
            margin-top: 2px;
        }}
        .power-profile-card {{
            background: alpha({fg}, 0.04);
            border: 1px solid alpha({fg}, 0.12);
            border-radius: 10px;
            box-shadow: inset 0 1px 0 alpha({fg}, 0.03);
            transition: all 0.18s ease;
        }}
        .power-profile-card:hover {{
            border-color: alpha({fg}, 0.22);
            background: alpha({fg}, 0.055);
        }}
        .power-profile-card:checked {{
            border-color: alpha({accent}, 0.72);
            background: alpha({accent}, 0.22);
            box-shadow: 0 0 16px alpha(#ffffff, 0.18), inset 0 1px 0 alpha(#ffffff, 0.24);
        }}
        .power-profile-title {{
            font-size: 12px;
            color: {fg};
            font-weight: 760;
            margin-bottom: 1px;
        }}
        .power-profile-desc {{
            font-size: 10px;
            color: {fg_dim};
            font-weight: 510;
            line-height: 1.2;
        }}

        .fan-mode-compact-strip {{
            background: alpha({fg}, 0.035);
            border: 1px solid alpha({fg}, 0.16);
            border-radius: 10px;
            padding: 1px;
        }}
        .fan-mode-compact-btn {{
            background: transparent;
            border: none;
            border-radius: 7px;
            min-height: 0;
            color: {fg_dim};
            font-size: 11px;
            font-weight: 640;
            padding: 5px 10px;
            transition: all 0.16s ease;
        }}
        .fan-mode-compact-btn:hover {{
            background: alpha({fg}, 0.08);
            color: {fg};
        }}
        .fan-mode-compact-btn:checked {{
            background: linear-gradient(180deg, alpha({accent}, 0.92), alpha({accent_dark}, 0.90));
            color: #f6f7f9;
            box-shadow: 0 0 10px alpha(#ffffff, 0.26);
        }}
        .fan-control-status {{
            font-size: 11px;
            color: {fg_dim};
            font-weight: 520;
            margin-top: 2px;
        }}

        /* ── Fan page dynamic theme accents ── */
        .fan-theme-eco .temp-circle {{
            border-color: #56d17a;
            box-shadow: 0 0 16px rgba(86, 209, 122, 0.18);
        }}
        .fan-theme-eco .sensor-bar {{ background: #56d17a; }}
        .fan-theme-eco .sensor-pod,
        .fan-theme-eco .fan-mode-compact-strip {{ border-color: rgba(86, 209, 122, 0.26); }}
        .fan-theme-eco .power-profile-card:checked,
        .fan-theme-eco .fan-mode-compact-btn:checked {{
            background: rgba(86, 209, 122, 0.24);
            border-color: rgba(122, 234, 156, 0.54);
            box-shadow: 0 0 8px rgba(86, 209, 122, 0.16);
        }}

        .fan-theme-balanced .temp-circle {{
            border-color: #3ca8ff;
            box-shadow: 0 0 16px rgba(60, 168, 255, 0.18);
        }}
        .fan-theme-balanced .sensor-bar {{ background: #3ca8ff; }}
        .fan-theme-balanced .sensor-pod,
        .fan-theme-balanced .fan-mode-compact-strip {{ border-color: rgba(60, 168, 255, 0.24); }}
        .fan-theme-balanced .power-profile-card:checked,
        .fan-theme-balanced .fan-mode-compact-btn:checked {{
            background: rgba(60, 168, 255, 0.24);
            border-color: rgba(128, 196, 255, 0.52);
            box-shadow: 0 0 8px rgba(60, 168, 255, 0.16);
        }}

        .fan-theme-performance .temp-circle {{
            border-color: #ef5b4a;
            box-shadow: 0 0 16px rgba(239, 91, 74, 0.20);
        }}
        .fan-theme-performance .sensor-bar {{ background: #ef5b4a; }}
        .fan-theme-performance .sensor-pod,
        .fan-theme-performance .fan-mode-compact-strip {{ border-color: rgba(239, 91, 74, 0.26); }}
        .fan-theme-performance .power-profile-card:checked,
        .fan-theme-performance .fan-mode-compact-btn:checked {{
            background: rgba(239, 91, 74, 0.24);
            border-color: rgba(255, 156, 145, 0.56);
            box-shadow: 0 0 8px rgba(239, 91, 74, 0.18);
        }}

        /* ── Global app colorization by performance mode ── */
        .app-perf-eco label,
        .app-perf-eco .heading,
        .app-perf-eco .section-title,
        .app-perf-eco .stat-lbl,
        .app-perf-eco .floating-page-title,
        .app-perf-balanced label,
        .app-perf-balanced .heading,
        .app-perf-balanced .section-title,
        .app-perf-balanced .stat-lbl,
        .app-perf-balanced .floating-page-title,
        .app-perf-performance label,
        .app-perf-performance .heading,
        .app-perf-performance .section-title,
        .app-perf-performance .stat-lbl,
        .app-perf-performance .floating-page-title {{
            color: {fg};
        }}
        .app-perf-eco button:checked,
        .app-perf-eco togglebutton:checked,
        .app-perf-eco .profile-btn:checked,
        .app-perf-eco .fan-mode-btn:checked,
        .app-perf-eco .zone-btn:checked {{
            background: rgba(86, 209, 122, 0.24);
            border-color: rgba(122, 234, 156, 0.50);
            color: {fg};
        }}
        .app-perf-eco scale highlight,
        .app-perf-eco progressbar progress,
        .app-perf-eco levelbar block.filled,
        .app-perf-eco .sensor-bar {{
            background: #56d17a;
        }}
        .app-perf-balanced button:checked,
        .app-perf-balanced togglebutton:checked,
        .app-perf-balanced .profile-btn:checked,
        .app-perf-balanced .fan-mode-btn:checked,
        .app-perf-balanced .zone-btn:checked {{
            background: rgba(60, 168, 255, 0.24);
            border-color: rgba(128, 196, 255, 0.50);
            color: {fg};
        }}
        .app-perf-balanced scale highlight,
        .app-perf-balanced progressbar progress,
        .app-perf-balanced levelbar block.filled,
        .app-perf-balanced .sensor-bar {{
            background: #3ca8ff;
        }}
        .app-perf-performance button:checked,
        .app-perf-performance togglebutton:checked,
        .app-perf-performance .profile-btn:checked,
        .app-perf-performance .fan-mode-btn:checked,
        .app-perf-performance .zone-btn:checked {{
            background: rgba(239, 91, 74, 0.24);
            border-color: rgba(255, 156, 145, 0.52);
            color: {fg};
        }}
        .app-perf-performance scale highlight,
        .app-perf-performance progressbar progress,
        .app-perf-performance levelbar block.filled,
        .app-perf-performance .sensor-bar {{
            background: #ef5b4a;
        }}

        /* ── Dashboard perf mode colors ── */
        .perf-eco:checked {{
            background: #6f7f99;
            box-shadow: 0 4px 12px rgba(111, 127, 153, 0.35);
        }}
        .perf-balanced:checked {{
            background: {accent};
            box-shadow: 0 4px 12px {accent_shadow_strong};
        }}
        .perf-performance:checked {{
            background: #e66100;
            box-shadow: 0 4px 12px rgba(255, 255, 255, 0.22);
        }}

        /* ── Tool cards ── */
        .tool-card {{
            background: {card_bg};
            border-radius: {surface_radius}px;
            border: none;
            padding: 18px 22px;
            transition: all 0.2s ease;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .tool-card:hover {{
            box-shadow: 0 2px 8px {accent_shadow};
        }}
        .tool-name {{
            font-size: 14px;
            font-weight: 700;
            color: {fg};
        }}
        .tool-desc {{
            font-size: 11px;
            color: {fg_dim};
        }}
        .temp-circle {{
            background: radial-gradient(circle, {accent_glow} 0%, {card_bg} 100%);
            border: 2px solid {accent};
            border-radius: 50%;
            padding: 18px;
            box-shadow: 0 0 24px {accent_glow};
            min-width: 118px;
            min-height: 118px;
            transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
        }}
        .temp-circle:hover {{
            box-shadow: 0 0 50px {accent_shadow};
            transform: scale(1.05);
            border-color: {accent_hover};
        }}
        .sensor-bar {{
            background: {accent};
            border-radius: 3px;
            opacity: 0.42;
        }}
        .sensor-pod {{
            background: alpha({fg}, 0.03);
            border: 1px solid alpha({fg}, 0.08);
            border-radius: 12px;
            padding: 10px 12px;
        }}
        .sensor-card-item {{
            padding: 6px 8px;
            border-radius: 8px;
            background: alpha({fg}, 0.025);
            transition: all 0.2s ease;
        }}
        .sensor-card-item:hover {{
            background: alpha({fg}, 0.05);
        }}
        .sensor-temp-val {{
            font-size: 14px;
            font-weight: 680;
            color: {fg};
        }}
        .tool-status {{
            font-size: 12px;
            font-weight: 600;
        }}
        .tool-installed {{
            color: {accent};
        }}
        .tool-not-installed {{
            color: #ef5350;
        }}
        .tool-install-btn {{
            background: {accent};
            color: white;
            border: none;
            border-radius: 10px;
            padding: 6px 16px;
            font-weight: 700;
            font-size: 12px;
        }}
        .tool-install-btn:hover {{
            background: {accent_hover};
        }}

        /* ── Game cards ── */
        .game-card {{
            background: {card_bg};
            border-radius: {surface_radius}px;
            border: 1px solid {card_border};
            padding: 12px;
            transition: all 0.2s ease;
        }}
        .game-card:hover {{
            border-color: {accent_border_hover};
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .card {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: {surface_radius}px;
            padding: 28px;
            box-shadow: 0 12px 22px rgba(0,0,0,0.14);
        }}
        .inner-panel {{
            background: rgba(152, 156, 166, 0.07);
            border: 1px solid alpha({accent}, 0.14);
            border-radius: 14px;
            padding: 14px;
            box-shadow: inset 0 1px 0 alpha({fg}, 0.04), 0 0 0 1px alpha(#ffffff, 0.04), 0 8px 18px alpha(#ffffff, 0.08);
        }}
        .status-strip {{
            background: rgba(152, 156, 166, 0.06);
            border: 1px solid alpha({accent}, 0.12);
            border-radius: 12px;
            padding: 10px 12px;
            box-shadow: 0 6px 14px alpha(#ffffff, 0.07);
        }}
        .home-model-strip {{
            padding: 5px 8px;
            border-radius: 10px;
            border: 1px solid alpha({fg}, 0.22);
            box-shadow: 0 0 16px alpha({fg}, 0.10);
        }}
        .home-model-details {{
            min-width: 0;
        }}
        .home-model-top {{
            min-height: 0;
        }}
        .home-spec-row {{
            margin-top: 2px;
            border-top: 1px solid alpha({fg}, 0.08);
            padding-top: 6px;
        }}
        .home-spec-item {{
            border-radius: 8px;
            background: alpha({fg}, 0.03);
            border: 1px solid alpha({fg}, 0.08);
            padding: 5px 8px;
        }}
        .home-spec-item image {{
            color: {fg_very_dim};
            margin-right: 6px;
        }}
        .home-spec-title {{
            font-size: 10px;
            color: {fg_dim};
            letter-spacing: 0.4px;
            font-weight: 620;
        }}
        .home-spec-value {{
            font-size: 11px;
            font-weight: 720;
            color: {fg};
        }}
        .battery-sparkline-frame {{
            background: rgba(152, 156, 166, 0.06);
            border: 1px solid alpha({accent}, 0.12);
            border-radius: 12px;
            box-shadow: 0 0 14px alpha(#ffffff, 0.06);
            min-height: 62px;
        }}

        .game-icon-box {{
            background: {accent_glow};
            border-radius: 10px;
        }}
        .game-name {{
            font-size: 13px;
            font-weight: 700;
            color: {fg};
        }}
        .game-source {{
            font-size: 10px;
            font-weight: 600;
            color: {accent};
            background: {accent_dim};
            padding: 2px 8px;
            border-radius: 8px;
        }}
        .game-launch-btn {{
            background: {accent};
            color: white;
            border: none;
            border-radius: 8px;
            padding: 4px 12px;
            font-weight: 600;
            font-size: 11px;
        }}

        /* ── Search ── */
        .search-entry {{
            background: {input_bg};
            border: 1px solid {card_border};
            border-radius: 12px;
            padding: 8px 15px;
            color: {fg};
        }}

        /* ── KB Frame ── */
        .kb-frame {{
            background: rgba(0,0,0,0.25);
            border: 1px solid {card_border};
            border-radius: {surface_radius}px;
            padding: 12px;
        }}

        /* ── Color picker ── */
        .color-picker-btn {{
            background: {input_bg};
            border: 2px dashed {fg_very_dim};
            border-radius: 50%;
            min-width: 28px;
            min-height: 28px;
            padding: 0;
            font-weight: 700;
            color: {fg_dim};
        }}

        /* ── Warning ── */
        .warning-box {{
            background: rgba(255, 200, 0, 0.06);
            border: 1px solid rgba(255, 200, 0, 0.2);
            border-radius: {surface_radius}px;
            padding: 20px;
        }}
        .warning-text {{
            color: #ffcc00;
            font-weight: 700;
            font-size: 16px;
        }}
        .warning-sub {{
            color: #e6b800;
            font-weight: 500;
            font-size: 12px;
        }}

        /* ── Empty state ── */
        .empty-state {{
            padding: 40px;
        }}

        /* ── Inputs ── */
        scale trough {{
            background: {input_bg};
            border-radius: 4px;
        }}
        scale highlight {{
            background: {accent};
            border-radius: 4px;
        }}
        scale value {{
            background: {card_bg};
            color: {fg};
            border: none;
            border-radius: 6px;
            padding: 2px 6px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }}
        dropdown > button {{
            background: alpha({fg}, 0.04);
            border: 1px solid {card_border};
            outline: none;
            box-shadow: none;
            border-radius: 10px;
            color: {fg};
            min-height: 0;
            padding: 6px 10px;
        }}
        dropdown > button:hover {{
            background: alpha({fg}, 0.08);
        }}
        dropdown > button:focus {{
            outline: none;
            box-shadow: 0 0 0 2px alpha({accent}, 0.16);
            border: 1px solid alpha({accent}, 0.45);
        }}
        popover, popover.background {{
            background: transparent;
            border: none;
            box-shadow: none;
            color: {fg};
        }}
        popover > contents, popover.background > contents {{
            background: {card_bg};
            border: 1px solid alpha({fg}, 0.12);
            border-radius: 14px;
            box-shadow: 0 12px 28px rgba(0,0,0,0.24);
            padding: 6px;
        }}
        popover scrolledwindow,
        popover.background scrolledwindow,
        popover viewport,
        popover.background viewport,
        popover listview,
        popover.background listview {{
            background: {card_bg};
            color: {fg};
        }}
        popover modelbutton, popover label {{
            color: {fg};
        }}
        popover row label,
        popover modelbutton label {{
            color: {fg};
        }}
        popover modelbutton {{
            border-radius: 10px;
            padding: 8px 12px;
            margin: 1px 0;
            font-weight: 600;
            background: transparent;
        }}
        popover modelbutton:hover {{
            background: alpha({fg}, 0.08);
        }}
        popover row {{
            background: transparent;
            color: {fg};
            border-radius: 10px;
            min-height: 32px;
        }}
        popover row:hover {{
            background: alpha({fg}, 0.08);
        }}
        popover row:selected {{
            background: alpha({accent}, 0.16);
        }}

        /* ── Update button ── */
        .update-btn {{
            background: {accent};
            color: white;
            border: none;
            border-radius: 10px;
            padding: 8px 20px;
            font-weight: 700;
            font-size: 12px;
        }}
        .update-btn:hover {{
            background: {accent_hover};
        }}
        .update-available {{
            color: {accent};
            font-weight: 600;
        }}

        /* ── Dashboard pill rows ── */
        .pill-row {{
            background: {accent_dim};
            border-radius: {surface_radius}px;
            padding: 8px 12px;
        }}
        .pill-frame {{
            background: rgba(152, 156, 166, 0.06);
            border-radius: {surface_radius}px;
            border: 1px solid alpha({accent}, 0.13);
            box-shadow: 0px 4px 10px rgba(0,0,0,0.08), 0 0 12px alpha(#ffffff, 0.05);
            transition: all 300ms cubic-bezier(0.2, 1, 0.2, 1);
        }}
        .profile-strip {{
            border-radius: 12px;
        }}
        .profile-tile {{
            min-height: 116px;
        }}
        .profile-caption {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }}
        .profile-value {{
            font-size: 14px;
            font-weight: 760;
        }}
        .pill-frame:hover {{
            background: {accent_glow};
            border-color: {accent};
            box-shadow: 0px 8px 20px {accent_shadow};
            transform: translateY(-1px);
        }}
        .pill-muted {{
            opacity: 0.55;
            border-style: dashed;
        }}

        .temp-value {{
            font-family: "JetBrains Mono", "Roboto Mono", monospace;
            font-size: 30px;
            font-weight: 820;
            letter-spacing: 0.6px;
            color: {fg};
        }}
        .temp-unit {{
            font-family: "JetBrains Mono", "Roboto Mono", monospace;
            font-size: 16px;
            font-weight: 700;
            color: {fg_very_dim};
            margin-bottom: 8px;
        }}
        .sensor-name {{
            letter-spacing: 0.8px;
        }}
        .cpu-sparkline-frame {{
            background: rgba(152, 156, 166, 0.06);
            border: 1px solid alpha({accent}, 0.12);
            border-radius: 12px;
            box-shadow: 0 0 14px alpha(#ffffff, 0.06);
            margin-bottom: 6px;
            min-height: 62px;
        }}

        .info-inline {{
            font-family: "JetBrains Mono", "Inter", monospace;
            font-size: 12px;
            letter-spacing: 0.2px;
        }}
        .info-kernel-icon {{
            color: {fg_very_dim};
            margin-right: 4px;
        }}

        .debug-console {{
            background-color: #0c0c0c;
            color: #00ff41;
            font-family: 'Monospace', 'Courier New', monospace;
            font-size: 13px;
        }}
        .debug-console text {{
            background-color: #0c0c0c;
        }}

        {presets_css}
        """

        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    # ── UI construction ───────────────────────────────────────────────────────

    def _make_window_control_button(self, icon_name, callback, extra_css_class=None):
        btn = Gtk.Button()
        btn.add_css_class("window-control-btn")
        if extra_css_class:
            btn.add_css_class(extra_css_class)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        btn.set_child(icon)
        btn.connect("clicked", callback)
        return btn

    def _build_floating_bar(self):
        handle = Gtk.WindowHandle()

        bar = Gtk.Box(spacing=6)
        bar.add_css_class("floating-topbar")

        left = Gtk.Box(spacing=6, halign=Gtk.Align.START, valign=Gtk.Align.CENTER)

        self.menu_back_btn = Gtk.Button()
        self.menu_back_btn.add_css_class("menu-back-btn")
        self.menu_back_btn.set_child(self._build_menu_back_content())
        self.menu_back_btn.set_tooltip_text("Ana Menü" if get_lang() == "tr" else "Main Menu")
        self.menu_back_btn.connect("clicked", lambda *_: self._navigate("home"))
        self.menu_back_btn.set_sensitive(False)
        self.menu_back_btn.set_opacity(0.35)
        self.menu_back_btn.set_size_request(32, 32)
        left.append(self.menu_back_btn)

        brand_icon = Gtk.Image.new_from_icon_name("omenapplogo")
        brand_icon.set_pixel_size(20)
        left.append(brand_icon)

        self.floating_page_title = Gtk.Label(label=self._home_title())
        self.floating_page_title.add_css_class("floating-page-title")
        left.append(self.floating_page_title)

        controls = Gtk.Box(spacing=6)
        controls.append(self._make_window_control_button(
            "window-minimize-symbolic", self._on_window_minimize
        ))
        self.fullscreen_btn = self._make_window_control_button(
            "view-fullscreen-symbolic", self._on_window_toggle_fullscreen
        )
        controls.append(self.fullscreen_btn)
        controls.append(self._make_window_control_button(
            "window-close-symbolic", self._on_window_close, "close-btn"
        ))

        bar.append(left)
        bar.append(controls)

        handle.set_child(bar)
        return handle

    def _build_floating_sidebar(self):
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sidebar.add_css_class("sidebar")
        sidebar.add_css_class("floating-sidebar")
        sidebar.set_size_request(88, -1)

        nav_items = [
            ("dashboard", self.page_titles["dashboard"], "view-grid-symbolic"),
            ("fan",       self.page_titles["fan"],       "weather-tornado-symbolic"),
            ("lighting",  self.page_titles["lighting"],  "weather-clear-night-symbolic"),
            ("keyboard",  self.page_titles["keyboard"],  "input-keyboard-symbolic"),
            ("mux",       "MUX",                        "video-display-symbolic"),
        ]

        nav_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, margin_top=12)
        for page_id, label, icon_name in nav_items:
            nav_box.append(self._make_nav_button(page_id, label, icon_name))
        sidebar.append(nav_box)

        sidebar.append(Gtk.Label(vexpand=True))

        settings_btn = self._make_nav_button("settings", self.page_titles["settings"], "emblem-system-symbolic")
        sidebar.append(settings_btn)
        sidebar.append(Gtk.Box(margin_bottom=10))
        return sidebar

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("app-shell")
        root.set_overflow(Gtk.Overflow.HIDDEN)
        self._root_shell = root
        self.set_child(root)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(150)
        self.nav_labels  = {}
        self.nav_buttons = {}

        self._content_overlay = Gtk.Overlay(hexpand=True, vexpand=True)
        root.append(self._content_overlay)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                       hexpand=True, vexpand=True)
        body.set_margin_top(14)
        body.set_margin_start(14)
        body.set_margin_end(14)
        body.set_margin_bottom(14)
        self._content_overlay.set_child(body)

        self.menu_back_btn = Gtk.Button()
        self.menu_back_btn.add_css_class("menu-back-btn")
        self.menu_back_btn.set_child(self._build_menu_back_content())
        self.menu_back_btn.set_tooltip_text("Ana Menü" if get_lang() == "tr" else "Main Menu")
        self.menu_back_btn.connect("clicked", lambda *_: self._navigate("home"))
        self.menu_back_btn.set_sensitive(False)
        self.menu_back_btn.set_opacity(0.35)
        self.menu_back_btn.set_size_request(32, 32)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        content.add_css_class("content-shell")
        self.inline_page_header = Gtk.Box(spacing=8)
        self.inline_page_header.add_css_class("inline-page-header")
        self.inline_page_header.append(self.menu_back_btn)

        self.inline_page_title = Gtk.Label(label="", xalign=0)
        self.inline_page_title.add_css_class("inline-page-title")
        self.inline_page_title.set_hexpand(True)
        self.inline_page_header.append(self.inline_page_title)

        content.append(self.inline_page_header)
        content.append(self.stack)
        body.append(content)

        self.home_page = self._build_home_page()

        # Pages
        self.dashboard_page = DashboardPage(service=self.service, on_navigate=self._navigate)
        self.fan_page        = FanPage(service=self.service, on_profile_change=self._on_profile_mode_changed)
        self.lighting_page   = LightingPage(service=self.service)
        self.keyboard_page   = KeyboardPage(service=self.service)
        self.mux_page        = MUXPage(service=self.service)
        self.settings_page   = SettingsPage(
            on_theme_change=self._on_theme_change,
            on_lang_change=self._on_lang_change,
            on_temp_unit_change=self._on_temp_unit_change,
            service=self.service,
        )

        self.stack.add_named(self.home_page, "home")
        self.stack.add_named(self.dashboard_page, "dashboard")
        self.stack.add_named(self.fan_page,        "fan")
        self.stack.add_named(self.lighting_page,   "lighting")
        self.stack.add_named(self.keyboard_page,   "keyboard")
        self.stack.add_named(self.mux_page,        "mux")
        self.stack.add_named(self.settings_page,   "settings")

        self.fan_page.set_dark(self.app_theme == "dark")
        self.fan_page.set_temp_unit(self.temp_unit)
        self.dashboard_page.set_temp_unit(self.temp_unit)

        self._rebuilding = True
        self.settings_page.set_theme_index(
            0 if self.app_theme == "dark" else 1 if self.app_theme == "light" else 2)
        self.settings_page.set_lang_index(0 if get_lang() == "tr" else 1)
        self.settings_page.set_temp_unit_index(0 if self.temp_unit == "C" else 1)
        self._rebuilding = False

        self._navigate("home")
        self._set_performance_mode("balanced")
        self._update_fullscreen_button_icon()
        self.connect("notify::fullscreened", self._on_fullscreen_state_changed)
        self._install_responsive_scaling()

    def _build_home_page(self):
        sc = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._launcher_cards = {}

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(10)
        root.set_margin_start(14)
        root.set_margin_end(14)
        root.set_margin_bottom(12)
        sc.set_child(root)
        self._home_root_box = root
        self._home_scroll = sc

        model_strip = Gtk.Box(spacing=12)
        model_strip.add_css_class("status-strip")
        model_strip.add_css_class("home-model-strip")
        model_name = get_device_model_name()

        model_icon = self._build_model_brand_image(model_name, size=84)
        model_strip.append(model_icon)
        self._home_model_icon = model_icon

        details_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        details_col.set_hexpand(True)
        details_col.add_css_class("home-model-details")

        top_row = Gtk.Box(spacing=10)
        top_row.add_css_class("home-model-top")
        model_label = Gtk.Label(label=model_name, xalign=0)
        model_label.add_css_class("heading")
        model_label.set_hexpand(True)
        top_row.append(model_label)
        details_col.append(top_row)

        hw = self._get_home_hardware_info()
        labels = {
            "cpu": "CPU",
            "disk": "Disk" if get_lang() == "en" else "Disk",
            "gpu": "GPU",
            "ram": "RAM",
        }
        icons = {
            "cpu": "processor-symbolic",
            "disk": "drive-harddisk-symbolic",
            "gpu": "video-display-symbolic",
            "ram": "media-memory-symbolic",
        }

        spec_row = Gtk.Box(spacing=8, homogeneous=True)
        spec_row.add_css_class("home-spec-row")
        self._home_spec_row = spec_row
        for key in ("cpu", "disk", "gpu", "ram"):
            item = Gtk.Box(spacing=6)
            item.add_css_class("home-spec-item")

            ico = Gtk.Image.new_from_icon_name(icons[key])
            ico.set_pixel_size(14)
            item.append(ico)

            txt_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            ttl = Gtk.Label(label=labels[key], xalign=0)
            ttl.add_css_class("home-spec-title")
            txt_col.append(ttl)
            val = Gtk.Label(label=hw.get(key, "N/A"), xalign=0)
            val.add_css_class("home-spec-value")
            txt_col.append(val)
            item.append(txt_col)

            spec_row.append(item)

        details_col.append(spec_row)
        model_strip.append(details_col)
        root.append(model_strip)

        subtitle = Gtk.Label(label=self._home_subtitle(), xalign=0)
        subtitle.add_css_class("launcher-page-subtitle")
        root.append(subtitle)

        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(3)
        flow.set_min_children_per_line(1)
        flow.set_row_spacing(12)
        flow.set_column_spacing(12)
        flow.set_homogeneous(True)
        flow.set_valign(Gtk.Align.START)
        flow.set_hexpand(True)
        root.append(flow)
        self._home_flow = flow

        labels_tr = {
            "dashboard": "Sistem özeti ve canlı sensörler",
            "fan": "Fan, güç ve termal profiller",
            "lighting": "Aydınlatma efektleri ve parlaklık",
            "keyboard": "Özel tuşlar ve kısayollar",
            "mux": "GPU geçiş modu ve sürücü",
            "settings": "Tema, dil ve uygulama ayarları",
        }
        labels_en = {
            "dashboard": "System overview and live sensors",
            "fan": "Fan, power and thermal profiles",
            "lighting": "Lighting effects and brightness",
            "keyboard": "Special keys and shortcuts",
            "mux": "GPU switching mode and driver",
            "settings": "Theme, language and app settings",
        }
        desc = labels_tr if str(get_lang() or "").lower().startswith("tr") else labels_en

        cards = [
            ("dashboard", self.page_titles["dashboard"], "dashboard"),
            ("fan", self.page_titles["fan"], "fan"),
            ("lighting", self.page_titles["lighting"], "lighting"),
            ("keyboard", self.page_titles["keyboard"], "keyboard"),
            ("mux", "MUX", "mux"),
            ("settings", self.page_titles["settings"], "settings"),
        ]

        for page_id, title_text, icon_name in cards:
            flow.insert(self._make_launcher_card(page_id, title_text, desc.get(page_id, ""), icon_name), -1)

        self._apply_home_scale(self._ui_scale_bucket)

        return sc

    def _pick_ui_scale_bucket(self, width, height):
        if width < 1120 or height < 720:
            return "compact"
        if width > 1600 and height > 920:
            return "spacious"
        return "normal"

    def _install_responsive_scaling(self):
        if hasattr(self, "_root_shell") and self._root_shell is not None and not self._ui_scale_tick_id:
            self._ui_scale_tick_id = self._root_shell.add_tick_callback(self._on_scale_tick)
        GLib.idle_add(self._apply_ui_scale_from_current_size)

    def _on_scale_tick(self, _widget, _frame_clock):
        width, height = self._get_current_ui_size()
        if width != self._ui_last_width or height != self._ui_last_height:
            self._ui_last_width = width
            self._ui_last_height = height
            self._apply_ui_scale(width, height)
        return GLib.SOURCE_CONTINUE

    def _get_current_ui_size(self):
        width = 0
        height = 0
        if hasattr(self, "_root_shell") and self._root_shell is not None:
            try:
                width = max(width, int(self._root_shell.get_width() or 0))
                height = max(height, int(self._root_shell.get_height() or 0))
            except Exception:
                pass
            try:
                alloc = self._root_shell.get_allocation()
                width = max(width, int(alloc.width or 0))
                height = max(height, int(alloc.height or 0))
            except Exception:
                pass
        try:
            width = max(width, int(self.get_width() or 0))
            height = max(height, int(self.get_height() or 0))
        except Exception:
            pass
        return width, height

    def _apply_ui_scale_from_current_size(self):
        width, height = self._get_current_ui_size()
        self._ui_last_width = width
        self._ui_last_height = height
        self._apply_ui_scale(width, height)
        return False

    def _apply_ui_scale(self, width, height):
        bucket = self._pick_ui_scale_bucket(int(width or 0), int(height or 0))
        if bucket == self._ui_scale_bucket and getattr(self, "_ui_scale_applied_once", False):
            return

        self._ui_scale_bucket = bucket
        self._ui_scale_applied_once = True

        classes = ("app-scale-compact", "app-scale-normal", "app-scale-spacious")
        target_cls = f"app-scale-{bucket}"
        targets = [self]
        if hasattr(self, "_root_shell") and self._root_shell:
            targets.append(self._root_shell)

        for target in targets:
            for cls in classes:
                target.remove_css_class(cls)
            target.add_css_class(target_cls)

        self._apply_home_scale(bucket)
        for page_attr in ("dashboard_page", "fan_page", "lighting_page", "keyboard_page", "mux_page", "settings_page"):
            page = getattr(self, page_attr, None)
            if page and hasattr(page, "set_ui_scale"):
                try:
                    page.set_ui_scale(bucket, int(width or 0), int(height or 0))
                except Exception:
                    pass

    def _apply_home_scale(self, bucket):
        root = getattr(self, "_home_root_box", None)
        flow = getattr(self, "_home_flow", None)
        icon = getattr(self, "_home_model_icon", None)
        spec_row = getattr(self, "_home_spec_row", None)
        if not root or not flow:
            return

        if bucket == "compact":
            root.set_spacing(8)
            root.set_margin_top(8)
            root.set_margin_start(10)
            root.set_margin_end(10)
            root.set_margin_bottom(10)
            flow.set_row_spacing(10)
            flow.set_column_spacing(10)
            if icon is not None:
                icon.set_pixel_size(66)
            if spec_row is not None:
                spec_row.set_spacing(6)
        elif bucket == "spacious":
            root.set_spacing(12)
            root.set_margin_top(14)
            root.set_margin_start(18)
            root.set_margin_end(18)
            root.set_margin_bottom(16)
            flow.set_row_spacing(14)
            flow.set_column_spacing(14)
            if icon is not None:
                icon.set_pixel_size(92)
            if spec_row is not None:
                spec_row.set_spacing(10)
        else:
            root.set_spacing(10)
            root.set_margin_top(10)
            root.set_margin_start(14)
            root.set_margin_end(14)
            root.set_margin_bottom(12)
            flow.set_row_spacing(12)
            flow.set_column_spacing(12)
            if icon is not None:
                icon.set_pixel_size(84)
            if spec_row is not None:
                spec_row.set_spacing(8)

    def _make_launcher_card(self, page_id, title_text, subtitle_text, icon_key):
        btn = Gtk.Button()
        btn.add_css_class("launcher-card")
        btn.connect("clicked", lambda *_: self._navigate(page_id))

        overlay = Gtk.Overlay()
        column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        icon_wrap = Gtk.Box(halign=Gtk.Align.FILL, valign=Gtk.Align.START, vexpand=False)
        icon_wrap.add_css_class("launcher-icon-wrap")
        icon = self._make_fixed_menu_icon(icon_key, 42)
        icon.set_halign(Gtk.Align.START)
        icon.set_valign(Gtk.Align.START)
        icon.set_margin_start(6)
        icon.set_margin_top(2)
        icon_wrap.append(icon)
        column.append(icon_wrap)

        column.append(Gtk.Box(vexpand=True))

        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        text_box.set_margin_top(8)
        text_box.set_margin_bottom(8)
        text_box.set_margin_start(12)
        text_box.set_margin_end(12)

        title = Gtk.Label(label=title_text, xalign=0)
        title.add_css_class("launcher-card-title")
        text_box.append(title)

        subtitle = Gtk.Label(label=subtitle_text, xalign=0)
        subtitle.add_css_class("launcher-card-sub")
        subtitle.set_wrap(True)
        subtitle.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        text_box.append(subtitle)

        column.append(text_box)

        metric_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        metric_box.set_halign(Gtk.Align.END)
        metric_box.set_valign(Gtk.Align.END)
        metric_box.set_margin_end(8)
        metric_box.set_margin_bottom(8)

        metric_main = Gtk.Label(label="--", xalign=1)
        metric_main.add_css_class("launcher-metric-main")
        metric_box.append(metric_main)

        metric_sub = Gtk.Label(label="", xalign=1)
        metric_sub.add_css_class("launcher-metric-sub")
        metric_box.append(metric_sub)

        mini_bar = None
        cpu_bar = None
        gpu_bar = None
        if page_id == "dashboard":
            cpu_bar = Gtk.LevelBar()
            cpu_bar.set_min_value(0.0)
            cpu_bar.set_max_value(100.0)
            cpu_bar.set_value(0.0)
            cpu_bar.set_size_request(88, 4)
            cpu_bar.add_css_class("launcher-mini-bar")
            cpu_bar.add_css_class("launcher-util-bar")
            cpu_bar.add_css_class("launcher-cpu-bar")
            metric_box.append(cpu_bar)

            gpu_bar = Gtk.LevelBar()
            gpu_bar.set_min_value(0.0)
            gpu_bar.set_max_value(100.0)
            gpu_bar.set_value(0.0)
            gpu_bar.set_size_request(88, 4)
            gpu_bar.add_css_class("launcher-mini-bar")
            gpu_bar.add_css_class("launcher-util-bar")
            gpu_bar.add_css_class("launcher-gpu-bar")
            metric_box.append(gpu_bar)

        if page_id == "lighting":
            mini_bar = Gtk.LevelBar()
            mini_bar.set_min_value(0.0)
            mini_bar.set_max_value(100.0)
            mini_bar.set_value(0.0)
            mini_bar.set_size_request(76, 5)
            mini_bar.add_css_class("launcher-mini-bar")
            mini_bar.add_css_class("launcher-util-bar")
            metric_box.append(mini_bar)

        mode_badge = None
        if page_id == "mux":
            mode_badge = Gtk.Label(label="Hybrid")
            mode_badge.add_css_class("launcher-mode-badge")
            mode_badge.set_halign(Gtk.Align.END)
            mode_badge.set_valign(Gtk.Align.START)
            mode_badge.set_margin_top(8)
            mode_badge.set_margin_end(8)

        status_badge = Gtk.Label(label="!")
        status_badge.add_css_class("launcher-status-badge")
        status_badge.set_halign(Gtk.Align.START)
        status_badge.set_valign(Gtk.Align.START)
        status_badge.set_margin_top(8)
        status_badge.set_margin_start(8)
        status_badge.set_visible(False)

        overlay.set_child(column)
        overlay.add_overlay(metric_box)
        overlay.add_overlay(status_badge)
        if mode_badge is not None:
            overlay.add_overlay(mode_badge)

        self._launcher_cards[page_id] = {
            "button": btn,
            "icon": icon,
            "metric_main": metric_main,
            "metric_sub": metric_sub,
            "mini_bar": mini_bar,
            "cpu_bar": cpu_bar,
            "gpu_bar": gpu_bar,
            "mode_badge": mode_badge,
            "status_badge": status_badge,
        }

        btn.set_child(overlay)
        return btn

    def _make_fixed_menu_icon(self, icon_key, size):
        dark = self._is_effective_dark()
        rgb = (0.92, 0.94, 0.97) if dark else (0.16, 0.18, 0.22)
        return FixedMenuIcon(icon_key, size=size, rgb=rgb)

    def _build_menu_back_content(self):
        row = Gtk.Box()
        row.set_halign(Gtk.Align.CENTER)
        row.set_valign(Gtk.Align.CENTER)
        dark = self._is_effective_dark()
        rgb = (1.0, 1.0, 1.0) if dark else (0.16, 0.18, 0.22)
        row.append(FixedMenuIcon("back", size=18, rgb=rgb, line_width=2.8))
        return row

    def _is_effective_dark(self):
        if self.app_theme == "dark":
            return True
        if self.app_theme == "light":
            return False
        if HAS_ADW:
            try:
                return bool(Adw.StyleManager.get_default().get_dark())
            except Exception:
                return True
        settings = Gtk.Settings.get_default()
        if settings is not None:
            try:
                return bool(settings.get_property("gtk-application-prefer-dark-theme"))
            except Exception:
                pass
        return True

    def _refresh_launcher_icon_colors(self):
        dark = self._is_effective_dark()
        rgb = (0.92, 0.94, 0.97) if dark else (0.16, 0.18, 0.22)
        for refs in self._launcher_cards.values():
            icon = refs.get("icon")
            if icon is None:
                continue
            try:
                icon.rgb = rgb
                icon.queue_draw()
            except Exception:
                pass

    def _on_window_minimize(self, *_):
        try:
            self.minimize()
        except Exception:
            pass

    def _on_window_close(self, *_):
        self.close()

    def _on_window_toggle_fullscreen(self, *_):
        try:
            is_fullscreened = bool(self.get_property("fullscreened"))
            if is_fullscreened:
                self.unfullscreen()
            else:
                self.fullscreen()
        except Exception:
            pass

    def _on_fullscreen_state_changed(self, *_):
        self._update_fullscreen_button_icon()

    def _update_fullscreen_button_icon(self):
        if not hasattr(self, "fullscreen_btn"):
            return
        try:
            is_fullscreened = bool(self.get_property("fullscreened"))
        except Exception:
            is_fullscreened = False
        icon_name = "view-restore-symbolic" if is_fullscreened else "view-fullscreen-symbolic"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(16)
        self.fullscreen_btn.set_child(icon)

    def _make_nav_button(self, page_id, label, icon_name):
        btn = Gtk.Button()
        btn.add_css_class("nav-item")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                      halign=Gtk.Align.CENTER)
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(22)
        icon.add_css_class("nav-icon")
        box.append(icon)

        lbl = Gtk.Label(label=label)
        lbl.add_css_class("nav-label")
        self.nav_labels[page_id] = lbl
        box.append(lbl)

        btn.set_child(box)
        btn.connect("clicked", lambda w, pid=page_id: self._navigate(pid))
        self.nav_buttons[page_id] = btn
        return btn

    def _find_first_scrolled_window(self, widget):
        if widget is None:
            return None
        if isinstance(widget, Gtk.ScrolledWindow):
            return widget

        child = widget.get_first_child()
        while child is not None:
            found = self._find_first_scrolled_window(child)
            if found is not None:
                return found
            child = child.get_next_sibling()
        return None

    def _set_back_button_floating(self, floating):
        if not hasattr(self, "menu_back_btn"):
            return
        floating = bool(floating)
        if self._back_button_floating == floating:
            return

        btn = self.menu_back_btn
        parent = btn.get_parent()
        if parent is not None:
            parent.remove(btn)

        if floating and self._content_overlay is not None:
            btn.add_css_class("floating-back-btn-active")
            btn.set_halign(Gtk.Align.START)
            btn.set_valign(Gtk.Align.START)
            self._content_overlay.add_overlay(btn)
        else:
            btn.remove_css_class("floating-back-btn-active")
            btn.set_halign(Gtk.Align.FILL)
            btn.set_valign(Gtk.Align.FILL)
            if hasattr(self, "inline_page_header"):
                self.inline_page_header.prepend(btn)

        self._back_button_floating = floating

    def _clear_scroll_tracking(self):
        if self._scroll_adjustment is not None and self._scroll_adjustment_handler:
            try:
                self._scroll_adjustment.disconnect(self._scroll_adjustment_handler)
            except Exception:
                pass
        self._scroll_adjustment = None
        self._scroll_adjustment_handler = 0

    def _on_scroll_value_changed(self, adjustment):
        try:
            value = float(adjustment.get_value())
        except Exception:
            value = 0.0
        should_float = value > 36 and hasattr(self, "menu_back_btn") and self.menu_back_btn.get_sensitive()
        self._set_back_button_floating(should_float)

    def _bind_back_button_scroll_behavior(self, page_id):
        self._clear_scroll_tracking()
        self._set_back_button_floating(False)

    def _navigate(self, page_id):
        self.stack.set_visible_child_name(page_id)
        if hasattr(self, "inline_page_header"):
            self.inline_page_header.set_visible(page_id != "home")
        if hasattr(self, "inline_page_title"):
            if page_id == "home":
                self.inline_page_title.set_label("")
            else:
                self.inline_page_title.set_label(self.page_titles.get(page_id, page_id.title()))
        if hasattr(self, "menu_back_btn"):
            is_home = page_id == "home"
            self.menu_back_btn.set_sensitive(not is_home)
            self.menu_back_btn.set_visible(not is_home)
            self.menu_back_btn.set_opacity(1.0)
            self._set_back_button_floating(False)
        self._bind_back_button_scroll_behavior(page_id)
        for pid, btn in self.nav_buttons.items():
            if pid == page_id:
                btn.add_css_class("active")
            elif "active" in btn.get_css_classes():
                btn.remove_css_class("active")
        page = self.stack.get_child_by_name(page_id)
        if hasattr(page, "refresh"):
            page.refresh()
        if page_id == "home":
            self._refresh_launcher_metrics()

    def _update_logo(self):
        """Load the app logo from disk into self.logo_icon."""
        logo_path = os.path.join(IMAGES_DIR, "omenapplogo.png")
        if hasattr(self, 'logo_icon'):
            if os.path.exists(logo_path):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(logo_path, 48, 48, True)
                self.logo_icon.set_from_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            else:
                self.logo_icon.set_from_icon_name("computer-symbolic")

    # ── Daemon connection ─────────────────────────────────────────────────────

    def _connect_daemon(self):
        try:
            from pydbus import SystemBus
            bus = SystemBus()
            self.service = bus.get("com.yyl.hpmanager")
            self.ready   = True
            self.dashboard_page.set_service(self.service)
            self.fan_page.set_service(self.service)
            self.lighting_page.set_service(self.service)
            if hasattr(self, 'keyboard_page'):
                self.keyboard_page.service = self.service
            self.mux_page.set_service(self.service)
            self.settings_page.set_service(self.service)
            print("Daemon connected")
            self._refresh_launcher_metrics()
        except Exception as e:
            print(f"⚠ Daemon connection failed: {e}")
            print("  Application will run without daemon support.")

    def _set_performance_mode(self, profile):
        mode_map = {
            "power-saver": "eco",
            "balanced": "balanced",
            "performance": "performance",
            "eco": "eco",
        }
        mode = mode_map.get(str(profile), "balanced")
        prev_mode = self.performance_mode
        self.performance_mode = mode

        classes = ("app-perf-eco", "app-perf-balanced", "app-perf-performance")
        target_class = f"app-perf-{mode}"
        targets = [self]
        if hasattr(self, "_root_shell") and self._root_shell:
            targets.append(self._root_shell)

        for target in targets:
            for cls in classes:
                target.remove_css_class(cls)
            target.add_css_class(target_class)

        # In dark mode, accent color follows active performance mode.
        if prev_mode != mode and self._is_effective_dark():
            self._apply_css()

    def _on_profile_mode_changed(self, profile):
        self._set_performance_mode(profile)

    # ── Settings callbacks ────────────────────────────────────────────────────

    def _on_theme_change(self, theme):
        if self._rebuilding:
            return
        self.app_theme = theme
        self._save_config()
        self._apply_theme_preference()
        self._apply_css()
        self._refresh_launcher_icon_colors()
        if hasattr(self, "menu_back_btn"):
            self.menu_back_btn.set_child(self._build_menu_back_content())
        if hasattr(self, 'fan_page'):
            self.fan_page.set_dark(theme == "dark")
        self._update_logo()
        self._refresh_launcher_metrics()

    def _on_lang_change(self, lang):
        if self._rebuilding:
            return
        if get_lang() == lang:
            return
        set_lang(lang)
        self._save_config()
        self.page_titles = {
            "dashboard": T("dashboard"),
            "fan": T("fan"),
            "lighting": T("lighting"),
            "keyboard": T("keyboard"),
            "mux": "MUX",
            "settings": T("settings"),
        }
        for pid, lbl in self.nav_labels.items():
            if pid in self.page_titles:
                lbl.set_label(self.page_titles[pid])
        if hasattr(self, "inline_page_title"):
            current = self.stack.get_visible_child_name() if hasattr(self, "stack") else "home"
            if current == "home":
                self.inline_page_title.set_label("")
            else:
                self.inline_page_title.set_label(self.page_titles.get(current, current.title()))
        if hasattr(self, "menu_back_btn"):
            self.menu_back_btn.set_child(self._build_menu_back_content())
            self.menu_back_btn.set_tooltip_text("Ana Menü" if get_lang() == "tr" else "Main Menu")
        # Defer page rebuild — cannot destroy widgets inside a signal handler
        GLib.idle_add(self._rebuild_pages)

    def _start_launcher_metrics(self):
        if self._launcher_timer_id is not None:
            return
        self._refresh_launcher_metrics()
        self._launcher_timer_id = GLib.timeout_add(_LAUNCHER_REFRESH_MS, self._tick_launcher_metrics)

    def _tick_launcher_metrics(self):
        if hasattr(self, "stack"):
            try:
                if self.stack.get_visible_child_name() != "home":
                    return GLib.SOURCE_CONTINUE
            except Exception:
                pass
        self._refresh_launcher_metrics()
        return GLib.SOURCE_CONTINUE

    def _refresh_launcher_metrics(self):
        if hasattr(self, "stack"):
            try:
                if self.stack.get_visible_child_name() != "home":
                    return
            except Exception:
                pass
        if self._launcher_busy:
            return
        self._launcher_busy = True
        threading.Thread(target=self._fetch_launcher_metrics, daemon=True).start()

    def _get_nvidia_runtime_status_path(self):
        if self._nvidia_runtime_status_scanned:
            return self._nvidia_runtime_status_path

        self._nvidia_runtime_status_scanned = True
        try:
            for dev in os.listdir("/sys/bus/pci/devices"):
                vendor_file = f"/sys/bus/pci/devices/{dev}/vendor"
                if not os.path.exists(vendor_file):
                    continue
                try:
                    with open(vendor_file) as f:
                        if f.read().strip() == "0x10de":
                            path = f"/sys/bus/pci/devices/{dev}/power/runtime_status"
                            self._nvidia_runtime_status_path = path if os.path.exists(path) else None
                            break
                except Exception:
                    continue
        except Exception:
            pass
        return self._nvidia_runtime_status_path

    def _is_nvidia_awake(self):
        path = self._get_nvidia_runtime_status_path()
        if path is None or not os.path.exists(path):
            return True
        try:
            with open(path) as f:
                return f.read().strip() != "suspended"
        except Exception:
            return True

    def _fetch_launcher_metrics(self):
        data = {
            "ok": bool(self.service),
            "sys": {},
            "fan": {},
            "pp": {},
            "light": {},
            "gpu": {},
            "cpu_pct": None,
            "gpu_pct": None,
        }
        try:
            if self.service:
                try:
                    data["sys"] = json.loads(self.service.GetSystemInfo())
                except Exception:
                    pass
                try:
                    data["fan"] = json.loads(self.service.GetFanInfo())
                except Exception:
                    pass
                try:
                    data["pp"] = json.loads(self.service.GetPowerProfile())
                except Exception:
                    pass
                try:
                    data["light"] = json.loads(self.service.GetState())
                except Exception:
                    pass
                try:
                    data["gpu"] = json.loads(self.service.GetGpuInfo())
                except Exception:
                    pass

            try:
                with open("/proc/stat") as f:
                    cpu = f.readline().strip().split()
                vals = [int(x) for x in cpu[1:9]]
                idle_all = vals[3] + vals[4]
                total = sum(vals)
                pct = self._launcher_cpu_smooth
                if self._launcher_cpu_prev is not None:
                    prev_total, prev_idle = self._launcher_cpu_prev
                    total_delta = total - prev_total
                    idle_delta = idle_all - prev_idle
                    if total_delta > 0:
                        pct = (1.0 - (idle_delta / total_delta)) * 100.0
                self._launcher_cpu_prev = (total, idle_all)
                if self._launcher_cpu_smooth <= 0.0:
                    self._launcher_cpu_smooth = max(0.0, min(100.0, pct))
                else:
                    self._launcher_cpu_smooth = (self._launcher_cpu_smooth * 0.62) + (max(0.0, min(100.0, pct)) * 0.38)
                data["cpu_pct"] = self._launcher_cpu_smooth
            except Exception:
                pass

            if self._nvidia_smi:
                if self._is_nvidia_awake():
                    try:
                        out = subprocess.check_output(
                            [self._nvidia_smi, "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                            stderr=subprocess.DEVNULL,
                            timeout=1.5,
                        ).decode().strip()
                        data["gpu_pct"] = float(out)
                    except Exception:
                        pass
                else:
                    data["gpu_pct"] = 0.0
        finally:
            GLib.idle_add(self._apply_launcher_metrics, data)

    def _set_launcher_badge(self, page_id, visible):
        refs = self._launcher_cards.get(page_id)
        if not refs:
            return
        badge = refs.get("status_badge")
        if badge is not None:
            badge.set_visible(bool(visible))

    def _set_launcher_dimmed(self, page_id, dimmed):
        refs = self._launcher_cards.get(page_id)
        if not refs:
            return
        btn = refs.get("button")
        if btn is None:
            return
        if dimmed:
            btn.add_css_class("launcher-card-dimmed")
        else:
            btn.remove_css_class("launcher-card-dimmed")

    @staticmethod
    def _set_temp_tone(label, temp):
        for cls in ("launcher-temp-cool", "launcher-temp-warm", "launcher-temp-hot"):
            label.remove_css_class(cls)
        try:
            t = float(temp)
        except Exception:
            t = 0.0
        if t > 0 and t < 50:
            label.add_css_class("launcher-temp-cool")
        elif t >= 80:
            label.add_css_class("launcher-temp-hot")
        else:
            label.add_css_class("launcher-temp-warm")

    def _apply_launcher_metrics(self, data):
        self._launcher_busy = False
        if not self._launcher_cards:
            return False

        ok = bool(data.get("ok"))
        sysi = data.get("sys", {}) or {}
        fani = data.get("fan", {}) or {}
        ppi = data.get("pp", {}) or {}
        ligi = data.get("light", {}) or {}
        gpui = data.get("gpu", {}) or {}
        cpu_pct = data.get("cpu_pct")
        gpu_pct = data.get("gpu_pct")

        if not ok:
            for pid, refs in self._launcher_cards.items():
                if pid == "settings":
                    self._set_launcher_dimmed(pid, False)
                    badge = refs.get("status_badge")
                    if badge is not None:
                        badge.add_css_class("launcher-status-badge-critical")
                    self._set_launcher_badge(pid, True)
                    refs["metric_main"].set_label("Daemon Kapalı" if get_lang() == "tr" else "Daemon Offline")
                    refs["metric_sub"].set_label("Ayarlar" if get_lang() == "tr" else "Settings")
                else:
                    self._set_launcher_dimmed(pid, True)
                    self._set_launcher_badge(pid, False)
                    refs["metric_main"].set_label("Beklemede" if get_lang() == "tr" else "Standby")
                    refs["metric_sub"].set_label("-")
            return False

        for pid, refs in self._launcher_cards.items():
            self._set_launcher_dimmed(pid, False)
            badge = refs.get("status_badge")
            if badge is not None:
                badge.remove_css_class("launcher-status-badge-critical")

        dash = self._launcher_cards.get("dashboard")
        if dash:
            ct = int(sysi.get("cpu_temp", 0) or 0)
            gt = int(sysi.get("gpu_temp", 0) or 0)
            cp = int(cpu_pct) if cpu_pct is not None else 0
            gp = int(gpu_pct) if gpu_pct is not None else 0
            dash["metric_main"].set_label(f"CPU {ct}°C • {cp}%")
            dash["metric_sub"].set_label(f"GPU {gt}°C • {gp}%")
            self._set_temp_tone(dash["metric_main"], ct)
            self._set_temp_tone(dash["metric_sub"], gt)
            if dash.get("cpu_bar") is not None:
                dash["cpu_bar"].set_value(max(0, min(100, cp)))
            if dash.get("gpu_bar") is not None:
                dash["gpu_bar"].set_value(max(0, min(100, gp)))
            self._set_launcher_badge("dashboard", (not ok) or (ct <= 0 and gt <= 0))

        perf = self._launcher_cards.get("fan")
        if perf:
            active = str(ppi.get("active", "balanced"))
            self._set_performance_mode(active)
            profile_map = {
                "power-saver": "Sessiz" if get_lang() == "tr" else "Quiet",
                "balanced": "Dengeli" if get_lang() == "tr" else "Balanced",
                "performance": "Performans" if get_lang() == "tr" else "Performance",
            }
            profile = profile_map.get(active, active.capitalize())
            fans = fani.get("fans", {}) if isinstance(fani, dict) else {}
            rpms = []
            for fid in sorted(fans.keys()):
                try:
                    cur = int(fans[fid].get("current", 0))
                except Exception:
                    cur = 0
                if cur > 0:
                    rpms.append(str(cur))
            rpm_str = "/".join(rpms) if rpms else "0"
            perf["metric_main"].set_label(profile)
            perf["metric_sub"].set_label(f"{rpm_str} RPM")
            self._set_launcher_badge("fan", (not ok) or (not bool(fani)))

        light = self._launcher_cards.get("lighting")
        if light:
            mode = str(ligi.get("mode", "unknown"))
            mode_map = {
                "static": T("static_eff"),
                "breathing": T("breathing"),
                "wave": T("wave"),
                "cycle": T("cycle"),
            }
            bright = int(ligi.get("brightness", 0) or 0)
            light["metric_main"].set_label(mode_map.get(mode, mode.capitalize()))
            light["metric_sub"].set_label(f"{bright}%")
            if light.get("mini_bar") is not None:
                light["mini_bar"].set_value(max(0, min(100, bright)))
            lighting_module_ok = os.path.exists("/sys/module/hp_rgb_lighting")
            self._set_launcher_badge("lighting", (not ok) or (not lighting_module_ok) or (not bool(ligi)))

        mux = self._launcher_cards.get("mux")
        if mux:
            mode = str(gpui.get("mode", "unknown"))
            mode_map = {
                "integrated": "iGPU",
                "intel": "iGPU",
                "discrete": "dGPU",
                "nvidia": "dGPU",
                "dedicated": "dGPU",
                "hybrid": "Hybrid",
                "on-demand": "Hybrid",
            }
            mode_text = mode_map.get(mode, "N/A")
            mux["metric_main"].set_label(mode_text)
            mux["metric_sub"].set_label("")
            if mux.get("mode_badge") is not None:
                mux["mode_badge"].set_label(mode_text)
                if mode_text == "N/A" or mode.lower() == "unknown":
                    mux["mode_badge"].add_css_class("launcher-mode-badge-muted")
                else:
                    mux["mode_badge"].remove_css_class("launcher-mode-badge-muted")
            self._set_launcher_badge("mux", (not ok) or (mode_text == "N/A"))

        keyboard = self._launcher_cards.get("keyboard")
        if keyboard:
            keyboard["metric_main"].set_label("0 Aktif" if get_lang() == "tr" else "0 Active")
            keyboard["metric_sub"].set_label("Varsayılan" if get_lang() == "tr" else "Default")
            self._set_launcher_badge("keyboard", False)

        settings = self._launcher_cards.get("settings")
        if settings:
            settings["metric_main"].set_label("OK" if ok else "Offline")
            settings["metric_sub"].set_label("Daemon")
            self._set_launcher_badge("settings", not ok)

        return False

    def _on_temp_unit_change(self, unit):
        if self._rebuilding:
            return
        self.temp_unit = unit
        self._save_config()
        if hasattr(self, 'fan_page'):
            self.fan_page.set_temp_unit(unit)
        if hasattr(self, 'dashboard_page'):
            self.dashboard_page.set_temp_unit(unit)

    # ── Page rebuild (language change) ────────────────────────────────────────

    def _rebuild_pages(self):
        """Destroy and recreate all pages so T() picks up the new language."""
        self._rebuilding = True
        try:
            current_page = self.stack.get_visible_child_name()

            for attr in ('dashboard_page', 'fan_page', 'lighting_page'):
                page = getattr(self, attr, None)
                if page and hasattr(page, 'cleanup'):
                    page.cleanup()

            for name in ("home", "dashboard", "fan", "lighting", "keyboard", "mux", "settings"):
                child = self.stack.get_child_by_name(name)
                if child:
                    self.stack.remove(child)

            self.home_page = self._build_home_page()
            self.dashboard_page = DashboardPage(service=self.service, on_navigate=self._navigate)
            self.fan_page        = FanPage(service=self.service, on_profile_change=self._on_profile_mode_changed)
            self.lighting_page   = LightingPage(service=self.service)
            self.keyboard_page   = KeyboardPage(service=self.service)
            self.mux_page        = MUXPage(service=self.service)
            self.settings_page   = SettingsPage(
                on_theme_change=self._on_theme_change,
                on_lang_change=self._on_lang_change,
                on_temp_unit_change=self._on_temp_unit_change,
                service=self.service,
            )

            self.stack.add_named(self.home_page, "home")
            self.stack.add_named(self.dashboard_page, "dashboard")
            self.stack.add_named(self.fan_page,        "fan")
            self.stack.add_named(self.lighting_page,   "lighting")
            self.stack.add_named(self.keyboard_page,   "keyboard")
            self.stack.add_named(self.mux_page,        "mux")
            self.stack.add_named(self.settings_page,   "settings")

            self.fan_page.set_dark(self.app_theme == "dark")
            self.fan_page.set_temp_unit(self.temp_unit)
            self.dashboard_page.set_temp_unit(self.temp_unit)
            if self.performance_mode == "eco":
                self._set_performance_mode("power-saver")
            elif self.performance_mode == "performance":
                self._set_performance_mode("performance")
            else:
                self._set_performance_mode("balanced")

            self.settings_page.set_theme_index(
                0 if self.app_theme == "dark" else 1 if self.app_theme == "light" else 2)
            self.settings_page.set_lang_index(0 if get_lang() == "tr" else 1)
            self.settings_page.set_temp_unit_index(0 if self.temp_unit == "C" else 1)

            self._navigate(current_page or "home")
            self._apply_ui_scale_from_current_size()
            self._refresh_launcher_metrics()
        finally:
            self._rebuilding = False
        return False  # Do not repeat GLib.idle_add

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def do_close_request(self):
        self._clear_scroll_tracking()
        if self._ui_scale_tick_id:
            try:
                if hasattr(self, "_root_shell") and self._root_shell is not None:
                    self._root_shell.remove_tick_callback(self._ui_scale_tick_id)
            except Exception:
                pass
            self._ui_scale_tick_id = 0
        if self._launcher_timer_id:
            try:
                GLib.source_remove(self._launcher_timer_id)
            except Exception:
                pass
            self._launcher_timer_id = None
        for attr in ('dashboard_page', 'lighting_page', 'fan_page'):
            page = getattr(self, attr, None)
            if page and hasattr(page, 'cleanup'):
                try:
                    page.cleanup()
                except Exception as e:
                    print(f"Cleanup error for {attr}: {e}")
        try:
            self.get_application().quit()
        except Exception as e:
            print(f"Application quit error: {e}")
        return False


# ── Application ───────────────────────────────────────────────────────────────

class HPManagerApp(Adw.Application if HAS_ADW else Gtk.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self._on_activate)

    def _on_activate(self, app):
        print("Initializing window...", flush=True)
        win = HPManagerWindow(application=app)
        win.present()


def main():
    print("Initializing Application...", flush=True)
    if not HAS_ADW:
        print("Warning: libadwaita (Adw) not found. Running with GTK fallback theme support.", flush=True)
    app = HPManagerApp(
        application_id="com.yyl.hpmanager.gui",
        flags=Gio.ApplicationFlags.FLAGS_NONE,
    )
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
