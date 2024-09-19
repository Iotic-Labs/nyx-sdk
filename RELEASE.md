# Release process

This document outlines the current release process for the Nyx Client, this is subject to change and automation as the codebase changes.

# Manual release process

1. Create a branch to bump the version (this can be done with `poetry version major|minor|patch`) and commit the new pyproject.toml.
1. Also bump `examples/requiements.txt` and README.md version badge.
1. Merge the PR to main
1. Create a tag that matches the new version (eg 1.2.3 == v1.2.3) and push the tag.
1. Run the publishing workflow to release the version
