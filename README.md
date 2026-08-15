# RwG Tri-planar

A small **Substance 3D Painter** plugin to switch the **projection** of many
layers at once — instead of clicking every fill, mask and generator by hand.

> **Preview · v0.1.0**

Buttons for **All** or only the **Selected** layers, to **Tri-planar** or back to
**UV**, with checkboxes to target three categories independently:

- **Fill layers** — content fill layers.
- **Mask fills** — texture-driven masks (fill effects inside a mask stack).
- **Generators** — generators that have their own Tri-planar switch
  (`Use_Triplanar` and similar).

The status line reports what changed, e.g. *"Triplanar: 8 fill layer(s), 3 mask
fill(s), 2 generator(s) updated"*.

## Why

Smart materials often set each texture's projection to **UV**. On models with
bad or stretched UVs you want **Tri-planar**, but Painter has no built-in "switch
them all" — and multi-selecting layers doesn't propagate a projection change.
This does it in one click.

## Requirements

- **Substance 3D Painter 10.0+** — the layer-stack scripting API (with
  `set_projection_mode`) was added in 10.0.

## Install

Copy **`rwg_triplanar.py`** into Painter's Python plugins folder:

```
Windows:  C:\Users\<you>\Documents\Adobe\Adobe Substance 3D Painter\python\plugins\
```

Restart Painter, or **Python → Reload Plugins**. A dock **RwG Tri-planar**
appears (also under the *Window* menu).

## Use

1. Tick the categories you want to affect (**Fill layers / Mask fills /
   Generators**).
2. Click **All → Tri-planar** (whole stack) or **Selected → Tri-planar** (the
   selected layers / groups). **→ UV** switches back.

Only things that *have* a projection are touched — paint layers and other effects
are skipped. Groups are walked recursively.

## How it works

- **Fill layers & mask fills** — `FillLayerNode.set_projection_mode(
  ProjectionMode.Triplanar)`; the two are told apart by `is_in_mask_stack()`.
- **Generators** — the generator's `SourceSubstance` parameters are read, and any
  boolean **Tri-planar enable** switch (name contains `triplanar` and reads like
  an enable, e.g. `Use_Triplanar`) is set. Blending/scale floats like
  `Triplanar_Blending_Contrast` are left alone.

## Known limitations

- Generators that expose Tri-planar as a **projection enum** (0 = UV, 1 =
  Tri-planar) rather than a boolean switch are **not** auto-toggled — the meaning
  of the number varies per generator, so it's skipped to avoid setting a wrong
  value. Open an issue with that generator's parameter names and it can be added.
- Fill *effects* inside content stacks are treated as "fill layers".

## License

Non-commercial — see [`LICENSE`](LICENSE). Free to use, share and adapt with
credit to **RwG**; not for sale.
