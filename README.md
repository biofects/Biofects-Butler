# Biofects Butler for Home Assistant

Biofects Butler is the Home Assistant integration for the Biofects Butler Android HUD. Home Assistant remains the source of truth for authentication, entities, services, Assist pipelines, dashboard profiles, display assignments, and themes.

## Features

- Administrator-managed Butler dashboard profiles and pages.
- Grouped entity cards with configurable tap actions, calendars, media, and service controls.
- Weather panels with a selectable Home Assistant weather provider and attribute-driven Daily, Hourly, or Twice Daily forecasts.
- Profile-selectable greeting weather with a concise current temperature and forecast summary.
- Android greetings based on Home Assistant's configured timezone.
- Per-display dashboard themes including Butler Neon, Holographic Interface, and Biofects Aurora.
- Unified Android display registration and compatibility with older Android clients.
- A fixed assistant identity of `Biofects Butler`.
- Native Home Assistant OAuth metadata for the Android application.
- Local push updates with no Biofects cloud dependency.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/biofects/Biofects-Butler` as a custom repository with category **Integration**.
3. Install **Biofects Butler** and restart Home Assistant.
4. Open **Settings > Devices & services > Add integration** and select **Biofects Butler**.

After setup, administrators can open **Butler Dashboards** from the Home Assistant sidebar.

For Android 1.0.0, use Home Assistant integration 1.0.0. The Android release notes state the minimum compatible integration version. [Android downloads](https://github.com/biofects/Biofects-Butler-Releases/releases/latest)

## Optional Piper voices

See the [Piper voice directory](piper-voices/) for setup instructions and ready-to-copy system prompts. Install each ONNX model and matching JSON config on your Piper service.

## Manual installation

Download the integration ZIP from the matching GitHub Release and verify its SHA-256 checksum. Extract it into the Home Assistant configuration directory so this file exists:

```text
config/custom_components/biofects_butler/manifest.json
```

Restart Home Assistant, then add **Biofects Butler** from **Settings > Devices & services**.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q tests
```

## Privacy

The integration communicates locally with Home Assistant and stores Butler configuration in Home Assistant. It does not send product data to Biofects cloud services and contains no ads, analytics, billing, or licensing SDKs.

## License

MIT

## Command Center layouts

In **Butler Dashboards**, open a Command Center screen and choose **Command Center Arrangement**, then save the profile. Home Assistant controls the arrangement for every theme. Select Original (Orbital), Console, Observatory, Wings, or Companion explicitly. Original is the default: status at the far left, navigation on both sides of a centered assistant, and media above events at the far right. Older profiles with **Theme signature** also use this fixed Original arrangement. Flexible grids keep their configured card arrangement.

Console places a compact assistant beside a broad status workspace. Orbital surrounds the assistant with side menus. Observatory places a large projection beside stacked status and information panels. Wings uses status and information rails around the assistant. Phone screens stack vertically; Console shows home status first and Observatory gives the projection more room. Updated Android and Home Assistant components are required for the saved selector.

## Custom Canvas

Choose **Customize → Home Layout → Custom Canvas** for an advanced dashboard. Use up to twelve columns, adjustable row heights and panel gaps, and panels spanning multiple columns and rows. Select a panel and click an empty canvas cell to place it, drag it to a cell or another panel, and drag its bottom-right corner to resize. Width, height, start column and start row are also available in panel controls for keyboard and precise editing.

Start from **Whole-home Command**, **Feature + Sidebar**, **Mosaic**, **Monitor Wall**, or **Daily Briefing**. The selected panel becomes the feature; existing panels, entities and actions stay attached. **Auto arrange** removes preferred positions and fills available gaps. **Undo layout** restores up to twenty layout changes during the editor session without reverting entity edits. Save the profile to persist the design.

Desktop, tablet and phone previews show placement and responsive reflow. Phones use one column in section order; tablets use up to six columns. Panels keep their configured heights and scroll vertically. Preferred positions reserve space before automatic panels; collisions move later panels down. Install matching updated Android and Home Assistant components before saving advanced canvas settings.

**Whole-home Command** groups existing panels by purpose: house status across the top, a prominent assistant beside weather, media and agenda, then quick controls and remaining panels. Phone reading order follows those groups. Undo restores the previous reading order and geometry while keeping subsequent entity edits.

## Visual designer

New profiles and pages start in the **Visual designer**. Existing pages keep their layout until you explicitly choose the designer. The entity library, panel canvas and card inspector work together: drag a panel onto a grid cell, drop an entity into a panel or onto an empty cell, and select its card to change the name, information-row/tile appearance, tile dimensions and tap behavior. **Open controls**, **Toggle entity**, and **Run scene / script / automation** use existing native Butler actions. Designing never operates the entities.

Move cards by dragging them between panels or selecting a destination in the inspector. Grouped entities and linked tap/hold actions move together. Duplicate panels retain their contents and actions. Moves that would duplicate an entity within a panel or exceed supported limits are rejected without removing the original. **Sections · automatic flow** clears preferred panel positions and arranges equal-width sections; corner resizing and precise placement remain available afterward. Advanced panel forms and layout presets are collapsed until needed.

Android preserves the order of mixed information rows and tiles within each named card group. This requires the updated Android renderer. The designer edits native Butler cards and does not execute third-party Lovelace custom-card code.

## Home artwork, headings and greetings

In the visual designer, **Image / logo**, **Heading**, **Text / greeting**, and **Weather** are independently movable and resizable elements. Replace or remove the Theme visual panel to use your own artwork. Image elements fit the image without a theme-imposed crop. Under Grid options, disable **Show built-in page header** to place your own title anywhere. Home's dashboard name is editable.

Select a Heading or Text panel to set fallback text and text size. Bind an `input_text` helper or template sensor as its first entity to show a live greeting, title or message. The entity state is used by default; select a state attribute under the source card's More card options to use an attribute instead. Templates and time-based greetings run in Home Assistant.

For Image panels, bind an HA image entity (using its `entity_picture`) or a helper containing `/local/...`, HTTP or HTTPS image paths. Set a fallback such as `/local/home-logo.png`. Unavailable sources use the fallback. Weather panels use the selected Home Assistant `weather.*` provider and its supported forecast. These elements use native Butler rendering and require the matching updated Android app and integration.


## Easier layout controls

In Butler Dashboards → Customize, select a page and use **Selected panel** to choose what to edit. In the Visual designer, **Place panel** offers Upper left, Upper right, or Below all panels. Arrow buttons move it one cell; Width and Height set its size. **Undo layout** restores geometry without reverting entity or action edits. Dragging is optional. Fixed templates keep their positions; select their panels to edit content, or expand **Change page layout** to choose another template.

Select a card and use **Move card up / down** to change its reading order, or **Move to panel** to relocate it with its actions. **Save changes** applies the selected profile to its assigned displays; changes remain in the editor until saved.

`NODE_PATH=<playwright-install>/node_modules node tools/test-simple-editor.cjs` checks panel selection, positioning, sizes, undo, card ordering, saving, and mobile overflow. Use `BUTLER_BROWSER=webkit` to run the same checks with WebKit when its browser and host libraries are installed.
