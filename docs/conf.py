from importlib.metadata import version as package_version


project = "demetrapy"
author = "Sermet Pekin"
release = package_version("demetrapy")

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
exclude_patterns = ["_build"]

html_theme = "furo"
html_title = f"demetrapy {release}"
html_theme_options = {
    "source_repository": "https://github.com/SermetPekin/demetrapy/",
    "source_branch": "main",
    "source_directory": "docs/",
}

autodoc_member_order = "bysource"
autodoc_typehints = "description"
myst_enable_extensions = ["colon_fence"]