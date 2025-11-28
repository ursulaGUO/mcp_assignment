## Building MCP server.py

### CLI steps
1. Enable the following services which are required for running server.py.
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```

2. Give IAM access to this project
```bash
gcloud projects add-iam-policy-binding $GOOGLE_CLOUD_PROJECT \
    --member=user:$(gcloud config get-value account) \
    --role='roles/run.invoker'
```

3. After the `server.py` is written, we run the following bash to deploy the MCP in europe-west1 region.

```bash
gcloud run deploy customer-mcp-project \
    --service-account=mcp-server-sa@$GOOGLE_CLOUD_PROJECT.iam.gserviceaccount.com \
    --no-allow-unauthenticated \
    --region=europe-west1 \
    --source=. \
    --labels=dev-tutorial=codelab-mcp
```

4. Write the MCP athentication information into gemini setting json file.
```bash
cloudshell edit ~/.gemini/settings.json
```
Export the project number and id token from the previous deployment.
```bash
export PROJECT_NUMBER=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT --format="value(projectNumber)")
export ID_TOKEN=$(gcloud auth print-identity-token)
```
View the value in CLI.
```bash
echo $PROJECT_NUMBER
echo $ID_TOKEN
```
Copy paste these values into the gemini json file.

### TESTING
Run `gemini` in cloudshell and we should be able to access the remote MCP server and use the MCP related functions to query the database.

## Building google adk 
5. Set variables
```bash

export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export SA_NAME=lab2-cr-service
export SERVICE_ACCOUNT="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
```

```bash
gcloud iam service-accounts create ${SA_NAME} \
    --display-name="Service Account for lab 2 "
```

6. Give cloud run service identiy to access remote MCP
```bash

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/run.invoker"
```

7. Deploy 
```bash
# Run the deployment command
uvx --from google-adk \
adk deploy cloud_run \
  --project=$PROJECT_ID \
  --region=europe-west1 \
  --service_name=customer-a2a \
  --with_ui \
  . \
  -- \
  --labels=dev-tutorial=codelab-adk \
  --service-account=$SERVICE_ACCOUNT
```