# Custom Canvas previews

These screenshots show the native dashboard layout editor using demonstration panels. The canvas previews panel geometry; live entity controls and theme artwork render on the Android display.

- [Whole-home command center](whole-home-command.png)
- [Whole-home phone layout](whole-home-phone.png)
- [Desktop: Feature + Sidebar](custom-canvas-desktop.png)
- [Phone: responsive reflow](custom-canvas-phone.png)

The desktop canvas supports up to twelve columns, explicit starting cells, true row spans, drag placement and resizing, and configurable row heights and gaps. Presets feature the selected panel. Layout undo retains subsequent entity edits.

Run placement and preservation checks with `node --test tools/test-dashboard-grid.cjs` from the integration repository. The browser smoke test is `node tools/test-layout-editor.cjs` and requires Playwright 1.49.1 with Chromium available. It exercises presets, layout undo, desktop/phone previews, pointer resizing, cell placement, drag-and-drop, automatic arrangement, zero gap and mobile overflow. Screenshots default to the system temporary directory; set `BUTLER_PREVIEW_DIR` to choose an output folder.

## Visual editing

[Visual sections designer preview](visual-sections-designer.png)

The left library searches Home Assistant entities and offers draggable panel types. Cards appear inside panels and can be selected for the right-hand inspector. Choosing a tap action changes the saved design without calling services. Keyboard alternatives are available through the library's add buttons, panel dimensions and the inspector's destination selector.

`node tools/test-visual-designer.cjs` (with Playwright available) checks entity search, drag-and-drop onto panels and empty grid cells, card moves, action preservation, duplication, Sections flow, inspector editing and mobile overflow. `node --test tools/test-dashboard-grid.cjs` also covers duplicate prevention and action-limit preservation. The browser-generated JSON is validated against the integration profile parser.
