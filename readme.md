## Environment Setup

1. Clone this repository: git clone [repository URL]

2. Navigate to the project directory: cd [project directory]

3. Create a virtual environment and install dependencies using pipenv: pipenv
   install

4. Activate the virtual environment: pipenv shell

5. Add environment values in .env file. You need master username and password of
   opensearch, and accesskey and secertkey of IAM user.

## Opensearch

1. This repo is build for opensearch managed cluster, not serverless. You must
   make opensearch cluster before run.

2. After creating opensearch cluster, you should associate analysis-nori
   packages first.

3. In devtools, make your index with name same as you set in .env file

```
PUT /[INDEX-NAME]
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "knn.space_type": "cosinesimil",
    "knn": "true",
    "analysis": {
      "tokenizer": {
        "nori_user_dict": {
          "type": "nori_tokenizer",
          "decompound_mode": "mixed",
          "user_dictionary_rules": ["형태소", "분석기"]
        }
      },
      "filter": {
        "nori_part_of_speech": {
          "type": "nori_part_of_speech",
          "lowercase": {
            "type": "lowercase"
          }
        }
      },
      "analyzer": {
        "nori_analyzer": {
          "type": "custom",
          "tokenizer": "nori_user_dict",
          "filter": ["lowercase", "nori_part_of_speech"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "content": {
        "type": "text"
      },
      "meta": {
        "type": "text"
      },
      "image": {
        "type": "binary"
      },
      "content_vector": {
        "type": "knn_vector",
        "dimension": 1024
      }
    }
  }
}
```

## Usage

1. Insert PDF files into OpenSearch: python insert_pdfpages_to_opensearch.py

2. Run the Streamlit demo: streamlit run streamlit_chat_demo.py

## Notes

- Place the PDF files to be processed in the `pdf/` directory.
- Refer to the .env file for OpenSearch and AWS Bedrock related settings.
- This code is not designed for production environments.
