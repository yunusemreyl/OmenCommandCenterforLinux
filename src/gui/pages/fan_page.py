#!/usr/bin/env python3
"""
Fan & Power Control Page — v1.3.7 with i18n.
"""
import os, json, subprocess, shutil, glob, threading, time, concurrent.futures
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gdk, GObject
from widgets.smooth_scroll import SmoothScrolledWindow

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
# CircularGauge integration removed as per instruction
from widgets.fan_curve import FanCurveWidget
import cairo
import math

DEFAULT_MODE_SYNC_DELAY_MS = 1500
CUSTOM_MODE_SYNC_DELAY_MS = 3000
_DBUS_TIMEOUT = 5  # seconds — prevents D-Bus hangs from freezing app
_dbus_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="dbus")


def _dbus_call(fn, *args, timeout=_DBUS_TIMEOUT):
    """Run a D-Bus proxy call with a timeout to avoid indefinite blocking."""
    fut = _dbus_pool.submit(fn, *args)
    try:
        return fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        print(f"⚠ D-Bus call timed out after {timeout}s: {fn}")
        return None
    except Exception as e:
        print(f"⚠ D-Bus call failed: {e}")
        return None

class FanSparkline(Gtk.DrawingArea):
    def __init__(self, color, history_len=60):
        super().__init__()
        self.set_size_request(-1, 30)
        self.color = color
        self.history_len = history_len
        self.history = [0] * history_len
        self._dark = True
        self.set_draw_func(self._draw)

    def set_dark(self, is_dark):
        self._dark = is_dark
        self.queue_draw()

    def add_value(self, val):
        self.history.pop(0)
        self.history.append(val)
        self.queue_draw()

    def set_chart_size(self, width, height):
        self.set_size_request(int(width), int(height))

    def _draw(self, _, cr, w, h):
        cr.set_line_width(2)
        cr.set_line_cap(1)
        cr.set_line_join(1)
        
        max_val = max(max(self.history), 100) # prevent div by 0 and give baseline scale
        
        # Draw gradient under the line
        cr.save()
        pattern = cairo.LinearGradient(0, 0, 0, h)
        if self._dark:
            pattern.add_color_stop_rgba(0, self.color[0], self.color[1], self.color[2], 0.3)
            pattern.add_color_stop_rgba(1, self.color[0], self.color[1], self.color[2], 0.0)
        else:
            pattern.add_color_stop_rgba(0, self.color[0], self.color[1], self.color[2], 0.2)
            pattern.add_color_stop_rgba(1, self.color[0], self.color[1], self.color[2], 0.0)
            
        cr.set_source(pattern)

        dx = w / (self.history_len - 1)
        cr.move_to(0, h)
        
        for i, val in enumerate(self.history):
            x = i * dx
            y = h - (val / max_val) * (h - 2)
            cr.line_to(x, y)
            
        cr.line_to(w, h)
        cr.close_path()
        cr.fill()
        cr.restore()
        
        # Draw line graph
        cr.set_source_rgb(*self.color)
        for i, val in enumerate(self.history):
            x = i * dx
            y = h - (val / max_val) * (h - 2)
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke()
        
        # Draw dot on current value
        current_y = h - (self.history[-1] / max_val) * (h - 2)
        cr.arc(w - 2, current_y, 3, 0, 2 * math.pi)
        if self._dark:
            cr.set_source_rgb(1, 1, 1)
        else:
            cr.set_source_rgb(*self.color)
        cr.fill()

