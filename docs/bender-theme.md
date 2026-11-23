# Futurama — Bender

In **Butler Dashboards → Displays**, choose **Futurama · Bender**, then select a **Background**:

- Plain teal
- Planet Express
- New New York at night
- Robot bar

Android **beta.50 (version code 75)** or later is required for the updated Bender artwork. The Echo Show 8 has been updated, and the live integration supports these options. Refresh the Home Assistant page if the selector is already open.

As of beta.50, Bender uses the promotional picture requested by the user, with blinking and speaking overlays. The original Canvas character has been replaced. Tap him for the existing voice control. Motion follows the app's Reduced and Off settings. The theme uses steel, teal, and warm yellow accents. Backgrounds render behind a dark overlay for readability, preserving dashboard geometry and interaction. Assistant names and TTS voices are still configured independently.

Background artwork was generated with the built-in image_gen tool and bundled locally. Exact prompts and asset paths are recorded in the Android repository at `docs/bender-background-artwork.md`.

Validation: Android beta.49 build and unit tests; all 147 Home Assistant tests; 22 frontend grid/selection checks; all four options selected through the live HA API and captured on Echo Show 8. Saved profiles and display assignments were verified unchanged. Final active selection: Bender with Planet Express. Tap-to-talk reached the device microphone; a spoken conversation was not verified remotely.

## Echo Show previews

- [Plain](layouts/bender__plain.png)
- [Planet Express](layouts/bender__planet_express.png)
- [New New York](layouts/bender__new_new_york.png)
- [Robot bar](layouts/bender__robot_bar.png)
