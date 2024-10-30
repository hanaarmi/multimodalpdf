## (Optional) Setting in EC2

1. Launch instance (e.g. Amazon Linux)

2. Run below command for setting dev envrionment. (This might vary depending on
   your environment.)

```bash
curl https://pyenv.run | bash # You will need to modify your .bashrc according to the pyenv prompts.
sudo yum install git
pyenv install 3.12.7 # This app use python 3.12.7
sudo yum update
sudo yum groupinstall "Development Tools" -y
sudn dnf install openssl-devel bzip2-devel libffi-devel zlib-devel -y
pyenv global 3.12.7
pip instal pipenv
```

## Environment Setup

1. Clone this repository: git clone [repository URL]

2. Navigate to the project directory: cd [project directory]

3. Create a virtual environment and install dependencies using pipenv: pipenv
   install

4. Activate the virtual environment: pipenv shell

5. Add environment values in .env file. You need master username and password of
   opensearch, and accesskey and secertkey of IAM user.

## Opensearch

1. This repo is built for opensearch managed cluster, not serverless. You must
   make opensearch cluster before running this app.

2. After creating opensearch cluster, you should associate analysis-nori
   packages first.

3. To use devtools in your local, you should set Access Policy in Security
   configuration tab.

4. In devtools, make your index with name same as you set in .env file

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
   - if you run in ec2 : streamlit run streamlit_chat_demo.py --server.port 8080
     --server.address 0.0.0.0
   - you should open firewall in security group to your local

## Notes

- Place the PDF files to be processed in the `pdf/` directory.
- Refer to the .env file for OpenSearch and AWS Bedrock related settings.
- This code is not designed for production environments.
