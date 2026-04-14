from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = collect_data_files('pyqtgraph', excludes=['**/examples/*'])

_excluded = {"pyqtgraph.examples", "pyqtgraph.opengl", "pyqtgraph.jupyter"}
all_imports = collect_submodules(
    "pyqtgraph",
    filter=lambda name: not any(name == ex or name.startswith(ex + ".") for ex in _excluded),
)
hiddenimports = [name for name in all_imports if "Template" in name]
hiddenimports += ['pyqtgraph.multiprocess.bootstrap']

try:
    from PyInstaller.utils.hooks.qt import exclude_extraneous_qt_bindings
except ImportError:
    pass
else:
    excludedimports = exclude_extraneous_qt_bindings(
        hook_name="hook-pyqtgraph",
        qt_bindings_order=None,
    )
