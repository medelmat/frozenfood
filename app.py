from flask import Flask, render_template, url_for, redirect, request
from azure.storage.blob import BlobServiceClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from jinja2 import environment

import os
import base64
import time

app = Flask(__name__)

def myb64decode(s):
	return base64.b64decode(s[:-1] + (b'===').decode('utf-8')).decode('utf-8')

def find_between( s, first='"captions":[{"text":"', last='","confidence' ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""
app.jinja_env.filters["myb64decode"] = myb64decode
app.jinja_env.filters["find_between"] = find_between



connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING') # retrieve the connection string from the environment variable
container_name = "images" # container name in which images will be store in the storage account
search_service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
key = os.getenv("AZURE_SEARCH_API_KEY")
index_name = "photos-index"
indexer_name = "photos-indexer"

credential = AzureKeyCredential(key)
indexers_client = SearchIndexerClient(search_service_endpoint, credential)
blob_service_client = BlobServiceClient.from_connection_string(conn_str="DefaultEndpointsProtocol=https;AccountName=cognitivesearchimg;AccountKey=2Ry4xctzV2hXOLKT6Osoh+sNvK4kxpaWAUUNJiGJ+l0Tcb2wtD+kdnk2PZaFB0/WlgryUBmCVv6w+AStr4z5Cg==;EndpointSuffix=core.windows.net") # create a blob service client to interact with the storage account
search_client = SearchClient(endpoint=search_service_endpoint,
                      index_name=index_name,
                      credential=credential)

try:
    container_client = blob_service_client.get_container_client(container=container_name) # get container client to interact with the container in which images will be stored
    container_client.get_container_properties() # get properties of the container to force exception to be thrown if container does not exist
except Exception as e:
    print(e)
    print("Creating container...")
#     container_client = blob_service_client.create_container(container_name) # create a container in the storage account if it does not exist


@app.route('/')
def home():
	"""Landing page."""
	return render_template("index.jinja2")


@app.route("/upload-photos", methods=["POST"])
def upload_photos():

	for file in request.files.getlist("photos"):
		try:
			container_client.upload_blob(file.filename, file, metadata={'IsDeleted':'false'}) # upload the file to the container using the filename as the blob name
			indexers_client.run_indexer(indexer_name) # update index    
		except Exception as e:
			print(e)
        
	return redirect('/search-photos')

@app.route("/search-photos", methods=["POST", "GET"])
def search_photos():

	if request.method == 'GET':
		query = ""
	else:
		query = request.form['query']

	results = search_client.search(search_text=query)
	listresults=[]
	for result in results:

		#print(result)
		listresults.append(result)
	#print(type(listresults)	)
	#print(listresults)
	return render_template("list.jinja2", images=listresults)

@app.route("/delete-photo/<name>", methods=["GET"])
def delete_photo(name):
	try:

		container_client.get_blob_client(name).set_blob_metadata(
                               metadata={"IsDeleted":"true"})
		indexers_client.run_indexer(indexer_name) # update index  
		time.sleep(30) 

		container_client.delete_blob(blob=name) # upload the file to the container using the filename as the blob name
		 
	except Exception as e:
		print(e)
        
	return redirect('/search-photos')   

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8080, debug=True)