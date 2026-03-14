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
        self.set_spacing(20)
        self.service = service
        self.set_margin_top(30)
        self.set_margin_start(40)
        self.set_margin_end(40)
        self.set_margin_bottom(30)

        self.model_type = _detect_model_type()
        self.branding = "OMEN" if self.model_type == "omen" else "Victus"
        self._build_ui()

    def _build_ui(self):
        title = Gtk.Label(label=T("keyboard_shortcuts"), xalign=0)
        title.add_css_class("page-title")
        self.append(title)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)

        # ── Gaming Key Lock (Windows Lock) ──
        lock_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        lock_card.add_css_class("card")
        
        lock_row = Gtk.Box(spacing=15)
        lock_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True)
        lock_info.append(Gtk.Label(label=T("win_lock"), xalign=0, css_classes=["section-title"]))
        lock_info.append(Gtk.Label(label="Toggles physical Windows Key lock (Gaming Key).", xalign=0, css_classes=["stat-lbl"]))
        lock_row.append(lock_info)

        self.win_lock_sw = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.win_lock_sw.connect("state-set", self._on_win_lock)
        lock_row.append(self.win_lock_sw)
        lock_card.append(lock_row)
        
        # Win Lock Hint
        lock_card.append(Gtk.Label(
            label=f"This corresponds to the F10 lock key icon on your {self.branding} laptop.",
            xalign=0, css_classes=["stat-lbl"]
        ))
        content.append(lock_card)

        # ── Special Keys ──
        keys_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        keys_card.add_css_class("card")
        keys_card.append(Gtk.Label(label=T("special_keys"), xalign=0, css_classes=["section-title"]))

        # Dynamic Row based on model
        key_name = T("omen_key") if self.model_type == "omen" else T("victus_key")
        key_desc = f"Opens the {self.branding} Manager application."
        key_row = self._make_shortcut_row(key_name, key_desc, "hplogolight")
        keys_card.append(key_row)

        if self.model_type == "victus":
            calc_row = self._make_shortcut_row(T("calc_key"), "Launches Calculator application.", "accessories-calculator-symbolic")
            keys_card.append(calc_row)

        content.append(keys_card)

        # ── Fixes ──
        fix_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        fix_card.add_css_class("card")
        fix_card.append(Gtk.Label(label="KEYBOARD FIXES", xalign=0, css_classes=["section-title"]))

        # PrtSc Fix
        prtsc_row = Gtk.Box(spacing=15)
        prtsc_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True)
        prtsc_info.append(Gtk.Label(label=T("prt_sc_fix"), xalign=0))
        prtsc_info.append(Gtk.Label(label=T("prt_sc_desc"), xalign=0, css_classes=["stat-lbl"], wrap=True))
        prtsc_row.append(prtsc_info)
        
        self.prtsc_fix_sw = Gtk.Switch(valign=Gtk.Align.CENTER)
        prtsc_row.append(self.prtsc_fix_sw)
        fix_card.append(prtsc_row)

        fix_card.append(Gtk.Separator())

        # F1 Fix
        f1_row = Gtk.Box(spacing=15)
        f1_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True)
        f1_info.append(Gtk.Label(label=T("f1_fix"), xalign=0))
        f1_info.append(Gtk.Label(label=T("f1_desc"), xalign=0, css_classes=["stat-lbl"], wrap=True))
        f1_row.append(f1_info)
        
        self.f1_fix_sw = Gtk.Switch(valign=Gtk.Align.CENTER)
        f1_row.append(self.f1_fix_sw)
        fix_card.append(f1_row)

        content.append(fix_card)

        # Apply Button
        apply_btn = Gtk.Button(label=T("apply_shortcuts"))
        apply_btn.add_css_class("suggested-action")
        apply_btn.set_margin_top(10)
        apply_btn.connect("clicked", self._on_apply_fixes)
        content.append(apply_btn)

        scroll.set_child(content)
        self.append(scroll)
        
        self._sync_state()

    def _make_shortcut_row(self, title, desc, icon_name):
        row = Gtk.Box(spacing=15)
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
            self.win_lock_sw.set_active(st.get("win_lock", False))
            self.prtsc_fix_sw.set_active(st.get("prtsc_fix", False))
            self.f1_fix_sw.set_active(st.get("f1_fix", False))
        except Exception: pass

    def _on_win_lock(self, sw, state):
        if self.service:
            try:
                self.service.SetWinLock(state)
            except Exception: pass
        return False

    def _on_apply_fixes(self, btn):
        if not self.service: return
        
        prtsc = self.prtsc_fix_sw.get_active()
        f1 = self.f1_fix_sw.get_active()
        
        try:
            self.service.SetKeyboardFixes(prtsc, f1)
            
            diag = Gtk.MessageDialog(
                transient_for=self.get_root(),
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text=T("apply_shortcuts"),
                secondary_text="Keyboard fixes have been applied and will persist across reboots."
            )
            diag.connect("response", lambda r, id: r.destroy())
            diag.present()
        except Exception as e:
            print(f"Error applying fixes: {e}")
