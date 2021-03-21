# fingerbank-api

Objective of this project is to interact with fingerbank.org through API and get details of device and API status details.
During API call to fingerbank.org, collect all API details which made succesful, failure and cached API calls.

Here collected sample details of API calls like, number of devices need to make API call, succesful API call, failures API call etc.
**
Execution:
**

1. docker docker-compose build
2. docker compose up

3. Got to Web page, and type below url to get API details
  - http://localhost:5000/getscore/<score_id>
