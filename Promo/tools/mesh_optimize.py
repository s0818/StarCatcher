# Mesh pipeline for AI-generated models: texture-preserving decimation + pivot/scale normalization.
# Usage: mesh_optimize.py <input.glb> <output_dir> <name> <target_triangles>
# Output: <name>.obj + .mtl + texture, centered on the origin, largest side = 1 unit.
import os, shutil, sys, tempfile
import numpy as np
import trimesh, pymeshlab

src, outdir, name, target = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
os.makedirs(outdir, exist_ok=True)

scene = trimesh.load(src)
mesh = trimesh.util.concatenate(list(scene.geometry.values())) if isinstance(scene, trimesh.Scene) else scene
before = len(mesh.faces)
# Normalize pivot (bounding-box center) and size (largest extent = 1)
lo, hi = mesh.bounds
mesh.apply_translation(-(lo + hi) / 2)
mesh.apply_scale(1.0 / float(np.max(hi - lo)))

tmp = tempfile.mkdtemp()
mesh.export(os.path.join(tmp, 'in.obj'))  # writes in.obj + material.mtl + texture image

ms = pymeshlab.MeshSet()
ms.load_new_mesh(os.path.join(tmp, 'in.obj'))
ms.meshing_remove_duplicate_vertices()
ms.meshing_decimation_quadric_edge_collapse_with_texture(targetfacenum=target, qualitythr=0.5, preserveboundary=True, optimalplacement=True)
after = ms.current_mesh().face_number()
out_obj = os.path.join(outdir, f'{name}.obj')
ms.save_current_mesh(out_obj, save_wedge_texcoord=True, save_vertex_color=False)
# copy the texture next to the OBJ (MeshLab keeps the original texture file name in the .mtl)
for f in os.listdir(tmp):
    if f.lower().endswith(('.png', '.jpg', '.jpeg')):
        shutil.copy2(os.path.join(tmp, f), os.path.join(outdir, f))
print(f'{name}: {before} -> {after} triangles ({100 * (1 - after / before):.0f}% fewer)')
