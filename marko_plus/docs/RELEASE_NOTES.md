# Marko Plus 0.4.17

Marko Plus 0.4.17 is deliberately limited to correcting the missing visible shortcut on the Toggle Comment AppMenu action from 0.4.16.

- **Edit → Toggle Comment** now carries the real `Ctrl+/` QAction shortcut, matching Markopad, so the keybind is visible in the AppMenu.
- The Keyboard Shortcuts dialog now discovers Toggle Comment from that live AppMenu QAction rather than adding a separate menu-less exception.
- Toggle Comment remains in the same Edit position: after Delete and before Duplicate Line/Selection.
- Toggle Comment behavior, source-editor implementation, Ribbon placement, File Ribbon ordering, More Actions ordering, and all unrelated functionality are unchanged.
