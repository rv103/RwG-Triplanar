"""
RwG Tri-planar switch - Substance 3D Painter plugin
-----------------------------------------------------------------------------
Switch the projection of many fill layers at once instead of clicking each one.
Buttons for ALL fill layers or only the SELECTED ones, to Tri-planar or back to
UV. Walks into groups recursively AND into content / mask effects, so a
texture-driven mask (a fill effect in the mask stack) is switched too. It also
toggles a generator's own Tri-planar switch (e.g. `Use_Triplanar`) via the
generator's parameters. (Paint layers etc. are skipped.)

Needs the layer-stack scripting API (Painter 10.0+). Drop this .py into
  Documents\\Adobe\\Adobe Substance 3D Painter\\python\\plugins\\
and Python -> Reload Plugins.

Non-commercial license. (c) RwG.
"""

try:
    from PySide6 import QtWidgets
except Exception:  # older Painter
    from PySide2 import QtWidgets

import substance_painter.ui as spui
import substance_painter.textureset as sptex
import substance_painter.layerstack as spls
import substance_painter.logging as splog

PLUGIN_VERSION = "0.1.0"
_widgets = []


def _children(node):
    """Return a node's child layers (for groups), trying the known accessors."""
    for attr in ("sub_layers", "get_sub_layers", "sub_layer_nodes"):
        f = getattr(node, attr, None)
        if callable(f):
            try:
                return list(f())
            except Exception:
                pass
    return []


def _effects(node):
    """Return a node's content + mask effects (a texture-driven mask is a fill
    effect in the mask stack, so it needs its projection set too)."""
    out = []
    for attr in ("content_effects", "mask_effects"):
        f = getattr(node, attr, None)
        try:
            items = f() if callable(f) else f
        except Exception:
            items = None
        if items:
            try:
                out.extend(list(items))
            except Exception:
                pass
    return out


def _walk(nodes):
    """Yield every node in the tree (depth-first): layers, group children, and
    the fill effects inside content / mask stacks."""
    stack = list(nodes)
    seen = set()
    while stack:
        n = stack.pop()
        key = getattr(n, "uid", None)
        key = key if key is not None else id(n)
        if key in seen:
            continue
        seen.add(key)
        yield n
        stack.extend(_children(n))
        stack.extend(_effects(n))


def _generator_triplanar(node, enable):
    """Toggle a generator's own Tri-planar switch (e.g. `Use_Triplanar`) through
    its SourceSubstance parameters. Returns 1 if a switch was changed."""
    getter = getattr(node, "get_source", None)
    if not callable(getter):
        return 0
    try:
        src = getter()
    except Exception:
        return 0
    if src is None or not hasattr(src, "get_parameters") or not hasattr(src, "set_parameters"):
        return 0
    try:
        params = src.get_parameters()
    except Exception:
        return 0
    if not isinstance(params, dict):
        return 0

    changed = False
    for k, v in list(params.items()):
        kl = str(k).lower()
        if "triplanar" not in kl:
            continue
        # only the on/off ENABLE toggle: an int/bool (not the blending-contrast
        # float), whose name reads like an enable (use/enable/activate) or is just
        # "triplanar" / "use_triplanar".
        is_toggle = isinstance(v, bool) or (isinstance(v, int) and not isinstance(v, bool))
        looks_enable = kl in ("triplanar", "use_triplanar") \
            or any(w in kl for w in ("use", "enable", "activ"))
        if is_toggle and looks_enable:
            params[k] = 1 if enable else 0
            changed = True
    if not changed:
        return 0
    try:
        src.set_parameters(params)
        return 1
    except Exception as e:
        try:
            splog.warning(f"[RwG Tri-planar] generator {node.get_name()}: {e}")
        except Exception:
            pass
        return 0


def _in_mask_stack(node):
    f = getattr(node, "is_in_mask_stack", None)
    try:
        return bool(f()) if callable(f) else bool(f)
    except Exception:
        return False


