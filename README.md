# SD WebUI Civitai Model Downloader

A simple extension for downloading models directly from [Civitai](https://civitai.com) into your Stable Diffusion WebUI environment.\
I made this for myself because Civitai Helper is always broken and I don't care about most of the features besides downloading and deleting models.

### Note: Only tested and working on Forge Classic.


## Features

- View model information and preview images before downloading.
- Pick between preview images to use as thumbnail.
- Real-time download progress and the ability to cancel downloads.
- Check for new versions of existing models.
- Check and download missing model info like preview images or metadata.
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
- `models/Lora/` (LoRA, LyCORIS, LoCon, LoHa, DoRA)\
  *Note: LoCon and LyCORIS files are saved into the Lora folder by default, you change this in the settings.*
- `models/embeddings/` (Textual Inversion)
- `models/hypernetworks/` (Hypernetworks)
- `models/Controlnet/` (ControlNet)
- `models/VAE/` (VAE)
- `models/ESRGAN/` (Upscalers)

Each model downloaded will have accompanying `.metadata.json` and `.preview.jpg/png/webp` files.

## Support

For issues or feature requests, please open an [issue](https://github.com/otacoo/sd-webui-civitai-downloader/issues).

## Images

### Model Downloader:
![model_downloader](https://github.com/user-attachments/assets/fbba0452-d5b1-469d-a270-acb72dfee49d)

### Model card buttons:
![Screenshot (906)](https://github.com/user-attachments/assets/09ed8996-a622-41f6-b53c-813a7d7be5e5)

### Settings:
![settings](https://github.com/user-attachments/assets/2aacdd33-5adf-4bf4-a834-176f6febf5e3)
