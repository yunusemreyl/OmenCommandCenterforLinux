#!/usr/bin/env python3
"""Keyboard & Shortcuts Page — tailored for OMEN/Victus hotkeys."""
import os, platform, subprocess, json
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

def T(k):
    from i18n import T as _T
    return _T(k)

def _detect_model_type():
    for dmi_file in ("/sys/devices/virtual/dmi/id/product_name",
                     "/sys/devices/virtual/dmi/id/product_family"):
        try:
            if os.path.exists(dmi_file):
                with open(dmi_file) as f:
                    name = f.read().strip().lower()
                    if "victus" in name: return "victus"
                    if "omen" in name: return "omen"
        except Exception: pass
    return "omen"

class KeyboardPage(Gtk.Box):
    def __init__(self, service=None):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_spacing(0)
        self.service = service
        
        self.model_type = _detect_model_type()
        self.branding = "OMEN" if self.model_type == "omen" else "Victus"
        
        # Resolve logo path
        self.logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "images", "omenlogo.png")
        if not os.path.exists(self.logo_path):
            self.logo_path = "/usr/share/hp-manager/images/omenlogo.png"
            
        self._build_ui()

    def _build_ui(self):
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        root.set_margin_top(24)
        root.set_margin_start(32)
        root.set_margin_end(32)
        root.set_margin_bottom(24)
        scroll.set_child(root)
        self.append(scroll)

        # Header with Logo
        header = Gtk.Box(spacing=15, valign=Gtk.Align.CENTER)
        if os.path.exists(self.logo_path):
            from gi.repository import GdkPixbuf, Gdk
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.logo_path, 48, 48, True)
            img = Gtk.Image.new_from_paintable(Gdk.Texture.new_for_pixbuf(pix))
            header.append(img)
        
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title = Gtk.Label(label=T("keyboard_shortcuts"), xalign=0, css_classes=["title-1"])
        title_box.append(title)
        desc = Gtk.Label(label=T("shortcuts_desc"), xalign=0, css_classes=["dim-label"])
        title_box.append(desc)
        header.append(title_box)
        root.append(header)

        root.append(Gtk.Separator())

        # ── SPECIAL KEYS ──
        keys_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        keys_card.add_css_class("card")
        keys_card.append(Gtk.Label(label=T("special_keys"), xalign=0, css_classes=["heading"]))
        
        # Omen/Victus Key
        omen_row = self._make_shortcut_row(T("omen_key"), 
                                        "Opens OMEN Command Center for Linux.", 
                                        self.logo_path)
        keys_card.append(omen_row)

        if self.model_type == "victus":
            calc_row = self._make_shortcut_row(T("calculator"), 
                                            "Launches Calculator application.", 
                                            "accessories-calculator-symbolic")
            keys_card.append(calc_row)
        
        root.append(keys_card)

        # ── KEYBOARD FIXES (The main meat) ──
        fix_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        fix_card.add_css_class("card")
        
        fix_header = Gtk.Box(spacing=10)
        fix_header.append(Gtk.Image.new_from_icon_name("system-run-symbolic"))
        fix_header.append(Gtk.Label(label=T("driver_status"), xalign=0, css_classes=["heading"]))
        fix_card.append(fix_header)

        # PrtSc Fix
        prtsc_box = Gtk.Box(spacing=15)
        prtsc_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True)
        prtsc_info.append(Gtk.Label(label=T("prt_sc_fix"), xalign=0, css_classes=["title-4"]))
        prtsc_info.append(Gtk.Label(label=T("prt_sc_desc"), xalign=0, css_classes=["dim-label"], wrap=True))
        prtsc_box.append(prtsc_info)
        self.prtsc_sw = Gtk.Switch(valign=Gtk.Align.CENTER)
        prtsc_box.append(self.prtsc_sw)
        fix_card.append(prtsc_box)

        fix_card.append(Gtk.Separator())

        # F1 Fix
        f1_box = Gtk.Box(spacing=15)
        f1_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True)
        f1_info.append(Gtk.Label(label=T("f1_fix"), xalign=0, css_classes=["title-4"]))
        f1_info.append(Gtk.Label(label=T("f1_desc"), xalign=0, css_classes=["dim-label"], wrap=True))
        f1_box.append(f1_info)
        self.f1_sw = Gtk.Switch(valign=Gtk.Align.CENTER)
        f1_box.append(self.f1_sw)
        fix_card.append(f1_box)

        root.append(fix_card)

        # Footer Action
        footer = Gtk.Box(spacing=12, halign=Gtk.Align.END)
        self.apply_btn = Gtk.Button(label=T("apply_shortcuts"))
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.connect("clicked", self._on_apply)
        footer.append(self.apply_btn)
        root.append(footer)

        self._sync_state()

    def _make_shortcut_row(self, title, desc, icon_name):
        row = Gtk.Box(spacing=15)
        if icon_name.startswith("/") or icon_name.endswith(".png"):
            if os.path.exists(icon_name):
                from gi.repository import GdkPixbuf, Gdk
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_name, 24, 24, True)
                icon = Gtk.Image.new_from_paintable(Gdk.Texture.new_for_pixbuf(pix))
            else:
                icon = Gtk.Image.new_from_icon_name("image-missing")
        else:
            icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(24)
        row.append(icon)
        
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info.append(Gtk.Label(label=title, xalign=0))
        info.append(Gtk.Label(label=desc, xalign=0, css_classes=["stat-lbl"]))
        row.append(info)
        return row

    def _sync_state(self):
        if not self.service: return
        try:
            st = json.loads(self.service.GetState())
            self.prtsc_sw.set_active(st.get("prtsc_fix", False))
            self.f1_sw.set_active(st.get("f1_fix", False))
        except Exception: pass

    def _on_apply(self, btn):
        if not self.service: return
        p = self.prtsc_sw.get_active()
        f = self.f1_sw.get_active()
        
        try:
            self.service.SetKeyboardFixes(p, f)
            
            # Show success toast or info
            toast = Gtk.MessageDialog(
                transient_for=self.get_root(),
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=T("hwdb_applied")
            )
            toast.connect("response", lambda r, id: r.destroy())
            toast.present()
        except Exception as e:
            print(f"Apply shortcuts failed: {e}")

