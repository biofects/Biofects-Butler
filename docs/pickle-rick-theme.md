# Rick and Morty — Pickle Rick

In **Butler Dashboards → Displays**, select **Rick and Morty · Pickle Rick**, then choose a **Background**:

- Plain green
- Rick’s garage
- Portal world
- Sewer lab

Requires Android **beta.52 (version code 77)** or later. The Echo Show 8 and live integration have been updated. Refresh the Home Assistant page to load the new selector.

The theme uses bundled character artwork, blinking and speaking animation, and green accents. Tap Pickle Rick for the existing voice control. Motion follows the app’s Reduced and Off settings. The artwork preserves its proportions; background changes preserve the dashboard layout. Voice and assistant personality remain separately configured.

Artwork was generated using the built-in image_gen tool. Exact prompts and saved asset filenames are recorded in the Android repository at `docs/pickle-rick-artwork.md`.

Validation: Android build/unit tests, 151 Home Assistant tests, 24 frontend grid/selector checks, and live Echo Show previews of all four selections. Profiles and assignments are checked for preservation. Final active selection: Pickle Rick with Rick’s garage.

## Echo Show previews

- [Plain green](layouts/pickle-rick__plain.png)
- [Garage](layouts/pickle-rick__garage.png)
- [Portal world](layouts/pickle-rick__portal_world.png)
- [Sewer lab](layouts/pickle-rick__sewer_lab.png)

## Speech animation fix (beta.52)

Replaces the barely visible mouth squeeze with a drawn jaw that opens and closes by up to 130 source pixels during speech. At the Echo Show dashboard size this produces roughly 36 pixels of motion. Teeth and tongue follow the opening. Reduced motion uses a smaller range; Off uses a fixed speaking expression. The mouth returns to the original artwork when speech ends.

Verified on the Echo Show during a real text-to-Assist request and audio playback. Captured frames show closed and open jaw positions, followed by the original idle expression after playback completed. [Live speech frames](layouts/pickle-rick-speech-beta52.jpg). Android unit tests include full/reduced/off motion and a minimum jaw-travel check.
