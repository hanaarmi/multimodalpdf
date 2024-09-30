import base64
import json
import logging
import lib.logging_config as logging_config
import boto3
import os
import re

# logging_config.setup_logging()
logger = logging.getLogger(__name__)


def get_bedrock_session(aws_access_key_id, aws_secret_access_key, region_name):
    return boto3.Session(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name
    )


def get_text_vector(session, input_text, dimensions=1024):

    if not input_text or len(input_text.strip()) == 0:
        return None

    bedrock = session.client(service_name='bedrock-runtime')

    request_body = {
        "inputText": input_text,
        "dimensions": dimensions
    }

    body = json.dumps(request_body)
    response = bedrock.invoke_model(
        body=body,
        modelId="amazon.titan-embed-text-v2:0",  # Titan Text v2
        accept="application/json",
        contentType="application/json"
    )

    response_body = json.loads(response.get('body').read())

    embedding = response_body.get("embedding")
    return embedding


def extract_text_from_image_using_bedrock(session, model_id, imagefile):

    logger.info("Starting extract_text_from_image_using_bedrock function")

    if not session:
        logger.error("Session is not provided. Returning from function.")
        return

    logger.info("Creating Bedrock runtime client")
    bedrock_client = session.client(service_name='bedrock-runtime')

    # Read image file and encode to base64
    logger.info(f"Reading image file: {imagefile}")
    with open(imagefile, "rb") as image_file:
        image_bytes = image_file.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    logger.info("Image successfully encoded to base64")

    # Create prompt
    logger.info("Creating prompt")
    prompt = "이미지에서 표에 있는 텍스트를 포함하여 모든 텍스트를 추출해주세요. 추출된 텍스트 내용만 출력해주세요."
    contents = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image_base64
            }
        },
        {
            "type": "text",
            "text": prompt
        }
    ]

    # Prepare request body
    logger.info("Preparing request body")
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": contents

            }
        ]
    }
    logger.info("Request body prepared")

    # Invoke model
    logger.info("Invoking model")
    serialized_body = json.dumps(body)
    response = bedrock_client.invoke_model(
        body=serialized_body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json"
    )

    # Get response body
    response_body = json.loads(response['body'].read())

    if ('content' in response_body and
        isinstance(response_body['content'], list) and
        len(response_body['content']) > 0 and
            'text' in response_body['content'][0]):
        extracted_text = response_body['content'][0]['text']
    else:
        extracted_text = "결과를 가져오지 못했습니다."

    return extracted_text.strip()


