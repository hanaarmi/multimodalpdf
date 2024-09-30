# extract images from pdf
import sys
import json
import os
import logging

import lib.logging_config as logging_config
import lib.bedrock as bedrock

# logging_config.setup_logging()
logger = logging.getLogger(__name__)

# Add parent directory to sys.path
sys.path.append('..')  # noqa

# Root library
import fitz  # noqa
from PIL import Image  # noqa


# Extract images and metadata
# Experimental function
# not for production use
def extract_images_and_metadata(
        pdffile, savedir,
        min_width=100, min_height=100, left_margin=20, right_margin=20, bottom_margin=50,
        dpi=150):

    # Create save directory and delete existing files
    if not os.path.exists(savedir):
        os.makedirs(savedir)
    else:
        for filename in os.listdir(savedir):
            file_path = os.path.join(savedir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)

    # Open PDF file
    doc = fitz.open(pdffile)
    metadata = {}

    # Extract images and metadata from each page
    for page_num, page in enumerate(doc):

        # If you want to skip pages, use the following code
        # if (page_num < 30):
        #     continue
        # if (page_num > 30):
        #     break

        # Convert page to image
        pix = page.get_pixmap(dpi=200)
        image_path = os.path.join(savedir, f"page_{page_num}_main.png")
        pix.save(image_path)

        # Extract images
        images = page.get_images(full=True)

        for img_index, img in enumerate(images):
            xref = img[0]
            logger.info(f"Page {page_num}, Image {img_index}: xref: {xref}")
            base_image = doc.extract_image(xref)

            if base_image:
                try:
                    # Extract image location and size information
                    img_rects = page.get_image_rects(xref)
                    if not img_rects:
                        raise IndexError("No image rectangles found")
                    # Actual image location in the page
                    img_rect = img_rects[0]
                except IndexError:
                    logger.error(
                        f"Page {page_num}, Image {img_index}: No location information")
                    # Use the entire page as the image area
                    img_rect = page.rect

                # Original image width and height (size in PDF page)
                pdf_width = img_rect.width
                pdf_height = img_rect.height

                # Actual image data size
                image_width = base_image["width"]
                image_height = base_image["height"]

                logger.info(f"- PDF size: {pdf_width}x{pdf_height}")
                logger.info(f"- Actual image size: {image_width}x{image_height}")  # noqa

                # Check minimum size (based on actual image size)
                if image_width < min_width or image_height < min_height:
                    logger.info(f"Skipped (Minimum size not met)")
                    continue

                # Expand image area (left, right, bottom direction)
                expanded_rect = fitz.Rect(
                    img_rect.x0 - left_margin,
                    img_rect.y0,
                    img_rect.x1 + right_margin,
                    img_rect.y1 + bottom_margin
                )

                # Adjust expanded area to fit within page range
                page_rect = page.rect
                expanded_rect = expanded_rect.intersect(page_rect)

                # Extract high resolution image (expanded area)
                pix = page.get_pixmap(matrix=fitz.Matrix(
                    dpi/72, dpi/72), clip=expanded_rect)

                # Convert to PIL image and save
                pil_image = Image.frombytes(
                    "RGB", [pix.width, pix.height], pix.samples)
                image_filename = f"page_{page_num}_img_{
                    img_index}_small.png"
                image_path = os.path.join(savedir, image_filename)
                pil_image.save(image_path, "PNG")
                logger.info(f"Saved expanded high resolution image: {
                            image_filename}")

                # Save metadata
                metadata[image_filename] = {
                    "page": page_num,
                    "image_text": "",
                    "file_name": image_filename,
                    "pdf_width": pdf_width,
                    "pdf_height": pdf_height,
                    "image_width": image_width,
                    "image_height": image_height,
                    "extracted_width": pix.width,
                    "extracted_height": pix.height,
                    "original_rect": {"x0": img_rect.x0, "y0": img_rect.y0, "x1": img_rect.x1, "y1": img_rect.y1},
                    "expanded_rect": {"x0": expanded_rect.x0, "y0": expanded_rect.y0, "x1": expanded_rect.x1, "y1": expanded_rect.y1}
                }

    metadata_file = os.path.join(savedir, "metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as metadata_file:
        json.dump(metadata, metadata_file, ensure_ascii=False, indent=4)

    doc.close()

    return metadata_file


# Extract images, caption and metadata
# Real user scenario
def extract_images_caption_and_metadata(
        pdffile, savedir,
        min_width=20, min_height=20, left_margin=20, right_margin=20, bottom_margin=50,
        dpi=150,
        bedrock_session=None,
        bedrock_modelid=None):

    # Create save directory and delete existing files
    if not os.path.exists(savedir):
        os.makedirs(savedir)
    else:
        for filename in os.listdir(savedir):
            file_path = os.path.join(savedir, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                os.rmdir(file_path)

    # Open PDF file
    doc = fitz.open(pdffile)
    metadata = {}

    # Extract images and metadata from each page
    metadata = {}
    metadata_file = os.path.join(savedir, "metadata.json")

    for page_num, page in enumerate(doc):

        # If you want to skip pages, use the following code
        # if (page_num < 30):
        #     continue
        # if (page_num > 30):
        #     break

        # Convert page to image
        pix = page.get_pixmap(dpi=dpi)
        image_main = os.path.join(savedir, f"page_{page_num}_main.png")
        pix.save(image_main)

        # Extract text from image using bedrock
        main_extracted_text = bedrock.extract_text_from_image_using_bedrock(
            bedrock_session, bedrock_modelid, image_main)
        logger.info(f"Main extracted text: {main_extracted_text}")

        metadata[image_main] = {
            "page": page_num,
            "type": "main",
            "file_name": image_main,
            "image_text": main_extracted_text,
        }

        # Extract images
        images = page.get_images(full=True)

        for img_index, img in enumerate(images):
            xref = img[0]
            logger.info(f"Page {page_num}, Image {img_index}: xref: {xref}")
            base_image = doc.extract_image(xref)

            if base_image:
                try:
                    # Extract image location and size information
                    img_rects = page.get_image_rects(xref)
                    if not img_rects:
                        raise IndexError("No image rectangles found")
                    # Actual image location in the page
                    img_rect = img_rects[0]
                except IndexError:
                    logger.error(
                        f"Page {page_num}, Image {img_index}: No location information")
                    # Use the entire page as the image area
                    img_rect = page.rect

                # Original image width and height (size in PDF page)
                pdf_width = img_rect.width
                pdf_height = img_rect.height

                # Actual image data size
                image_width = base_image["width"]
                image_height = base_image["height"]

                logger.info(f"- PDF size: {pdf_width}x{pdf_height}")
                logger.info(f"- Actual image size: {image_width}x{image_height}")  # noqa

                # Check minimum size (based on actual image size)
                if image_width < min_width or image_height < min_height:
                    logger.info(f"Skipped (Minimum size not met)")
                    continue

                # Expand image area (left, right, bottom direction)
                expanded_rect = fitz.Rect(
                    img_rect.x0 - left_margin,
                    img_rect.y0,
                    img_rect.x1 + right_margin,
                    img_rect.y1 + bottom_margin
                )

                # Adjust expanded area to fit within page range
                page_rect = page.rect
                expanded_rect = expanded_rect.intersect(page_rect)

                # Extract high resolution image (expanded area)
                pix = page.get_pixmap(matrix=fitz.Matrix(
                    dpi/72, dpi/72), clip=expanded_rect)

                # Convert to PIL image and save
                pil_image = Image.frombytes(
                    "RGB", [pix.width, pix.height], pix.samples)
                subimage_filename = f"page_{page_num}_img_{
                    img_index}_small.png"
                image_sub = os.path.join(savedir, subimage_filename)
                pil_image.save(image_sub, "PNG")
                logger.info(f"Saved expanded high resolution image: {
                            subimage_filename}")

                is_same_image, sub_extracted_text = bedrock.extract_structured_text_from_image_using_bedrock(
                    bedrock_session, bedrock_modelid, image_main, image_sub)
                logger.info(f"Is same image: {is_same_image}")
                logger.info(f"Sub extracted text: {sub_extracted_text}")

                # Check if image is same with main image
                if is_same_image:
                    logger.info(f"Skipped (Same with main image)")
                    continue

                # Save metadata
                metadata[image_sub] = {
                    "page": page_num,
                    "type": "sub",
                    "file_name": image_sub,
                    "image_text": sub_extracted_text,
                }

        # Update metadata.json file after processing each page
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=4)

    doc.close()

    return metadata_file
