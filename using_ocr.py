import os
import base64
import json
from io import BytesIO

import torch
import requests
from pdf2image import convert_from_bytes
from transformers import Qwen2VLForConditionalGeneration, AutoTokenizer, AutoProcessor
from qwen_vl_utils import process_vision_info
import re 

def extract_link(ocr_result):
    """
    Extracts the first internet link from the given text or checks for phrases starting with 'git'.

    Args:
        ocr_result (str): The text to search for a link or 'git' phrase.

    Returns:
        str: The extracted link or 'git' phrase if found, otherwise "null".
    """
    # 정규식 패턴: HTTP 또는 HTTPS로 시작하는 URL 찾기
    url_pattern = r"https?://[^\s]+"
    urls = re.findall(url_pattern, ocr_result)

    # 'git'으로 시작하는 문구 찾기
    git_pattern = r"\bgit\b[^\n]*"
    git_phrases = re.findall(git_pattern, ocr_result)

    # URL이 있으면 반환, 없으면 'git' 문구 반환, 둘 다 없으면 "null"
    if urls:
        return urls[0]
    elif git_phrases:
        return git_phrases[0]
    else:
        return "null"

def load_model(model_path):
    """
    Load the model and processor from the given model path.

    Args:
        model_path (str): Path to the pre-trained model.

    Returns:
        tuple: (model, processor)
    """
    # Load the model
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        model_path,
        torch_dtype=torch.bfloat16,
        attn_implementation="eager",
        device_map="auto",
    )

    # Load the tokenizer and processor
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    min_pixels = 256 * 28 * 28
    max_pixels = 1280 * 28 * 28
    processor = AutoProcessor.from_pretrained(
        model_path, min_pixels=min_pixels, max_pixels=max_pixels
    )

    return model, processor

def loading_pdf_image(url, output_dir="pdf_image", output_filename="first_page.jpg"):
    """
    Download a PDF and save the first page as an image.

    Args:
        url (str): URL of the PDF.
        output_dir (str): Directory to save the image.
        output_filename (str): Name of the output image file.

    Returns:
        str: Path to the saved image.
    """
    # Download the PDF
    response = requests.get(url)

    if response.status_code == 200:
        print("PDF downloaded successfully.")
    else:
        print(f"Failed to download PDF. Status code: {response.status_code}")
        exit()

    # Convert the first page of the PDF to an image
    pdf_data = BytesIO(response.content)
    images = convert_from_bytes(pdf_data.read(), first_page=1, last_page=1)

    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Directory {output_dir} created.")

    # Save the image
    output_path = os.path.join(output_dir, output_filename)
    images[0].save(output_path, "JPEG")
    print(f"Image saved as {output_path}")

    return output_path

def perform_ocr(model, processor, image_path):
    """
    Perform OCR on the given image using the model and processor._)

    Args:
        model: Loaded Qwen2VL model.
        processor: Loaded processor for the model.
        image_path (str): Path to the image to process.

    Returns:
        str: OCR result text.
    """
    # Load and encode the image
    with open(image_path, "rb") as f:
        encoded_image = base64.b64encode(f.read()).decode('utf-8')
    base64_data = f"data:image;base64,{encoded_image}"

    # Prepare messages for the model
    messages = [
        {
            "role": "user",
            "content": [
                {
                     "type": "image", 
                    "image": base64_data 
                },

                {
                    "type": "text", 
                    "text": "Find the online link or project page. If it does not exist, return null; otherwise, return the link."
                }, 
            ],
        }
    ]

    # Tokenize text and prepare inputs
    tokenized_text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(messages)

    inputs = processor(
        text=[tokenized_text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    ).to("cuda")

    # Set generation configurations
    generation_config = model.generation_config
    generation_config.do_sample = True
    generation_config.temperature = 1.0
    generation_config.top_k = 1
    generation_config.top_p = 0.9
    generation_config.min_p = 0.1
    generation_config.best_of = 5
    generation_config.max_new_tokens = 2048
    generation_config.repetition_penalty = 1.06

    # Perform inference
    generated_ids = model.generate(**inputs, generation_config=generation_config)
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )

    return output_text[0]

# Example usage
if __name__ == "__main__":
    # Load the models
    model_path = "/home/cvlab/Desktop/arxiv-daily-feature-branch-name/EraX-VL-7B-V1.0"
    model, processor = load_model(model_path)

    # Download PDF and save the first page as an image
    pdf_url = 'https://arxiv.org/pdf/2308.01390'
    image_path = loading_pdf_image(pdf_url)
    image_path = "/home/cvlab/Desktop/arxiv-daily-feature-branch-name/pdf_image/first_page.jpg"
    # Perform OCR
    result = perform_ocr(model, processor, image_path)
    print("OCR Result:", result)
