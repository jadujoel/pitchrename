# -*- mode: python -*-

import sys, os
from glob import glob

#lib_dir = sys.executable.replace(os.path.join("bin", "python"), "lib")
#bin_dir = sys.executable.replace(os.path.join("bin", "python"), "bin")

basedir = '/Users/admin/Desktop/pitchrename'
#resources = basedir + '/resources'
ffmpeg = ('{}/ffmpeg'.format(basedir), '.')
ffprobe = ('{}/ffprobe'.format(basedir), '.')
datas = []
binaries = [ffmpeg, ffprobe]

# def _include_if_exists(datas, lib_dir, lib_pattern):
#     results = glob(os.path.join(lib_dir, lib_pattern))
#     if results:
#         for result in results:
#             datas.append((result, '.'))

# Include Fffmpeg
# for dep_so in [
#         'ffmpeg*'
#         'libavutil*',
#         'libavutil.56*',
#         'libavcodec*',
#         'libavformat*',
#         'libavdevice*',
#         'libavfilter*',
#         'libavresample*',
#         'libswscale*',
#         'libswresample*',
#         'libpostproc*'
#         ]:
#     _include_if_exists(datas, lib_dir, dep_so)

#print(datas)
#quit()

block_cipher = None

a = Analysis(['pitchrename.py'],
             pathex=[basedir],
             binaries=binaries,
             datas=datas,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

#a.datas += Tree(resources, prefix='resources')

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='pitchrename',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )


coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='contents')

