## Environment Setup

1. Clone this repository:
git clone [repository URL]

2. Navigate to the project directory:
cd [project directory]

3. Create a virtual environment and install dependencies using pipenv:
pipenv install

4. Activate the virtual environment:
pipenv shell

## Usage

1. Insert PDF files into OpenSearch:
python insert_pdfpages_to_opensearch.py

2. Run the Streamlit demo:
streamlit run streamlit_chat_demo.py


## Notes

- Place the PDF files to be processed in the `pdf/` directory.
- Refer to the .env file for OpenSearch and AWS Bedrock related settings.
- This code is not designed for production environments.