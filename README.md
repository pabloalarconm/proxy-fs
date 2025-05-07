# OSTrials Proxy for FAIRsharing and FAIRWizard

This service acts as a **proxy API** to authenticate and submit FAIRsharing records on behalf of a user, facilitating integration with external tools like **FAIRWizard questionnaire for FAIR assessment components**.

---

## Start with Docker

Update the environment variables with your **FAIRsharing user credentials**. Also, you can modify URLs to change from dev to production:

```yaml
version: '3'
services:
  api:
    image: pabloalarconm/proxy-fs:0.0.1
    ports:
      - "8000:8000"
    environment:
      - AUTH_URL=https://dev-api.fairsharing.org/users/sign_in
      - DATA_URL=https://dev-api.fairsharing.org/fairsharing_records/
      - USERNAME=*****
      - PASSWORD=*****
```

### Environment Variables Reference
| Variable  | Description                          |
| --------- | ------------------------------------ |
| AUTH\_URL | FAIRsharing authentication endpoint. |
| DATA\_URL | FAIRsharing submission endpoint.     |
| USERNAME  | Your FAIRsharing username.           |
| PASSWORD  | Your FAIRsharing password.           |

## API Endpoints

| Method | Path      | Description                                       |
| ------ | --------- | ------------------------------------------------- |
| GET    | `/docs`   | Opens interactive API documentation (Swagger UI). |
| POST   | `/submit` | Submits a FAIRsharing record.                     |

### Accessing API Documentation
Navigate to http://localhost:8000/docs to explore and test the API interactively via Swagger UI.

### Submitting a FAIRsharing Record

You can submit a record via API using `/submit`.
```
curl -X 'POST' \
  'http://localhost:8000/submit' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "fairsharing_record": {
        "metadata": {
            "name": "Benchmark trial",
            "abbreviation": "benchmark",
            "description": "Benchmark description",
            "homepage": "https://fairsharing.org",
            "contacts": [
                {
                    "contact_name": "Pablo Alarcón-Moreno",
                    "contact_orcid": "0000-0001-5974-589X",
                    "contact_email": "pablo@mail.com"
                }
            ]
        },
        "record_type_id": 16,
        "subject_ids": [
            511
        ],
        "domain_ids": [
            1933,
            1722,
            1916
        ],
        "record_associations_attributes": [
            {
                "linked_record_id": "528",
                "record_assoc_label_id": 14
            },
            {
                "linked_record_id": "175",
                "record_assoc_label_id": 14
            }
        ]
    }
}'

```