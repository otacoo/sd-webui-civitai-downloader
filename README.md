# SD WebUI Civitai Model Downloader

A simple extension for downloading models directly from [Civitai](https://civitai.com) into your Stable Diffusion WebUI environment.

### Note: Only tested and working on Forge Classic.

## Features

- View model information and preview images before downloading.
- Real-time download progress and the ability to cancel downloads.
- Adds buttons to every model card to open the model page or delete the files.
- Models are automatically saved in the correct folders (Checkpoints, Lora, LyCORIS, Textual Inversion, Hypernetworks etc.).
- Saves model metadata and preview images alongside the downloaded model file.

## SD WebUI Installation

1. Go into `Extensions` tab > `Install from URL`
2. Paste `https://github.com/otacoo/sd-webui-civitai-downloader.git`
3. Press Install
4. Apply and Restart the UI

## API Key

To download restricted models (XXX) on Civitai requires authentication. To use your Civitai API key:

1. Go to the **Settings** tab in the WebUI.
2. Find the **Civitai Model Downloader** section.
3. Enter your Civitai API key in the provided field.
4. Save settings.

## Folder Structure

Downloaded models are saved to the following folders:

- `models/Stable-diffusion/` (Checkpoints)
- `models/Lora/` (LoRA, LyCORIS, LoCon, LoHa)\
  *Note: LoCon and LyCORIS files are saved into the Lora folder by default, you change this in the settings.*
- `models/embeddings/` (Textual Inversion)
- `models/hypernetworks/` (Hypernetworks)
- `models/Controlnet/` (ControlNet)
- `models/VAE/` (VAE)
- `models/ESRGAN/` (Upscalers)

Each model downloaded will have accompanying `.metadata.json` and `.preview.jpg/png/webp` files.

## Support

For issues or feature requests, please open an [issue](https://github.com/otacoo/sd-webui-civitai-downloader/issues).
