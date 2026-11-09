import sys, zipfile, io, os, tempfile
import trimesh, ezdxf, numpy as np
for z in sys.argv[1:]:
    d = tempfile.mkdtemp(); zf = zipfile.ZipFile(z); assert zf.testzip() is None; zf.extractall(d)
    names = zf.namelist(); print(os.path.basename(z), len(names), 'files')
    bad = 0
    for n in names:
        p = os.path.join(d, n)
        if n.endswith('.stl'):
            m = trimesh.load(p, process=True)
            ok = m.is_watertight and m.is_winding_consistent and m.volume > 0
            if not ok or n == 'plug-whole.stl':
                print('  %-22s tris %6d watertight %s winding %s vol %.0f ext %s' % (n, len(m.faces), m.is_watertight, m.is_winding_consistent, m.volume, np.round(m.extents, 2)))
            bad += not ok
        elif n.endswith('.dxf'):
            doc = ezdxf.readfile(p); aud = doc.audit()
            types = {}
            for e in doc.modelspace(): types[e.dxftype()] = types.get(e.dxftype(), 0) + 1
            print('  %-22s version %s layers %d entities %s audit errors %d' % (n, doc.dxfversion, len(doc.layers), types, len(aud.errors)))
            bad += len(aud.errors)
    tiles = [n for n in names if n.startswith('tiles/')]
    vol = sum(trimesh.load(os.path.join(d, n)).volume for n in tiles); whole = trimesh.load(os.path.join(d, 'plug-whole.stl')).volume
    print('  tiles %d, sum of tile volumes %.0f vs whole plug %.0f (%.2f%%)  problems: %d' % (len(tiles), vol, whole, 100 * (vol / whole - 1), bad))
