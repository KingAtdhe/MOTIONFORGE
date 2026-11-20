# Coach mesh inspection (owner's rigged Tripo models)

Sources: `assets/blender/rigged/man.glb`, `woman.glb`. Tools: `tools/blender/inspect_mesh.py` (as imported) and
`tools/blender/inspect_welded.py` (seam splits welded on an in-memory copy, so real holes show up). Neither writes files.

| check | man | woman | action |
|---|---|---|---|
| object transforms | identity rotation/scale on armature and mesh; importer parents + a stray `Icosphere` helper | same | helpers deleted on load (existing); build scales to coach height without changing proportions |
| skin weights | 53 bones, 0 unweighted verts, ≤ 4 influences, sums = 1 | same | none |
| face winding (welded) | 0 conflicts | 0 conflicts | none |
| normals | one closed shell, positive volume (outward); custom split normals present | same | kept as imported (recalculating would drop the authored smoothing) |
| duplicate vertices | 21 400 positional duplicates = UV-seam splits of the glTF format, not defects | 18 681, same | none |
| duplicate faces / wire edges | 0 / 0 | 0 / 0 | none |
| loose geometry | one 8-face fragment inside the torso | none | deleted (`repair_mesh`) |
| holes | 22 boundary loops of 3–8 edges (waistband, feet, scalp) | 20 (scalp, shoulders, waist) | real pinholes closed with existing vertices only (man 4, woman 2); the rest are sub-0.001 mm² slivers, left alone |
| edges shared by > 2 faces | 33 (waistband overlap, feet) | 24 (head, shoulder seams) | left: tiny interior flaps, not visible, removing them would change the surface |
| UVs | one UV map, all inside 0–1 | same | new pinhole faces copy UVs from neighbours |
| textures | base colour 4K sRGB, normal 2K tangent space, roughness/metal 2K | same | base colour downsized to 2K for phones (existing) |
| material | opaque, double-sided; **metallic ~16–18 % painted over skin and fabric** | same | metallic set to 0 except genuine metal (> 0.5, ~1 % of texels): skin/cloth no longer darken and look plastic under phone lighting |

Shape, proportions and vertex positions are unchanged apart from the closed pinholes and the removed fragment
(verified: same dimensions, one connected shell, winding consistent after repair).
