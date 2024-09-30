import os
from io import BytesIO
import base64
import re
import streamlit as st  # type: ignore
from dotenv import load_dotenv  # type: ignore
import logging

import lib.bedrock as bedrock
import lib.opensearch as opensearch
from lib.logging_config import setup_logging


if 'logging_setup' not in st.session_state:
    setup_logging()
    st.session_state.logging_setup = True
    logger = logging.getLogger(__name__)

# Initialize global variables
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'full_response' not in st.session_state:
    st.session_state.full_response = ""
if 'images' not in st.session_state:
    st.session_state.images = []
if 'contents' not in st.session_state:
    st.session_state.contents = []
if 'valid_pages' not in st.session_state:
    st.session_state.valid_pages = []
if 'bedrock_session' not in st.session_state:
    st.session_state.bedrock_session = None

# Initialize debug_log
if 'debug_log' not in st.session_state:
    st.session_state.debug_log = []

# Function to add debug log


def add_debug_log(message):
    st.session_state.debug_log.append(message)


# Create a Bedrock session if it doesn't exist
if st.session_state.bedrock_session is None:
    load_dotenv(override=True)
    st.session_state.bedrock_session = bedrock.get_bedrock_session(
        os.environ["AWS_ACCESS_KEY_ID"],
        os.environ["AWS_SECRET_ACCESS_KEY"],
        os.environ["AWS_REGION"]
    )
    st.session_state.bedrock_sonnet35_session = bedrock.get_bedrock_session(
        os.environ["AWS_ACCESS_KEY_ID"],
        os.environ["AWS_SECRET_ACCESS_KEY"],
        os.environ["AWS_REGION"]
    )
    st.session_state.bedrock_modelid = os.environ["BEDROCK_MODEL_ID"]
    st.session_state.bedrock_sonnet35_modelid = os.environ["BEDROCK_MODEL_ID"]
    st.session_state.opensearch_endpoint = os.environ["OPENSEARCH_ENDPOINT"]
    st.session_state.opensearch_index_name = os.environ["OPENSEARCH_INDEX_NAME"]
    st.session_state.opensearch_username = os.environ["OPENSEARCH_USERNAME"]
    st.session_state.opensearch_password = os.environ["OPENSEARCH_PASSWORD"]

# Title
st.title("Multimodal PDF Search")

# Layout: Create two columns
col1, col2 = st.columns([5, 5])

with col1:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    if user_query := st.chat_input("무엇을 도와드릴까요?"):
        # Add user message
        st.session_state.messages.append(
            {"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # AI response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            st.session_state.full_response = ""

            try:
                # Perform OpenSearch query only for the first question
                querytype = "general"
                if len(st.session_state.messages) == 1:

                    # Classify request type
                    # Rerouting user query to the appropriate handler
                    querytype = bedrock.classify_request_type(
                        st.session_state.bedrock_session,
                        st.session_state.bedrock_modelid,
                        user_query)

                    st.session_state.images, st.session_state.contents = opensearch.query_imagesearch_to_opensearch(
                        user_query,
                        querytype,
                        5,
                        st.session_state.bedrock_session,
                        st.session_state.opensearch_endpoint,
                        st.session_state.opensearch_index_name,
                        st.session_state.opensearch_username,
                        st.session_state.opensearch_password
                    )

                    add_debug_log("Contents:")
                    for i, content in enumerate(st.session_state.contents, 1):
                        add_debug_log(f"  {i}. {content}")
                # Execute Sonnet query streaming

                def streaming_callback(chunk):
                    st.session_state.full_response += chunk
                    message_placeholder.markdown(
                        st.session_state.full_response + " ")

                add_debug_log(f"length of contents: {
                              len(st.session_state.contents)}")

                final_response = bedrock.query_bedrock_with_images_and_text_with_streaming(
                    st.session_state.bedrock_sonnet35_session,
                    st.session_state.bedrock_sonnet35_modelid,
                    querytype,
                    user_query,
                    [BytesIO(base64.b64decode(image))
                     for image in st.session_state.images],
                    st.session_state.contents,
                    streaming_callback=streaming_callback
                )

                message_placeholder.markdown(st.session_state.full_response)

                # Update valid pages
                st.session_state.valid_pages = [
                    int(page.strip())
                    for pages in re.findall(r'<refpage>(.*?)</refpage>', st.session_state.full_response)
                    for page in pages.split(',')
                ]

            except Exception as e:
                st.error(f"Error during query: {str(e)}")

            # Add AI message
            st.session_state.messages.append(
                {"role": "assistant", "content": st.session_state.full_response})

with col2:
    # Display images (within a scrollable container)
    with st.container():
        st.subheader("Related Images")
        for i, (image, content) in enumerate(zip(st.session_state.images, st.session_state.contents)):
            if i + 1 in st.session_state.valid_pages:
                image = BytesIO(base64.b64decode(image))
                st.image(image, caption=content, use_column_width=True)
                st.markdown("___")

# At the end of your script, outside of any columns:
st.markdown("## Debug Logs")
for log in st.session_state.debug_log:
    st.text(log)

# Clear debug logs for next run
st.session_state.debug_log = []
