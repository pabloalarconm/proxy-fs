# OSTrials Proxy for FAIR Wizard Authoring Tool

This service acts as a **proxy API** to authenticate and submit FAIR assessment components comming from [**FAIR Wizard authoring tool**](https://ostrails-fair.fair-wizard.com/wizard/) on behalf of a user, facilitating integration with external tools like:

 - **FAIRsharing**
 - **OSTrails Github assessment metadata repository**
 - **FAIR Data Point**

## Start with Docker

```yaml
version: '3'
services:
  api:
    image: pabloalarconm/proxy-fs:1.0.0
    ports:
      - "8000:8000"
    environment:
      - AUTH_URL=https://api.fairsharing.org/users/sign_in
      - DATA_URL=https://api.fairsharing.org/fairsharing_records/
      - USERNAME=*****
      - PASSWORD=*****
      - GITHUB_TOKEN=*****
```
> **Note:** Update the environment variables with your **FAIRsharing user credentials**. Also, you can modify URLs to change from dev to production
---


### Environment Variables Reference
| Variable  | Description                          |
| --------- | ------------------------------------ |
| AUTH\_URL | FAIRsharing authentication endpoint. |
| DATA\_URL | FAIRsharing submission endpoint.     |
| USERNAME  | Your FAIRsharing username.           |
| PASSWORD  | Your FAIRsharing password.           |
| GITHUB_TOKEN  | Your Github access token.        |

## API Endpoints

| Method | Path      | Description                                       |
| ------ | --------- | ------------------------------------------------- |
| GET    | `/questionnaire/docs`   | Opens interactive API documentation (Swagger UI).        |
| POST   | `/questionnaire/submit` | Submits a FAIRsharing record.                            |
| POST   | `/questionnaire/push`   | Git push a Github record and FDP test registration with your RDF DCAT-based record |


### Accessing API Documentation
Navigate to http://YOUR_DOMAIN/questionnaire/docs to explore and test the API interactively via Swagger UI.

### Submitting a Github and FDP Record

Find an example of a RDF DCAT-based record submission in Github and FDP [here](/proxy-fs/test/exploit_test.sh) via API using `/push`.

### Submitting a FAIRsharing Record

Find an example of a FAIRsharing record submission [here](/proxy-fs/test/exploit_test.sh) via API using `/submit`.