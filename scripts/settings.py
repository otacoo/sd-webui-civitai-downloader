import gradio as gr
from modules import shared
from modules.options import OptionDiv


def on_ui_settings():
    section = ("civitai_model_downloader", "Civitai Model Downloader")
    options = {
        "civitai_api_key": shared.OptionInfo(
            "",
            "Civitai API Key",
            gr.Textbox,
            {"interactive": True, "type": "text"},
            section=section,
        ).info("For downloading restricted models."),
        "sep00": OptionDiv(),
        "civitai_card_button_open_url": shared.OptionInfo(
            True,
            "Show 'Open URL' button on model cards",
            gr.Checkbox,
            {"interactive": True},
            section=section,
        ).info("Opens the model's Civitai page."),
        "civitai_card_button_delete": shared.OptionInfo(
            True,
            "Show 'Delete' button on model cards",
            gr.Checkbox,
            {"interactive": True},
            section=section,
        ).info("Deletes the model's files."),
        "sep01": OptionDiv(),
        "civitai_folder_lycoris": shared.OptionInfo(
            "Lora",
            "Folder for LyCORIS models",
            gr.Textbox,
            {"interactive": True, "type": "text"},
            section=section,
        ).info("Default: Lora"),
        "civitai_folder_locon": shared.OptionInfo(
            "Lora",
            "Folder for LoCon models",
            gr.Textbox,
            {"interactive": True, "type": "text"},
            section=section,
        ).info("Default: Lora"),
        "sep03": OptionDiv(),
        "civitai_disable_card_description": shared.OptionInfo(
            False,
            "Disable card description",
            gr.Checkbox,
            {"interactive": True},
            section=section,
        ).info("Hides description on model cards."),
    }
    for opt_name, opt_info in options.items():
        # Ensure OptionDiv has a section attribute set
        if (
            type(opt_info).__name__ == "OptionDiv"
            and getattr(opt_info, "section", None) is None
        ):
            opt_info.section = section
        shared.opts.add_option(opt_name, opt_info)
