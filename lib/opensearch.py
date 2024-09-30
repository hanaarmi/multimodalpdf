import base64
import json
import requests
from requests.auth import HTTPBasicAuth
import logging

import lib.bedrock as bedrock
import lib.logging_config as logging_config

logger = logging.getLogger(__name__)


def insert_metadata_to_opensearch(metadata_file, bedrock_session,
                                  opensearch_endpoint, index_name,
                                  username, password):
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadatas = json.load(f)

    documents = []
    for file_name, item in metadatas.items():

        # Extract page number
        item_page_number = item['page']

        # Extract image path
        item_image_file_name = file_name

        # Extract image text
        item_text = item['image_text']

        # Extract image type
        item_type = item['type']

        logger.info(f"item_page_number: {item_page_number}")
        logger.info(f"item_image_file_name: {item_image_file_name}")
        logger.info(f"item_text: {item_text}")
        logger.info(f"item_type: {item_type}")

        # 이미지 데이터를 base64로 인코딩
        with open(item_image_file_name, "rb") as image_file:
            image_data = image_file.read()

        embedding = bedrock.get_text_vector(bedrock_session, item_text)

        # 문서 생성
        document = {
            "page_number": int(item_page_number),
            "image_file_name": item_image_file_name,
            "text": item_text,
            "image_type": item_type,
            "image": base64.b64encode(image_data).decode('utf-8'),
        }
        if embedding is not None:
            document["content_vector"] = embedding

        # logger.info(f"document: {document}")

        # 문서 인덱싱 URL
        doc_url = f"{opensearch_endpoint}/{index_name}/_doc"

        # 문서 인덱싱
        response = requests.post(doc_url, auth=HTTPBasicAuth(
            username, password), json=document)

        # 결과 출력
        logger.info(f"Document indexing status: {response.status_code}")
        logger.info(f"Response: {response.json()}")


def query_imagesearch_to_opensearch(query, query_type, doc_count=5, bedrock_session=None,
                                    opensearch_endpoint=None, index_name=None,
                                    username=None, password=None):
    logger.info(f"Starting query_imagesearch_to_opensearch with query: {
                query}, doc_count: {doc_count}")

    if (opensearch_endpoint is None or
            index_name is None or username is None or
            password is None):
        logger.error(
            "opensearch_endpoint, index_name, username, password must be provided")
        logger.error(f"opensearch_endpoint: {opensearch_endpoint}")
        logger.error(f"index_name: {index_name}")
        logger.error(f"username: {username}")
        logger.error(f"password: {password}")
        return [], []

    # Set OpenSearch endpoint and index name
    logger.info(f"OpenSearch endpoint: {opensearch_endpoint}")
    logger.info(f"Index name: {index_name}")

    # Set basic authentication information
    logger.info(f"Username: {username}")
    logger.info("Password: [REDACTED]")

    # Query URL
    query_url = f"{opensearch_endpoint}/{index_name}/_search"
    logger.info(f"Query URL: {query_url}")

    # Query body
    vector_query = bedrock.get_text_vector(bedrock_session, query)
    logger.info(f"Vector query generated: {len(vector_query)} dimensions")
    if (query_type == "imagesearch"):
        query_body = {
            "size": doc_count,
            "_source": {"excludes": ["content_vector"]},
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "image_type": "sub"
                            }
                        },
                        {
                            "knn": {
                                "content_vector": {
                                    "vector": vector_query,
                                    "k": 5
                                }
                            }
                        }
                    ]
                }
            }
        }
    else:
        query_body = {
            "size": doc_count,
            "_source": {"excludes": ["content_vector"]},
            "query": {
                "bool": {
                    "must": [
                        {
                            "term": {
                                "image_type": "main"
                            }
                        },
                        {
                            "knn": {
                                "content_vector": {
                                    "vector": vector_query,
                                    "k": 5
                                }
                            }
                        }
                    ]
                }
            }
        }
    # logger.info(f"Query body: {json.dumps(query_body, indent=2)}")

    # HTTP request
    response = requests.get(query_url, auth=HTTPBasicAuth(
        username, password), json=query_body)
    logger.info(f"Response status code: {response.status_code}")

    # Process response
    if response.status_code == 200:
        response_json = response.json()
        # logger.info(f"Response JSON: {json.dumps(response_json, indent=2)}")
        images = []
        contents = []
        for hit in response_json['hits']['hits']:
            # Extract image binary
            image_binary = hit['_source']['image']
            images.append(image_binary)
            # Extract content
            content = hit['_source']['text']
            contents.append(content)

        logger.info(f"Number of images retrieved: {len(images)}")
        logger.info(f"Number of contents retrieved: {len(contents)}")
        return images, contents
    else:
        logger.error(f"Error in OpenSearch query. Status code: {
                     response.status_code}")
        logger.error(f"Error response: {response.text}")
        return [], []