# bimage = big image (image including all text and image)
# simage = small image (image to check where simage is in bimage)
def extract_structured_text_from_image_using_bedrock(session, model_id, bimagefile, simagefile):

    logger.info(
        "Starting extract_structured_text_from_image_using_bedrock function")

    if not session:
        logger.error("Session is not provided. Returning from function.")
        return

    logger.info("Creating Bedrock runtime client")
    bedrock_client = session.client(service_name='bedrock-runtime')

    # Read image file and encode to base64
    logger.info(f"Reading image file: {bimagefile}")
    with open(bimagefile, "rb") as image_file:
        bimage_bytes = image_file.read()
    bimage_base64 = base64.b64encode(bimage_bytes).decode('utf-8')
    logger.info(f"{bimagefile} successfully encoded to base64")

    logger.info(f"Reading image file: {simagefile}")
    with open(simagefile, "rb") as image_file:
        simage_bytes = image_file.read()
    simage_base64 = base64.b64encode(simage_bytes).decode('utf-8')
    logger.info(f"{simagefile} successfully encoded to base64")

    # Create prompt
    logger.info("Creating prompt")
    prompt = """
    첫번째 이미지는 전체 이미지고 두번째 이미지는 전체 이미지 중 한 부분일수도 있고 동일한 이미지일수도 있습니다.
    첫번째 이미지와 두번째 이미지가 해상도만 다르고 동일한 이미지라면, 
    <sameimage> 태그에 true 로 표기해주세요. 그 외의 경우에는 false 로 표기해주세요.
    두 이미지가 다른 것이 맞다면, 
    두번째 이미지가 의미하는 것이 무엇이고, 이것이 어떤 구조로 첫번째 이미지 안에 포함되었는지 알려줘야합니다.
    제목, 서브제목, 섹션, 캡션 순서대로 두번째 이미지를 정확하게 표현해주세요.
    출력형식은 제목>서브제목>섹션>캡션 으로 보여주고 다른 의견은 출력하지 마세요.
    출력에서 이미지에서 추출한 텍스트에 단순한 오타는 수정해주세요. 
    <sameimage> 태그는 마지막에 출력합니다.
    """
    # prompt = """
    # 첫번째 이미지는 전체 이미지고 두번째 이미지는 전체 이미지 중 한 부분입니다.
    # 두번째 이미지가 의미하는 것이 무엇이고, 이것이 어떤 구조로 이미지 안에 포함되었는지 알려줘야합니다.
    # 제목, 서브제목, 섹션, 캡션 순서대로 두번째 이미지를 정확하게 표현해주세요.
    # 출력형식은 제목>서브제목>섹션>캡션 으로 보여주세요.
    # 또한, 첫번째 이미지와 두번째 이미지가 해상도만 다르고 동일한 이미지라면,
    # <sameimage> 태그에 true 로 표기해주세요. 그 외의 경우에는 false 로 표기해주세요.
    # <debug> 태그에 <sameimage> 를 판단한 근거를 알려주세요.
    # """

    contents = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": bimage_base64
            }
        },
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": simage_base64
            }
        },
        {
            "type": "text",
            "text": prompt
        }
    ]

    # Prepare request body
    logger.info("Preparing request body")
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": contents

            }
        ]
    }
    logger.info("Request body prepared")

    # Invoke model
    logger.info("Invoking model")
    serialized_body = json.dumps(body)
    response = bedrock_client.invoke_model(
        body=serialized_body,
        modelId=model_id,
        accept="application/json",
        contentType="application/json"
    )

    # Get response body
    response_body = json.loads(response['body'].read())

    if ('content' in response_body and
        isinstance(response_body['content'], list) and
        len(response_body['content']) > 0 and
            'text' in response_body['content'][0]):
        extracted_text = response_body['content'][0]['text']
    else:
        extracted_text = "결과를 가져오지 못했습니다."

    logger.info(f"Extracted text: {extracted_text}")

    # Extract text content and <sameimage> tag value
    is_same_image = False

    # Find <sameimage> tag positions
    sameimage_start = extracted_text.find('<sameimage>')
    sameimage_end = extracted_text.find('</sameimage>')

    if sameimage_start != -1 and sameimage_end != -1:
        # Extract text before <sameimage> tag
        text = extracted_text[:sameimage_start].strip()

        # Extract <sameimage> tag value and convert to boolean
        sameimage_value = extracted_text[sameimage_start +
                                         len('<sameimage>'):sameimage_end].strip().lower()
        is_same_image = sameimage_value == 'true'

    else:
        # If <sameimage> tag is not present, use the entire text
        text = extracted_text.strip()

    # Return results
    return is_same_image, text


# Classify request type and return type
# 1. imagesearch : 특정 이미지 찾기 요청
# 2. general : 일반적인 정보 요청
def classify_request_type(session, model_id, user_query):
    sonnet = session.client(service_name='bedrock-runtime')

    # 요청 유형 분류를 위한 프롬프트 구성
    classification_prompt = f"""
    다음 텍스트를 분석하여 요청 유형을 판단해주세요:

    "{user_query}"

    이 요청이 다음 중 어떤 유형에 해당하는지 판단해주세요:
    1. 특정 이미지 찾기 요청: 사용자가 특정 이미지를 찾아달라는 요청을 한 경우이며,
    이미지와 유사한 단어와 찾아줘와 유사한 단어 모두 포함된 경우만 해당합니다.
    2. 일반적인 정보 요청: 일반적인 정보나 설명을 요구하는 경우

    판단 결과를 다음과 같은 형식으로 간단히 답변해주세요:
    - 특정 이미지 찾기 요청인 경우: "imagesearch"
    - 일반적인 정보 요청인 경우: "general"

    그리고 위 결과를 <querytype> 태그 안에 넣어서 주세요.
    """

    # 프롬프트를 body에 추가
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": classification_prompt
                    }
                ]
            }
        ]
    }

    try:
        serialized_body = json.dumps(body)

        response = sonnet.invoke_model(
            body=serialized_body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )

        response_body = json.loads(response['body'].read())

        # Extract classification result
        if ('content' in response_body and
            isinstance(response_body['content'], list) and
            len(response_body['content']) > 0 and
                'text' in response_body['content'][0]):

            full_text = response_body['content'][0]['text']

            # Extract text within <querytype> tag
            match = re.search(r'<querytype>(.*?)</querytype>', full_text)
            if match:
                classification_result = match.group(1).strip()
            else:
                logger.error("No <querytype> tag found in the response.")
        else:
            logger.error("Failed to retrieve classification result.")
    except Exception as e:
        classification_result = str(e)

    return classification_result

