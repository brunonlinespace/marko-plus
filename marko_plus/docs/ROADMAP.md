# Marko Plus Roadmap

## Current line: 0.0.1-r3

The current line establishes the Markopad source/preview experience inside a
large-Workspace shell, including registered Workspaces, dashboards, safe file
operations, application settings, and the Preview Font quote effect.

Suitable maintenance work includes crash/regression fixes, packaging and
documentation corrections, and measured performance improvements.

## Deferred work

- Separately test the experimental folder-tree keyboard navigation design.
- Explore source-view ordered-list numbering only in an explicit experimental
  line because it may require editor-engine changes.
- Complete the documented Markopad backports without copying Plus-only UI.
- Broaden AppImage and Wayland test coverage.
- Consider ARM64 and reproducible CI/container builds.

## Product boundary

Keep Marko Plus a focused Markdown Workspace application. New behavior should
extend real document/workspace workflows, not reintroduce script execution or
grow into a general-purpose IDE.
