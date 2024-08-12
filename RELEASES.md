# Releases

Releases are done to PyPI directly from the main branch.

This usually happens after every merge.
Check the commit log and the date of the latest [PyPI release](https://pypi.org/project/canonical-sphinx-extensions/#history) to see which changes are included.

## Publish a release

To publish a release, first make sure that the version number in `setup.cfg` is increased.
Otherwise, publishing will give an error.

Then manually trigger the "Publish canonical-sphinx-extensions to PyPI" workflow on the main branch.
To do so, you must have Write permission on the repository.
