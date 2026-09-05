from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

ext_modules = [
    Pybind11Extension(
        "ratelimiter",
        ["bindings.cpp"],
        include_dirs=["include"],
        cxx_std=17,
    ),
]

setup(
    name="ratelimiter",
    version="0.1.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    # This project ships ONLY the compiled extension (bindings.cpp). Set packages
    # explicitly to [] so setuptools doesn't try to auto-discover the include/,
    # bench/, and tests/ folders as Python packages (which aborts a clean build).
    packages=[],
)
