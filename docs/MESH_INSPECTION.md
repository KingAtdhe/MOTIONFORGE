# Coach mesh inspection

## 2026-11-20 — new Tripo coaches (FBX, Mixamo-named skeleton)

Sources: `tripo_convert_90120ea2…fbx` (female fitness coach), `tripo_convert_56cf074a…fbx` (male boxing coach),
converted with `tools/blender/import_tripo_fbx.py` to `assets/blender/rigged/coach_{f,m}_tripo.glb` (+ `_static.glb`).
Tools: `inspect_any.py` (as imported), `inspect_welded_any.py` (seams welded in memory), `shells.py` (per piece:
open edges, volume sign, share of faces pointing away from the nearest bone).

| check | female | male | action |
|---|---|---|---|
| pose / transforms | T-pose; armature + mesh identity rotation/scale; 1.0 unit tall | same | scaled to 1.68 m / 1.82 m by the build, proportions unchanged |
| size | 5 017 verts, 9 591 tris (quad-dominant) | 5 361 verts, 10 478 tris | none (light enough for phones) |
| skeleton / weights | 65 Mixamo bones, 0 unweighted verts, ≤ 4 influences, sums = 1 | same | none |
| duplicate verts / faces | 0 / 0 | 0 / 0 | none |
| pieces | 30 (body, hands, head, hair, lashes, shoes, laces) | 16 | none — separate pieces by design |
| winding | consistent | 1 conflict (2 faces), 5 edges shared by 3 faces (shoe) | left: tiny, inside a shoe |
| normals | body/clothes/hands 89–99 % outward; **4 eyelash strips fully inward** (vanish with back-face culling) | body 92–100 % outward; no inward pieces | the 4 strips flipped outward; nothing else |
| open edges | clothing hems and piece borders; 5 real pinholes | 11 pinholes | pinholes closed with existing vertices |
| UVs | one map, all inside 0–1 | same | none |
| textures | base 4K sRGB (bright, matte), normal 4K, roughness 4K (mean 0.65), metallic 4K (mean 0.03) | same (roughness 0.56) | resized to 2K; metallic below 0.5 set to 0; roughness lifted slightly (0.45 + 0.5·r); skin-streak clean-up **off** (none present) |
| material | opaque, double-sided | same | none |

Shape, proportions and UVs are unchanged; the build no longer deletes small surface pieces (only pieces fully enclosed
by the body).

## Earlier coaches (retired 2026-11-20)


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