def _apply(scope, mode_name, cats):
    """Switch the projection of the chosen categories (cats is a subset of
    {'fill', 'maskfill', 'generator'}) in `scope` to `mode_name`."""
    if not cats:
        return "Tick at least one category (Fill / Mask fill / Generator)."
    try:
        stack = sptex.get_active_stack()
    except Exception:
        return "Open a project first."
    if stack is None:
        return "No active texture set."

    mode = getattr(spls.ProjectionMode, mode_name, None)
    if mode is None:
        return f"Projection mode '{mode_name}' not available in this Painter version."
    enable = (mode_name == "Triplanar")

    if scope == "all":
        roots = spls.get_root_layer_nodes(stack)
    else:
        roots = spls.get_selected_nodes(stack)
        if not roots:
            return "Nothing selected - pick some layers first."

    counts = {"fill": 0, "maskfill": 0, "generator": 0}
    failed = 0
    for n in _walk(roots):
        setter = getattr(n, "set_projection_mode", None)
        if callable(setter):
            cat = "maskfill" if _in_mask_stack(n) else "fill"
            if cat not in cats:
                continue
            try:
                setter(mode)
                counts[cat] += 1
            except Exception as e:
                failed += 1
                try:
                    splog.warning(f"[RwG Tri-planar] {n.get_name()}: {e}")
                except Exception:
                    pass
            continue
        if "generator" in cats:
            counts["generator"] += _generator_triplanar(n, enable)

    labels = {"fill": "fill layer", "maskfill": "mask fill", "generator": "generator"}
    parts = [f"{counts[c]} {labels[c]}(s)" for c in ("fill", "maskfill", "generator") if counts[c]]
    msg = f"{mode_name}: " + (", ".join(parts) if parts else "nothing") + " updated"
    if failed:
        msg += f", {failed} failed (see Log)"
    if scope != "all" and not parts:
        msg += " - selection had nothing in those categories."
    return msg


def _build():
    w = QtWidgets.QWidget()
    w.setWindowTitle("RwG Tri-planar")
    v = QtWidgets.QVBoxLayout(w)

    v.addWidget(QtWidgets.QLabel("Categories to switch:"))
    cb_fill = QtWidgets.QCheckBox("Fill layers")
    cb_fill.setToolTip("Content fill layers.")
    cb_mask = QtWidgets.QCheckBox("Mask fills")
    cb_mask.setToolTip("Texture-driven masks (fill effects in a mask stack).")
    cb_gen = QtWidgets.QCheckBox("Generators")
    cb_gen.setToolTip("Generators with a Tri-planar switch (Use_Triplanar etc.).")
    for c in (cb_fill, cb_mask, cb_gen):
        c.setChecked(True)
        v.addWidget(c)

    v.addWidget(_separator())

    status = QtWidgets.QLabel("Tick categories, then apply to All or Selected.")
    status.setWordWrap(True)

    def cats():
        s = set()
        if cb_fill.isChecked():
            s.add("fill")
        if cb_mask.isChecked():
            s.add("maskfill")
        if cb_gen.isChecked():
            s.add("generator")
        return s

    def add(label, scope, mode, tip):
        b = QtWidgets.QPushButton(label)
        b.setToolTip(tip)
        b.clicked.connect(lambda _=False, s=scope, m=mode: status.setText(_apply(s, m, cats())))
        v.addWidget(b)

    add("All → Tri-planar", "all", "Triplanar",
        "Switch the ticked categories to Tri-planar across the whole stack.")
    add("Selected → Tri-planar", "sel", "Triplanar",
        "Switch the ticked categories to Tri-planar for the selected layers/groups.")
    v.addWidget(_separator())
    add("All → UV", "all", "UV",
        "Switch the ticked categories back to UV across the whole stack.")
    add("Selected → UV", "sel", "UV",
        "Switch the ticked categories back to UV for the selected layers/groups.")

    v.addWidget(status)
    v.addStretch(1)
    return w


def _separator():
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Sunken)
    return line


def start_plugin():
    w = _build()
    spui.add_dock_widget(w)
    _widgets.append(w)
    try:
        splog.info(f"[RwG Tri-planar] v{PLUGIN_VERSION} loaded.")
    except Exception:
        pass


def close_plugin():
    for w in _widgets:
        try:
            spui.delete_ui_element(w)
        except Exception:
            pass
    _widgets.clear()


if __name__ == "__main__":
    start_plugin()
