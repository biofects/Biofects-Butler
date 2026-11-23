# Piper voice models

Each voice has an ONNX model and a Piper JSON configuration. Keep the two files together and keep their filenames unchanged.

| Voice | Model and configuration basename |
|---|---|
| Homer | `en_US-HomerSimpson-medium` |
| Bender | `en_US-bender-medium` |
| HAL 9000 | `en_US-hal_6409-medium` |
| Jarvis | `en_GB-jarvis-medium` |
| Rick | `en_US-RickSanchez-medium` |

Copy the selected pair into your Piper service's voice data directory. Once the service exposes the voice to Home Assistant, Butler can list it in **Settings → Piper Voice** when it is available for the preferred Assist pipeline. These files are optional and sit outside the Home Assistant integration ZIP.

This directory tracks the prompt files. ONNX models and their matching JSON configs are kept as local files. The model copies came from the project's Piper data directory, and their redistribution terms have yet to be documented.

## System prompts

Piper supplies the voice. Copy one prompt into the instructions for your Home Assistant conversation agent to set the assistant’s personality.

- [Homer Simpson](personality-prompts/homer.txt)
- [Bender](personality-prompts/bender.txt)
- [HAL 9000](personality-prompts/hal-9000.txt)
- [J.A.R.V.I.S.](personality-prompts/jarvis.txt)
- [Rick Sanchez](personality-prompts/rick.txt)
- [Butler Neon](personality-prompts/butler-neon.txt)
- [Holographic Interface](personality-prompts/holographic-interface.txt)
- [Companion](personality-prompts/companion.txt)
- [Butler](personality-prompts/butler.txt)
- [Biofects Aurora](personality-prompts/biofects-aurora.txt)