class RotatingFanWidget(Gtk.DrawingArea):
    def __init__(self, size=160):
        super().__init__()
        self.set_size_request(size, size)
        self.val = 0
        self.txt = "0 RPM"
        self.rotation = 0.0  # phase value for subtle gauge glow animation
        self._dark = True
        self.theme = "balanced"

        self.set_draw_func(self._draw)

    def set_val(self, value, text):
        self.val = value
        self.txt = text
        self.queue_draw()

    def set_dark(self, is_dark):
        self._dark = is_dark
        self.queue_draw()

    def set_theme(self, theme):
        self.theme = theme if theme in ("eco", "balanced", "performance") else "balanced"
        self.queue_draw()

    def set_diameter(self, size):
        s = max(96, int(size))
        self.set_size_request(s, s)
        
    def tick_rotation(self, max_rpm=6000):
        if self.val <= 0:
            return

        speed = 0.04 + (self.val / 100.0) * 0.14
        self.rotation += speed
        if self.rotation >= 2 * math.pi:
            self.rotation -= 2 * math.pi
        self.queue_draw()

    def _draw(self, _, cr, w, h):
        cx, cy = w / 2, h / 2
        radius = min(cx, cy) - 8
        track_width = max(14, radius * 0.26)
        inner_r = radius - (track_width * 0.58)
        pct = max(0.0, min(100.0, float(self.val))) / 100.0

        if self.theme == "eco":
            c0 = (0.35, 0.92, 0.56)
            c1 = (0.16, 0.69, 0.34)
            glow = (0.82, 1.0, 0.90)
        elif self.theme == "performance":
            c0 = (1.0, 0.46, 0.35)
            c1 = (0.86, 0.20, 0.18)
            glow = (1.0, 0.90, 0.86)
        else:
            c0 = (0.10, 0.86, 1.00)
            c1 = (0.15, 0.55, 1.00)
            glow = (0.88, 0.97, 1.0)

        # Outer contour ring
        cr.set_line_width(2.2)
        if self._dark:
            cr.set_source_rgba(0.56, 0.64, 0.74, 0.20)
        else:
            cr.set_source_rgba(0.10, 0.12, 0.16, 0.20)
        cr.arc(cx, cy, radius + 1.5, 0, 2 * math.pi)
        cr.stroke()

        # Thick base track
        cr.set_line_width(track_width)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        if self._dark:
            cr.set_source_rgba(0.25, 0.30, 0.38, 0.72)
        else:
            cr.set_source_rgba(0.74, 0.78, 0.84, 0.82)
        cr.arc(cx, cy, radius - track_width * 0.5, 0, 2 * math.pi)
        cr.stroke()

        # Progress arc with cyan-blue gradient, similar to Legion-style heavy gauge
        start = -math.pi / 2
        end = start + (pct * 2 * math.pi)
        grad = cairo.LinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
        if self._dark:
            grad.add_color_stop_rgba(0.0, c0[0], c0[1], c0[2], 0.96)
            grad.add_color_stop_rgba(1.0, c1[0], c1[1], c1[2], 0.96)
        else:
            grad.add_color_stop_rgba(0.0, c0[0], c0[1], c0[2], 0.90)
            grad.add_color_stop_rgba(1.0, c1[0], c1[1], c1[2], 0.90)
        cr.set_source(grad)
        cr.arc(cx, cy, radius - track_width * 0.5, start, end)
        cr.stroke()

        # Endpoint glow cap
        ex = cx + math.cos(end) * (radius - track_width * 0.5)
        ey = cy + math.sin(end) * (radius - track_width * 0.5)
        pulse = 0.80 + 0.20 * math.sin(self.rotation * 1.7)
        cr.set_source_rgba(glow[0], glow[1], glow[2], 0.70 * pulse)
        cr.arc(ex, ey, max(2.6, track_width * 0.17), 0, 2 * math.pi)
        cr.fill()

        # Inner hub glow
        hub = cairo.RadialGradient(cx, cy, inner_r * 0.18, cx, cy, inner_r)
        if self._dark:
            hub.add_color_stop_rgba(0.0, 0.05, 0.07, 0.10, 0.86)
            hub.add_color_stop_rgba(1.0, 0.03, 0.04, 0.06, 0.34)
        else:
            hub.add_color_stop_rgba(0.0, 0.93, 0.95, 0.98, 0.88)
            hub.add_color_stop_rgba(1.0, 0.86, 0.89, 0.94, 0.52)
        cr.set_source(hub)
        cr.arc(cx, cy, inner_r, 0, 2 * math.pi)
        cr.fill()

        # Center value text
        value_txt = f"{int(round(self.val))}%"
        cr.select_font_face("JetBrains Mono", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(max(15, radius * 0.37))
        te = cr.text_extents(value_txt)
        cr.move_to(cx - (te.width / 2 + te.x_bearing), cy + 2)
        if self._dark:
            cr.set_source_rgba(0.93, 0.96, 1.0, 0.95)
        else:
            cr.set_source_rgba(0.10, 0.16, 0.24, 0.92)
        cr.show_text(value_txt)

def T(k):
    from i18n import T as _T
    return _T(k)


def _find_hwmon_by_name(name):
    base = "/sys/class/hwmon"
    if not os.path.exists(base):
        return None
    for d in sorted(os.listdir(base)):
        path = os.path.join(base, d)
        nf = os.path.join(path, "name")
        try:
            with open(nf) as f:
                if f.read().strip().lower() == name:
                    return path
        except Exception:
            pass
    return None


class SystemMonitor(threading.Thread):
    def __init__(self, services_provider):
        super().__init__(daemon=True)
        self.services_provider = services_provider
        self.running = True
        self._active_event = threading.Event()
        self._active_event.set()
        self.lock = threading.Lock()
        self.data = {
            "cpu_temp": 0.0,
            "gpu_temp": 0.0,
            "fan_info": dict(),
            "power_profile": dict(),
            "all_sensors": [],
            "power_conflict": None,
        }
        self._conflict_cache = None
        self._conflict_counter = 0
        self._collect_sensors = False
        self._sensor_refresh_every = 3
        self._sensor_cycle = 0

    def set_collect_sensors(self, enabled):
        self._collect_sensors = bool(enabled)

    def set_active(self, active):
        if active:
            self._active_event.set()
        else:
            self._active_event.clear()

    def run(self):
        while self.running:
            if not self._active_event.is_set():
                time.sleep(4.0)
                continue

            c, g = 0.0, 0.0
            fi, pp, si = {}, {}, {}
            services = self.services_provider()

            if services:
                platform_svc = services.get("platform")
                fan_svc = services.get("fan")
                power_svc = services.get("power")

                if platform_svc:
                    try:
                        raw = _dbus_call(platform_svc.GetSystemInfo)
                        if raw is not None:
                            si = json.loads(raw)
                            c = si.get("cpu_temp", 0.0)
                            g = si.get("gpu_temp", 0.0)
                    except Exception: pass

                if fan_svc:
                    try:
                        raw = _dbus_call(fan_svc.GetFanInfo)
                        if raw is not None:
                            fi = json.loads(raw)
                    except Exception: pass

                if power_svc:
                    try:
                        raw = _dbus_call(power_svc.GetPowerProfile)
                        if raw is not None:
                            pp = json.loads(raw)
                    except Exception: pass

            sensors = []
            if self._collect_sensors:
                self._sensor_cycle += 1
                # Full hwmon scan is relatively expensive; refresh less often while expanded.
                if self._sensor_cycle >= self._sensor_refresh_every:
                    self._sensor_cycle = 0
                    sensors = self._get_all_sensors()

            # Check for TLP / auto-cpufreq conflict (cached, every 10 cycles ~25s)
            self._conflict_counter += 1
            if self._conflict_counter >= 10:
                self._conflict_counter = 0
                self._conflict_cache = None
                for tool in ("tlp", "auto-cpufreq"):
                    try:
                        res = subprocess.run(["systemctl", "is-active", f"{tool}.service"],
                                             capture_output=True, text=True, timeout=2)
                        if res.stdout.strip() == "active":
                            self._conflict_cache = tool
                            break
                    except Exception:
                        pass

            with self.lock:
                self.data["cpu_temp"] = c
                self.data["gpu_temp"] = g
                self.data["fan_info"] = fi
                self.data["power_profile"] = pp
                self.data["all_sensors"] = sensors
                self.data["power_conflict"] = self._conflict_cache
                
            time.sleep(2.5)

    def _get_all_sensors(self):
        sensors = []
        try:
            for d in sorted(os.listdir("/sys/class/hwmon")):
                path = os.path.join("/sys/class/hwmon", d)
                name = "unknown"
                try:
                    with open(os.path.join(path, "name")) as f:
                        name = f.read().strip()
                except Exception: continue

                for tf in sorted(glob.glob(os.path.join(path, "temp*_input"))):
                    try:
                        with open(tf) as f:
                            temp = int(f.read().strip()) / 1000
                        label_file = tf.replace("_input", "_label")
                        try:
                            with open(label_file) as f:
                                label = f.read().strip()
                        except Exception:
                            label = os.path.basename(tf).replace("_input", "")
                        
                        # Fix up messy kernel sensor labels for the UI
                        if label.lower() == "package id 0":
                            label = "CPU Package"
                        elif label.lower().startswith("core "):
                            try:
                                core_num = int(label.split()[1])
                                label = f"Core {core_num + 1}"
                            except ValueError:
                                pass
                        elif label.lower() == "tctl":
                            label = "CPU (tctl)"
                        elif label.lower() == "tdie":
                            label = "CPU (tdie)"
                            
                        sensors.append({"driver": name, "label": label, "temp": temp})
                    except Exception: pass
        except Exception: pass
        return sensors

    def get_data(self):
        with self.lock:
            return self.data.copy()

    def stop(self):
        self.running = False
        self._active_event.set()


class FanPage(Gtk.Box):
    def __init__(self, service=None, on_profile_change=None):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(0)
        self.service = service          # fan service proxy
        self._platform_svc = None       # platform service proxy
        self._power_svc = None          # power service proxy
        self.on_profile_change = on_profile_change
        self.fan_mode = "standard" # Default to standard, will sync later
        self._curve_timer = None
        self._sensors_expanded = False
        self.temp_unit = "C"  # "C" or "F"
        
        # Stability vars
        self.temp_history = []
        self.last_applied_rpm = {} # {fan_idx: rpm}
        
        self._block_sync = False  # Prevents UI reverting due to stale cached data
        self._profile_card_boxes = []

        self.monitor = SystemMonitor(lambda: {
            "fan": self.service,
            "platform": self._platform_svc,
            "power": self._power_svc,
        })
        self.monitor.start()

        self._build_ui()
        self._timer = None
        self._anim_timer = None
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)
        self._sensor_widgets = {} # Storage for efficient sensor updates

    def _start_timers(self):
        if self._timer is None:
            self._timer = GLib.timeout_add(1500, self._refresh)
        if self._anim_timer is None:
            self._anim_timer = GLib.timeout_add(40, self._anim_tick)

    def _stop_timers(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = None
        if self._anim_timer:
            GLib.source_remove(self._anim_timer)
            self._anim_timer = None

    def _on_map(self, *_args):
        self.monitor.set_active(True)
        self.monitor.set_collect_sensors(self._sensors_expanded)
        self._start_timers()
        self._refresh()

    def _on_unmap(self, *_args):
        self.monitor.set_collect_sensors(False)
        self.monitor.set_active(False)
        self._stop_timers()

    def _anim_tick(self):
        if not self.get_mapped():
            return True
        self.fan1_gauge.tick_rotation()
        self.fan2_gauge.tick_rotation()
        return True

    def set_service(self, service):
        self.service = service

    def set_platform_service(self, service):
        self._platform_svc = service

    def set_power_service(self, service):
        self._power_svc = service

    def set_temp_unit(self, unit):
        self.temp_unit = unit

    def _format_temp(self, celsius):
        """Format temperature value for display in the user's preferred unit."""
        if self.temp_unit == "F":
            return f"{int(celsius * 9 / 5 + 32)}°F"
        return f"{int(celsius)}°C"

    def set_dark(self, is_dark):
        self.fan1_gauge.set_dark(is_dark)
        self.fan2_gauge.set_dark(is_dark)
        self.fan1_spark.set_dark(is_dark)
        self.fan2_spark.set_dark(is_dark)

    def _fetch_hw_power_limits_async(self):
        def _bg():
            cpu_w, gpu_w = 0, 0
            
            try:
                rapl = "/sys/class/powercap/intel-rapl/intel-rapl:0/constraint_1_power_limit_uw" # PL2 is usually Max
                if not os.path.exists(rapl):
                    rapl = "/sys/class/powercap/intel-rapl/intel-rapl:0/constraint_0_power_limit_uw"
                if os.path.exists(rapl):
                    with open(rapl) as f:
                        val = int(f.read().strip())
                        if val > 0:
                            cpu_w = val // 1000000
            except Exception:
                pass
                
            try:
                import subprocess
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=power.max_limit", "--format=csv,noheader,nounits"],
                    stderr=subprocess.DEVNULL, timeout=2.0
                ).decode().strip()
                if out:
                    try:
                        gpu_w = int(float(out))
                    except: pass
            except Exception:
                pass
                
            GLib.idle_add(self._update_hw_limit_tooltip, cpu_w, gpu_w)
            
        import threading
        threading.Thread(target=_bg, daemon=True).start()

    def _update_hw_limit_tooltip(self, cpu_w, gpu_w):
        if not (cpu_w or gpu_w): return
        limit_str = f" (CPU: ~{cpu_w}W, GPU: ~{gpu_w}W limitine kadar)"
        if "performance" in getattr(self, "profile_buttons", {}):
            base_tooltip = T("performance_tooltip")
            self.profile_buttons["performance"].set_tooltip_text(f"{base_tooltip}{limit_str}")

    def _build_ui(self):
        scroll = SmoothScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(22)
        content.set_margin_start(28)
        content.set_margin_end(28)
        content.set_margin_bottom(22)
        self._content_box = content

        title = Gtk.Label(label=T("fan_control"), xalign=0)
        title.add_css_class("page-title")
        content.append(title)

        # ═══ 1. SYSTEM STATUS SECTION (NO CARD) ═══
        fan_temp_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        fan_temp_card.set_margin_start(2)
        fan_temp_card.set_margin_end(2)
        fan_temp_card.set_margin_top(2)
        fan_temp_card.set_margin_bottom(4)

        ft_header = Gtk.Box(spacing=8)
        ft_header.append(Gtk.Image.new_from_icon_name("weather-tornado-symbolic"))
        ft_header.append(Gtk.Label(label=T("system_status"), css_classes=["section-title"]))
        fan_temp_card.append(ft_header)


        

        h_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 14)
        h_box.set_homogeneous(True)
        h_box.set_margin_top(18)
        h_box.set_margin_bottom(18)
        self._fan_metrics_row = h_box

        # Fan 1 (CPU)
        f1_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)
        f1_box.set_halign(Gtk.Align.CENTER)
        f1_box.append(Gtk.Label(label="CPU Fan", css_classes=["fan-title"]))
        self.fan1_gauge = RotatingFanWidget(132)
        f1_box.append(self.fan1_gauge)
        self.fan1_rpm_lbl = Gtk.Label(label="0 RPM", css_classes=["stat-rpm"])
        f1_box.append(self.fan1_rpm_lbl)
        self.fan1_spark = FanSparkline((0.3, 0.6, 1.0))
        self.fan1_spark.set_size_request(96, 20)
        f1_box.append(self.fan1_spark)
        h_box.append(f1_box)

        # Temps (Central Circle)
        temp_center_container = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        temp_center_container.set_halign(Gtk.Align.CENTER)
        temp_center_container.set_valign(Gtk.Align.CENTER)
        
        temp_circle = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)
        temp_circle.set_halign(Gtk.Align.CENTER)
        temp_circle.set_valign(Gtk.Align.CENTER)
        temp_circle.add_css_class("temp-circle")
        temp_circle.set_size_request(118, 118)
        self._temp_circle = temp_circle
        
        cpu_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        cpu_box.append(Gtk.Label(label="CPU", css_classes=["dim-label"]))
        self.cpu_label = Gtk.Label(label="--°C", css_classes=["title-3"])
        cpu_box.append(self.cpu_label)
        temp_circle.append(cpu_box)

        sep = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
        sep.set_size_request(38, -1)
        temp_circle.append(sep)

        gpu_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        gpu_box.append(Gtk.Label(label="GPU", css_classes=["dim-label"]))
        self.gpu_label = Gtk.Label(label="--°C", css_classes=["title-4"])
        gpu_box.append(self.gpu_label)
        temp_circle.append(gpu_box)
        
        temp_center_container.append(temp_circle)
        h_box.append(temp_center_container)

        # Fan 2 (GPU)
        f2_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)
        f2_box.set_halign(Gtk.Align.CENTER)
        f2_box.append(Gtk.Label(label="GPU Fan", css_classes=["fan-title"]))
        self.fan2_gauge = RotatingFanWidget(132)
        f2_box.append(self.fan2_gauge)
        self.fan2_rpm_lbl = Gtk.Label(label="0 RPM", css_classes=["stat-rpm"])
        f2_box.append(self.fan2_rpm_lbl)
        self.fan2_spark = FanSparkline((0.9, 0.4, 0.1))
        self.fan2_spark.set_size_request(96, 20)
        f2_box.append(self.fan2_spark)
        h_box.append(f2_box)

        fan_temp_card.append(h_box)

        self.fan_warning = Gtk.Label(label=T("fan_disabled"), css_classes=["warning-text"])
        self.fan_warning.set_visible(False)
        fan_temp_card.append(self.fan_warning)

        # Sensor expander as a Pill
        self.sensor_pill = Gtk.Frame()
        self.sensor_pill.add_css_class("pill-frame")
        self.sensor_pill.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        
        pill_content = Gtk.Box(spacing=8)
        pill_content.set_margin_top(6)
        pill_content.set_margin_bottom(6)
        pill_content.set_margin_start(10)
        pill_content.set_margin_end(10)
        
        self._expander_arrow = Gtk.Image.new_from_icon_name("pan-down-symbolic")
        self._expander_arrow.set_pixel_size(14)
        pill_content.append(self._expander_arrow)
        
        self._sensor_label = Gtk.Label(label=T("all_sensors"), css_classes=["stat-lbl"])
        pill_content.append(self._sensor_label)
        
        self.sensor_pill.set_child(pill_content)
        
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", lambda *args: self._toggle_sensors(None))
        self.sensor_pill.add_controller(gesture)
        
        fan_temp_card.append(self.sensor_pill)

        self.sensor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.sensor_box.set_valign(Gtk.Align.START)
        self.sensor_box.set_hexpand(True)
        self.sensor_box.set_visible(False)
        self.sensor_box.set_margin_top(6)
        fan_temp_card.append(self.sensor_box)
        content.append(fan_temp_card)

        # ═══ 2. FAN CONTROL (PROFILE CARDS + COMPACT MODE) ═══
        control_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=9)
        control_panel.add_css_class("fan-cyber-panel")

        power_lbl = Gtk.Label(label=T("power_profile"), xalign=0)
        power_lbl.add_css_class("fan-control-label")
        control_panel.append(power_lbl)

        self.profile_strip = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        self.profile_strip.add_css_class("power-profile-grid")
        self.profile_group = None
        profiles = [
            ("power-saver", T("saver"), T("saver_tooltip")),
            ("balanced", T("balanced"), T("balanced_tooltip")),
            ("performance", T("performance"), T("performance_tooltip")),
        ]
        self.profile_buttons = {}
        for pid, title, desc in profiles:
            btn = Gtk.ToggleButton()
            btn.add_css_class("power-profile-card")
            btn.set_tooltip_text(desc)

            card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            card_box.set_margin_top(8)
            card_box.set_margin_bottom(8)
            card_box.set_margin_start(10)
            card_box.set_margin_end(10)
            self._profile_card_boxes.append(card_box)

            title_lbl = Gtk.Label(label=title, xalign=0)
            title_lbl.add_css_class("power-profile-title")
            card_box.append(title_lbl)

            desc_lbl = Gtk.Label(label=desc, xalign=0, wrap=True)
            desc_lbl.add_css_class("power-profile-desc")
            desc_lbl.set_max_width_chars(24)
            card_box.append(desc_lbl)

            btn.set_child(card_box)
            btn.set_size_request(152, 88)
            if self.profile_group:
                btn.set_group(self.profile_group)
            else:
                self.profile_group = btn
            btn.connect("toggled", lambda w, p=pid: self._set_profile(p) if w.get_active() else None)
            self.profile_strip.append(btn)
            self.profile_buttons[pid] = btn
        control_panel.append(self.profile_strip)

        fan_lbl = Gtk.Label(label=T("fan_mode"), xalign=0)
        fan_lbl.add_css_class("fan-control-label")
        fan_lbl.set_margin_top(2)
        control_panel.append(fan_lbl)

        self.mode_selector = Gtk.Box(spacing=0, halign=Gtk.Align.CENTER)
        self.mode_selector.add_css_class("fan-mode-compact-strip")
        self.fan_mode_group = None
        modes = [("standard", T("standard")), ("max", T("max")), ("custom", T("custom"))]
        self.fan_mode_buttons = {}
        for mid, label in modes:
            btn = Gtk.ToggleButton(label=label)
            btn.add_css_class("fan-mode-compact-btn")
            btn.set_size_request(106, 30)
            if self.fan_mode_group:
                btn.set_group(self.fan_mode_group)
            else:
                self.fan_mode_group = btn
            btn.connect("toggled", lambda w, m=mid: self._on_fan_mode(m) if w.get_active() else None)
            self.mode_selector.append(btn)
            self.fan_mode_buttons[mid] = btn
        control_panel.append(self.mode_selector)

        status_row = Gtk.Box(spacing=10)
        self.pp_status = Gtk.Label(label=T("checking"), xalign=0)
        self.pp_status.add_css_class("fan-control-status")
        self.pp_status.set_hexpand(True)
        self.pp_status.set_halign(Gtk.Align.START)
        status_row.append(self.pp_status)

        self.fan_mode_status = Gtk.Label(label="", xalign=1)
        self.fan_mode_status.add_css_class("fan-control-status")
        self.fan_mode_status.set_hexpand(True)
        self.fan_mode_status.set_halign(Gtk.Align.END)
        status_row.append(self.fan_mode_status)
        control_panel.append(status_row)

        # TLP / auto-cpufreq conflict warning
        self._pp_conflict_lbl = Gtk.Label(label="", use_markup=True, xalign=0, wrap=True)
        self._pp_conflict_lbl.add_css_class("warning-text")
        self._pp_conflict_lbl.set_visible(False)
        control_panel.append(self._pp_conflict_lbl)

        content.append(control_panel)

        # ═══ 3. FAN CURVE ═══
        self.curve_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.curve_card.add_css_class("card")
        self.curve_card.set_visible(False)

        curve_header = Gtk.Box(spacing=10)
        curve_header.append(Gtk.Image.new_from_icon_name("document-edit-symbolic"))
        curve_header.append(Gtk.Label(label=T("fan_curve"), css_classes=["section-title"]))
        self.curve_card.append(curve_header)

        curve_desc = Gtk.Label(label=T("curve_desc"), css_classes=["stat-lbl"], xalign=0, wrap=True)
        self.curve_card.append(curve_desc)

        self.fan_curve = FanCurveWidget()
        self.fan_curve.on_curve_changed = self._on_curve_changed
        self.curve_card.append(self.fan_curve)
        content.append(self.curve_card)

        scroll.set_child(content)
        self.append(scroll)
        
        # Default points backup
        self.default_points = [(48, 0), (58, 35), (70, 60), (78, 72), (85, 100)]
        self.custom_points = list(self.default_points)
        
        # Initial mode set (will be updated by daemon sync)
        self.set_fan_mode_ui("standard")
        self._apply_profile_theme("balanced")
        
        # Fetch power limits async to populate profile tooltips
        self._fetch_hw_power_limits_async()
        self.set_ui_scale("normal")

    def set_ui_scale(self, bucket, _width=0, _height=0):
        content = getattr(self, "_content_box", None)
        if content is not None:
            if bucket == "compact":
                content.set_spacing(12)
                content.set_margin_top(12)
                content.set_margin_start(14)
                content.set_margin_end(14)
                content.set_margin_bottom(12)
            elif bucket == "spacious":
                content.set_spacing(18)
                content.set_margin_top(26)
                content.set_margin_start(34)
                content.set_margin_end(34)
                content.set_margin_bottom(26)
            else:
                content.set_spacing(16)
                content.set_margin_top(22)
                content.set_margin_start(28)
                content.set_margin_end(28)
                content.set_margin_bottom(22)

        row = getattr(self, "_fan_metrics_row", None)
        if row is not None:
            row.set_spacing(10 if bucket == "compact" else 18 if bucket == "spacious" else 14)
            row.set_margin_top(12 if bucket == "compact" else 22 if bucket == "spacious" else 18)
            row.set_margin_bottom(12 if bucket == "compact" else 22 if bucket == "spacious" else 18)

        gauge_size = 114 if bucket == "compact" else 150 if bucket == "spacious" else 132
        for gauge in (getattr(self, "fan1_gauge", None), getattr(self, "fan2_gauge", None)):
            if gauge is not None and hasattr(gauge, "set_diameter"):
                gauge.set_diameter(gauge_size)

        spark_w = 82 if bucket == "compact" else 118 if bucket == "spacious" else 96
        spark_h = 18 if bucket == "compact" else 24 if bucket == "spacious" else 20
        for spark in (getattr(self, "fan1_spark", None), getattr(self, "fan2_spark", None)):
            if spark is not None and hasattr(spark, "set_chart_size"):
                spark.set_chart_size(spark_w, spark_h)

        temp_circle = getattr(self, "_temp_circle", None)
        if temp_circle is not None:
            side = 98 if bucket == "compact" else 132 if bucket == "spacious" else 118
            temp_circle.set_size_request(side, side)

        profile_btn_w = 134 if bucket == "compact" else 168 if bucket == "spacious" else 152
        profile_btn_h = 78 if bucket == "compact" else 98 if bucket == "spacious" else 88
        for btn in getattr(self, "profile_buttons", {}).values():
            btn.set_size_request(profile_btn_w, profile_btn_h)

        mode_btn_w = 92 if bucket == "compact" else 118 if bucket == "spacious" else 106
        mode_btn_h = 28 if bucket == "compact" else 34 if bucket == "spacious" else 30
        for btn in getattr(self, "fan_mode_buttons", {}).values():
            btn.set_size_request(mode_btn_w, mode_btn_h)

    def _unblock_sync(self):
        self._block_sync = False
        return False

    def set_fan_mode_ui(self, mode):
        self.fan_mode = mode
        if mode in getattr(self, "fan_mode_buttons", {}):
            btn = self.fan_mode_buttons[mode]
            if not btn.get_active():
                prev = self._block_sync
                self._block_sync = True
                btn.set_active(True)
                self._block_sync = prev

    def _apply_profile_theme(self, profile):
        mode_map = {
            "power-saver": "eco",
            "balanced": "balanced",
            "performance": "performance",
        }
        theme = mode_map.get(profile, "balanced")

        for cls in ("fan-theme-eco", "fan-theme-balanced", "fan-theme-performance"):
            self.remove_css_class(cls)
        self.add_css_class(f"fan-theme-{theme}")

        self.fan1_gauge.set_theme(theme)
        self.fan2_gauge.set_theme(theme)

        if theme == "eco":
            self.fan1_spark.color = (0.35, 0.88, 0.52)
            self.fan2_spark.color = (0.22, 0.72, 0.36)
        elif theme == "performance":
            self.fan1_spark.color = (0.98, 0.44, 0.33)
            self.fan2_spark.color = (0.84, 0.22, 0.18)
        else:
            self.fan1_spark.color = (0.30, 0.60, 1.00)
            self.fan2_spark.color = (0.18, 0.50, 0.95)

        self.fan1_spark.queue_draw()
        self.fan2_spark.queue_draw()

        if callable(self.on_profile_change):
            try:
                self.on_profile_change(profile)
            except Exception:
                pass

    def _toggle_sensors(self, btn):
        self._sensors_expanded = not self._sensors_expanded
        self.monitor.set_collect_sensors(self._sensors_expanded and self.get_mapped())
        self.sensor_box.set_visible(self._sensors_expanded)
        self._expander_arrow.set_from_icon_name(
            "pan-up-symbolic" if self._sensors_expanded else "pan-down-symbolic")

    def _update_sensor_list(self, sensors):
        if not self._sensors_expanded:
            return
            
        if not hasattr(self, "_sensor_grid") or not self._sensor_grid:
            while child := self.sensor_box.get_first_child():
                self.sensor_box.remove(child)
                
            self._sensor_grid = Gtk.Grid(column_spacing=12, row_spacing=10)
            self._sensor_grid.set_column_homogeneous(True)
            self._sensor_grid.set_hexpand(True)
            self.sensor_box.append(self._sensor_grid)
            
            self._cpu_pill = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["sensor-pod"])
            self._cpu_pill.append(self._pill_header("CPU", "processor-symbolic"))
            self._sensor_grid.attach(self._cpu_pill, 0, 0, 1, 1)
            
            self._other_pill = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, css_classes=["sensor-pod"])
            self._other_pill.append(self._pill_header(T("other_sensors"), "view-list-symbolic"))
            self._sensor_grid.attach(self._other_pill, 1, 0, 1, 1)

        # Categorize
        for s in sensors:
            key = f"{s['driver']}_{s['label']}"
            val_str = f"{int(s['temp'])}°"
            
            if key in self._sensor_widgets:
                lbl, bar = self._sensor_widgets[key]
                lbl.set_label(val_str)
                # bar is a Box, we can update its width to show intensity
                bar.set_size_request(int(min(s['temp'], 70)), 2) 
            else:
                # Create refined sensor row
                row = Gtk.Box(spacing=8)
                row.add_css_class("sensor-card-item")
                
                name_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
                lbl_name = Gtk.Label(label=s["label"], xalign=0, css_classes=["stat-lbl"])
                lbl_name.set_ellipsize(3)
                name_box.append(lbl_name)
                
                # Tiny progress-like bar under the name
                bar = Gtk.Box(height_request=2, hexpand=False, halign=Gtk.Align.START)
                bar.add_css_class("sensor-bar")
                bar.set_size_request(int(min(s['temp'], 70)), 2)
                name_box.append(bar)
                
                row.append(name_box)
                
                temp_lbl = Gtk.Label(label=val_str, xalign=1, css_classes=["sensor-temp-val"])
                row.append(temp_lbl)
                
                self._sensor_widgets[key] = (temp_lbl, bar)
                
                # Determine pill
                lbl_low = s["label"].lower()
                dr_low = s["driver"].lower()
                if any(x in lbl_low for x in ("core", "cpu", "tctl", "package id")):
                    self._cpu_pill.append(row)
                else:
                    self._other_pill.append(row)

    def _pill_header(self, title, icon):
        box = Gtk.Box(spacing=6)
        box.set_margin_bottom(6)
        img = Gtk.Image.new_from_icon_name(icon)
        img.set_pixel_size(14)
        img.set_opacity(0.65)
        box.append(img)
        lbl = Gtk.Label(label=title, xalign=0, css_classes=["section-title"])
        box.append(lbl)
        return box

    def _set_profile(self, profile):
        if self._block_sync:
            return  # Skip triggering if we are programmatically updating UI
        self._apply_profile_theme(profile)
        self._block_sync = True
        GLib.timeout_add(1500, self._unblock_sync)
        if self._power_svc:
            svc = self._power_svc
            def _bg():
                try:
                    _dbus_call(svc.SetPowerProfile, profile)
                    GLib.idle_add(lambda: self.pp_status.set_label(f"{T('active_profile')}: {profile}"))
                except Exception as e:
                    GLib.idle_add(lambda: self.pp_status.set_label(f"{T('error')}: {e}"))
            threading.Thread(target=_bg, daemon=True).start()

    def _on_fan_mode(self, mode):
        self.fan_mode = mode

        # Standard = EC auto control (pwm1_enable=2, no RPM commands)
        # Custom   = software-controlled fan curve (pwm1_enable=1)
        # Max      = hardware max speed (pwm1_enable=0)

        if mode == "standard":
            daemon_mode = "auto"
        elif mode == "custom":
            daemon_mode = "custom"
        else:
            daemon_mode = "max"

        # Curve visibility (only for custom)
        self.curve_card.set_visible(mode == "custom")
        self.fan_curve.set_interactive(mode == "custom")

        if mode == "custom":
            self.fan_curve.set_points(self.custom_points)

        # Clear applied RPM cache when switching modes
        self.last_applied_rpm = {}

        if self._block_sync:
            return # if programmatic UI update, do nothing
        self._block_sync = True
        block_ms = CUSTOM_MODE_SYNC_DELAY_MS if mode == "custom" else DEFAULT_MODE_SYNC_DELAY_MS
        GLib.timeout_add(block_ms, self._unblock_sync)

        if self.service:
            svc = self.service
            labels = {"standard": T("standard"), "max": T("max"), "custom": T("custom")}
            label_text = labels.get(mode, mode)
            def _bg():
                try:
                    _dbus_call(svc.SetFanMode, daemon_mode)
                    GLib.idle_add(lambda: self.fan_mode_status.set_label(f"{T('mode')}: {label_text}"))
                except Exception as e:
                    GLib.idle_add(lambda: self.fan_mode_status.set_label(f"{T('error')}: {e}"))
            threading.Thread(target=_bg, daemon=True).start()

        # Only apply fan curve in custom mode (standard delegates to EC)
        if mode == "custom":
            self._apply_fan_curve()

    def _on_curve_changed(self, points):
        if self.fan_mode == "custom":
            self.custom_points = points
            if self._curve_timer:
                GLib.source_remove(self._curve_timer)
            self._curve_timer = GLib.timeout_add(200, self._apply_fan_curve_debounced)

    def _apply_fan_curve_debounced(self):
        self._apply_fan_curve()
        self._curve_timer = None
        return False

    def _apply_fan_curve(self):
        """Apply fan curve — only used in 'custom' mode."""
        if self.fan_mode != "custom":
            return

        if not self.temp_history:
            return

        avg_temp = sum(self.temp_history) / len(self.temp_history)
        fan_pct = self.fan_curve.get_fan_pct_for_temp(avg_temp)

        if self.service:
            try:
                data = self.monitor.get_data()
                info = data.get("fan_info", {})
                fans = info.get("fans", {})

                for fn, fd in fans.items():
                    max_rpm = fd.get("max", 5800)
                    if max_rpm <= 0:
                        max_rpm = 5800

                    target_rpm = int(max_rpm * fan_pct / 100)

                    # Hysteresis: skip if RPM change < 300
                    last = self.last_applied_rpm.get(str(fn), -1)
                    if last >= 0 and abs(target_rpm - last) < 300:
                        continue

                    self.last_applied_rpm[str(fn)] = target_rpm
                    
                    # Apply asynchronously to prevent UI freeze on slow EC/WMI responses
                    def _apply_async(fidx, rpm):
                        try: self.service.SetFanTarget(fidx, rpm)
                        except: pass
                    threading.Thread(target=_apply_async, args=(int(str(fn)), target_rpm), daemon=True).start()
            except Exception as e:
                print(f"Fan control error: {e}")

    def _refresh(self):
        if not self.get_mapped():
            return True
            
        data = self.monitor.get_data()
        cpu_t = data.get("cpu_temp", 0)
        gpu_t = data.get("gpu_temp", 0)
        fan_info = data.get("fan_info", {})
        power_profile = data.get("power_profile", {})
        
        # Update history
        self.temp_history.append(cpu_t)
        if len(self.temp_history) > 5: # Keep last 5 seconds
            self.temp_history.pop(0)
            
        # Draw current temp marker on curve
        self.fan_curve.set_current_temp(cpu_t)
        

        
        self.cpu_label.set_label(self._format_temp(cpu_t))
        self.gpu_label.set_label(self._format_temp(gpu_t))

        if self.fan_mode == "custom":
            self._apply_fan_curve()
            
        # Sync Power Profile UI
        active_profile = power_profile.get("active", "")
        if active_profile and active_profile in self.profile_buttons and not self._block_sync:
            btn = self.profile_buttons[active_profile]
            if not btn.get_active():
                # Temporarily block sync so we don't send the command back to daemon
                self._block_sync = True
                btn.set_active(True)
                self._block_sync = False
        
        if active_profile:
            self.pp_status.set_label(f"{T('active_profile')}: {active_profile}")
            self._apply_profile_theme(active_profile)

        # Handle TLP / auto-cpufreq conflict
        conflict = data.get("power_conflict")
        if conflict:
            # TLP doesn't strictly block profile switching, but auto-cpufreq does.
            self.profile_strip.set_sensitive(conflict != "tlp")
            self._pp_conflict_lbl.set_label(
                f"<span color='#57e389'>{T('power_managed_by').format(tool=conflict.upper())}</span>")
            self._pp_conflict_lbl.set_visible(True)
            self.pp_status.set_label(f"{T('active_profile')}: {conflict.upper()}")
        else:
            self.profile_strip.set_sensitive(True)
            self._pp_conflict_lbl.set_visible(False)

        # Sync Fan Data
        available = fan_info.get("available", False)
        if available:
            self.fan_warning.set_visible(False)
            daemon_mode = fan_info.get("mode", "auto")
            
            # Map daemon modes to UI modes
            if not self._block_sync:
                if daemon_mode == "auto" and self.fan_mode != "standard":
                    self._block_sync = True; self.set_fan_mode_ui("standard"); self._block_sync = False
                elif daemon_mode == "max" and self.fan_mode != "max":
                    self._block_sync = True; self.set_fan_mode_ui("max"); self._block_sync = False
                elif daemon_mode == "custom" and self.fan_mode != "custom":
                    self._block_sync = True; self.set_fan_mode_ui("custom"); self._block_sync = False
            
            # Update gauges
            fans = fan_info.get("fans", {})
            fan_keys = sorted(fans.keys(), key=lambda x: int(x))
            gauges = [self.fan1_gauge, self.fan2_gauge]
            rpmlbls = [self.fan1_rpm_lbl, self.fan2_rpm_lbl]
            sparks  = [self.fan1_spark, self.fan2_spark]

            for i, fk in enumerate(fan_keys[:2]):
                rpm = fans[fk].get("current", 0)
                max_rpm = fans[fk].get("max", 5800)
                pct = min(rpm / max_rpm * 100, 100) if max_rpm > 0 else 0
                gauges[i].set_val(pct, f"{rpm}")
                rpmlbls[i].set_label(f"{rpm} RPM")
                sparks[i].add_value(rpm)
        else:
            self.fan_warning.set_visible(True)

        if self._sensors_expanded:
            self._update_sensor_list(data.get("all_sensors", []))
            
        return True

    def cleanup(self):
        self._stop_timers()
        self.monitor.stop()
