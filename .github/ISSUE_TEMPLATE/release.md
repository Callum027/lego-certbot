---
name: Release
about: Template for creating a checklist issue for a new release.
title: Tag v<new version>
labels: release
assignees: Callum027

---

Checklist:

1. [ ] Set milestone to `v<new version>`
1. [ ] Get the raw changelog using the following command:
   ```bash
   $ git log --oneline --decorate v<previous version>..HEAD
   ```
1. [ ] Update the `tool.poetry.version` field in `pyproject.toml`
1. [ ] Create pull request: <paste pull request here>
1. [ ] Merge pull request
1. [ ] Check that the CI pipeline passed on `main`: <paste CI workflow here>
1. [ ] Tag the new release
1. [ ] Check that the release was automatically published to PyPI: <paste release workflow here>
1. [ ] Close release milestone
1. [ ] Close this issue
