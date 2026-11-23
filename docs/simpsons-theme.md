# The Simpsons theme

Open Butler Dashboards → Displays. Choose The Simpsons under Theme, then choose Homer, Marge, Bart, Lisa or Maggie under Character. Homer is the initial selection. Selection applies to that display; its profile geometry, pages, navigation, entities and actions stay the same.

Android beta.44 (version code 69) or later is required. The Echo Show has been updated and all five selections were checked through the live HA API. Its previous Butler theme was restored after previewing. Install the new APK on other displays before selecting this theme there.

The characters blink and move their mouths while the assistant reports Speaking. This is speaking-state animation, not phoneme-level lip sync. Idle mouths stay closed; Maggie uses a pacifier. Reduced motion removes glances and reduces mouth movement; Off disables continuous animation. Tap the portrait to start voice input.

- [Homer preview](layouts/simpsons-homer.png)
- [Marge preview](layouts/simpsons-marge.png)

Validation: 104 profile/storage tests, 19 editor/grid checks, 5 Android character/layout tests, Chromium editor smoke test, signed APK verification, and live Echo/HA preview. Saved layouts and display assignments were verified unchanged.

## Scenery backgrounds (beta.46)

In Butler Dashboards → Displays, select The Simpsons and a Character, then use Background to choose Blue background, Simpsons’ house, or Kwik-E-Mart. Character and scenery selections preserve each other. Scenery is bundled in Android beta.46 (version code 71); install it on a display before enabling scenery. The Echo Show is updated and currently shows Homer with the house background. Existing layouts, menu order, actions and profile assignments remain unchanged.

- [House on Echo Show](layouts/simpsons-house-background.png)
- [Kwik-E-Mart on Echo Show](layouts/simpsons-kwik-e-mart-background.png)

Artwork was generated with the built-in image_gen tool. Final assets and exact prompts are recorded in the Android repository at docs/simpsons-background-artwork.md. No generation or image-download service is used at runtime.

## Homer picture (beta.47)

Homer now uses the existing promotional image from https://simpsonswiki.com/wiki/File:Homer_Simpson.png instead of the hand-drawn portrait. The unmodified transparent PNG is bundled in the Android app, with runtime eyelid and speaking-mouth overlays. Other characters, background choices, saved layouts and navigation are unchanged.

[Echo Show preview](layouts/simpsons-homer-picture-beta47.png). Source and ownership notes are recorded in the Android repository at docs/homer-picture-source.md. The Echo Show is updated to beta.47 (version code 72).