# Function to handle streaming data


def chunk_handler(chunk):
    print(chunk, end='')

# Function to get streaming response from Bedrock Model
# Helper function for query_bedrock_with_images_and_text_with_streaming function


def get_streaming_response(session, model_id, prompt, streaming_callback):

    bedrock = session.client(service_name='bedrock-runtime')

    # Get streaming response from Bedrock Model
    response = bedrock.invoke_model_with_response_stream(
        modelId=model_id,
        body=prompt,
        accept='application/json',
        contentType='application/json'
    )

    # Initialize all_chunks to store all chunks
    all_chunks = ""

    for event in response.get('body'):
        chunk = json.loads(event['chunk']['bytes'])
        if chunk['type'] == 'content_block_delta':
            if chunk['delta']['type'] == 'text_delta':
                streaming_callback(chunk['delta']['text'])
                all_chunks += chunk['delta']['text']

    return all_chunks


# Function to query Bedrock Model with images and text with streaming
def query_bedrock_with_images_and_text_with_streaming(session, model_id,
                                                      querytype, search_text,
                                                      images, texts,
                                                      streaming_callback=chunk_handler):
    contents = []

    # Debug message to check if length of images and metadata
    logger.info(f"length of images: {
                len(images)}, length of texts: {len(texts)}")

    # Debug messeae to verify texts
    for idx, text in enumerate(texts):
        logger.info(f"text {idx}: {text}")

    # Request type
    logger.info(f"Request type: {querytype}")

    for idx, (image, text) in enumerate(zip(images, texts)):

        # debug message to print idx and image size
        logger.info(f"idx: {idx}, image size: {len(image.getvalue())}")

        image_base64 = base64.b64encode(image.getvalue()).decode('utf-8')

        # Append text to contents
        contents.append({
            "type": "text",
            "text": str(idx + 1) + "페이지 이미지 시작"
        })

        contents.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": image_base64
            }
        })

        contents.append({
            "type": "text",
            "text": str(idx + 1) + "페이지 이미지 끝" + "\n\n"
        })

    if (querytype == "imagesearch"):

        additional_prompt = """
        입력된 이미지 순서대로 중요한 이미지입니다. 
        가능한 가장 첫번째 이미지는 무조건 참고하세요.

        - 실제로 참고한 이미지만 1,2,3 과 같은 형식으로 <refpage> 태그 안에 표기해주세요.

        """
        # - 디버그를 위한 요청입니다.
        # 디버그를 위해서 각각의 페이지마다 인식한 텍스트를 모두 빠짐없이 페이지별로 기술해주세요.
        # 디버그를 위한 정보는 <debug> 태그 안에 표기해주세요.

    else:

        additional_prompt = """
        위 이미지들을 참고하여 <query> 내의 질문에 답변해주세요.
        위 이미지들은 특정 분야를 설명한 문서의 각각의 페이지입니다.
        입력한 순서대로 1,2,3,4,5 와 같이 페이지 수로 가정합니다. 
        답변은 한국어로 작성해야 합니다.
        당신은 문서를 보고 문서에 대해 지식을 전달하는 가이드 역할을 해야합니다.
        페이지 내에 있는 화살표 등을 잘 보고 연관되는 표나 지식이 있으면 그것 또한 설명해주세요.
        그리고 설명에는 페이지 수에 대한 언급은 하지 마세요. 
        그리고 프롬프트에 입력한 내용을 답변에 사용하지 마세요.
        테이블이나 이미지에 있는 숫자는 정확하게 인식하여 사용해야 합니다.

        - 실제로 참고한 페이지만 1,2,3 과 같은 형식으로 <refpage> 태그 안에 표기해주세요.

        """
        # - 디버그를 위한 요청입니다.
        # 디버그를 위해서 각각의 페이지마다 인식한 텍스트를 모두 빠짐없이 페이지별로 기술해주세요.
        # 디버그를 위한 정보는 <debug> 태그 안에 표기해주세요.

    contents.append({
        "type": "text",
        "text": additional_prompt
    })

    contents.append({
        "type": "text",
        "text": "\n\n" + "<query>" + search_text + "</query>" + "\n\n"
    })

    # Construct prompt
    prompt = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": contents
            }
        ]
    }

    # Serialize prompt
    serialized_body = json.dumps(prompt)

    # Get streaming response from Bedrock Model
    final_response = get_streaming_response(
        session, model_id, serialized_body, streaming_callback)

    return final_response
