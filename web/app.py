from flask import Flask,jsonify, request, render_template
from flask_restful import Api, Resource 
from pymongo import MongoClient
from redis import Redis
import requests
import pickle
import logging
retriable_errors = [429, 502]
MAX_RETRIES = 3
token = "223ea7b88a5ab29723dbbc8dc77d95f847c3f555"
logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)
app = Flask(__name__)
api_data = {'ratelimit' : 0, 'total' : 0, 'mongo' : 0, 'redis' : 0, 'nodevice' : 0, 'api' : 0}

def handle_api_errors(func):
    """Decorator to handle API errors. """
    def wrapper(self, *args, **kwargs):
        max_retries = MAX_RETRIES
        handled_exceptions = (
            requests.HTTPError,
            requests.Timeout,
            requests.ConnectionError
        )
        retry = 1
        while True:
            try:
                return func(self, *args, **kwargs)
            except handled_exceptions as error:
                retry_interval = random.randint(1, 3)
                if isinstance(error, requests.exceptions.HTTPError):
                    if error.response.status_code == 401:
                        if hasattr(self, "refresh_token"):
                            print("Access token expired. Refreshing the token.")
                            try:
                                #Refresh the token
                                pass
                            except requests.HTTPError as err:
                                raise exc.TokenRefreshError(err)
                        else:
                            print("Authentication failed.")
                            raise exc.AuthException("Authentication error")
                    elif error.response.status_code in retriable_errors:
                        print("API ****** RATE LIMITED **********")
                        api_data['ratelimit'] = api_data['ratelimit'] +  1
                        retry_interval = 3
                    else:
                        print("API call failed. Not retrying. Error: {}".format(error))
                retry += 1
                if retry > max_retries:
                   time.sleep(retry_interval)
    return wrapper

def check_redis(mock):
   """
   Verify key value in redis cache
   param:mock
   return: return dict value if exists else None
   """
   val = redis.get(mock)
   if val:
      read_dict = pickle.loads(val)
      logging.info("Cache: Redis Data is avaialable -- %s"%read_dict)
      return read_dict

def check_mongo(mock):
   """
   Verify key value exists in mongo
   param:mock
   return: return dict value if exists else None
   """
   try:
      t1 = coll.find({"mockid" : mock}, { "_id": 0 })
      if t1.count() >= 1:
         cursor = coll.find({"mockid" : mock})
         for record in cursor:
            logging.info(record)
            logging.info("Mongo: Item already available, wont make API call")
            return record

   except:
     logging.error("Got exception  during mongo check") 


def update_cache(mock, resp):
   """
   Update Redis cache with key value
   param:mock
   param:resp
   """
   p_mydict = pickle.dumps(resp.json())
   redis.set(mock, p_mydict)
   redis.expire(mock, 20)
   logging.info("Insert data in Redis cache succesfull")
   logging.info ("TTL Values")
   logging.info(redis.ttl(mock))


def update_mongo(mock, resp):
   """
   Update Mongo with key value
   param:mock
   param:resp
   """
   try:
     data = {"mockid" : mock}
     data.update(resp.json())
     coll.insert_one(data)
     logging.info("Insert data in Mongo succesfull")
   except:
     logging.error("Got exception  during update") 


@app.route('/getcount')
def getcount():
    """
    Get document count from mongo entry
    return :  total no of documents
    """
    return 'Total documents in mongo :  %s'%(coll.find().count())

@app.route('/getscore/<val>')
def getscore(val):
   """
   Get document score count based on
   return :  total no of documents
   """
   count =coll.find({"score": {"$gt": int(val)}}).count()
   return render_template('test.html', val=val, count=count, total=api_data['total'], mongo=api_data['mongo'], 
 			   redis=api_data['redis'], nodevice=api_data['nodevice'], api=api_data['api'], ratelimit=api_data['ratelimit'])

@handle_api_errors
def getAPI(mock):
   """
   Make aPI call to fingerbank.org and return response and update cache and mongo
   param : mock mock id to fetch device details
   return :  response json
   """
   api_data['total'] = api_data['total'] +  1
   val = check_redis(mock.strip())
   if val:
      api_data['redis'] = api_data['redis'] +  1
      return val

   val = check_mongo(mock)
   if val:
      api_data['mongo'] = api_data['mongo'] +  1
      return val

   get_url = 'https://api.fingerbank.org/api/v2/combinations/interrogate?dhcp_fingerprint=%s'
   url = get_url%mock
   header = { "Authorization" : "Bearer %s"%token}
   resp = requests.get(url, headers=header)
   #print("RESPONS CODE ---%s"%resp.json())
   if resp.status_code == 200:
      print(resp.json())
      api_data['api'] = api_data['api'] +  1
      update_cache(mock, resp)
      update_mongo(mock, resp)
   else:
      print("Failure in Response ---- %s"%(resp.status_code ))
      api_data['nodevice'] = api_data['nodevice'] +  1
      return

if __name__ == "__main__":
   with open('dataconf.txt', 'r+') as fd:
      mock_data = fd.readlines()

   redis = Redis(host='redis', port=6379)
   try:
      client = MongoClient("mongodb://my_db:27017")
   except pymongo.errors.ConnectionFailure:
      logging.info("Could not connect to server:")
   try:
      db = client.test
      coll = db["log"]
   except:
      logging.info("No collection / db details found")

   for mock in mock_data:
      val = getAPI(mock.strip())

   app.run(host="0.0.0.0", debug=True)

