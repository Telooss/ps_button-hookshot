# PyInstaller recipe: pyinstaller packaging/ps-buttons-installer.spec  ->  dist/ps-buttons-installer.exe
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

root = Path(SPECPATH).parent
astc_datas, astc_bins, astc_hidden = collect_all("astc_encoder")  # one native build per CPU feature level
a = Analysis(
    [str(root / "packaging" / "entry.py")],
    pathex=[str(root)],
    binaries=astc_bins,
    datas=astc_datas + collect_data_files("archspec"),  # CPU detection data used by astc_encoder
    hiddenimports=collect_submodules("ps_buttons") + astc_hidden + ["texture2ddecoder", "tkinter", "tkinter.filedialog"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="ps-buttons-installer", console=True, upx=False)
