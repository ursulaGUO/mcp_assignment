# Customer MCP + A2A Cloud Run Deployment

## Summary
This repository has a read-to-use eployment of the ADK UI available here: https://customer-a2a-984887160551.europe-west1.run.app

The two main components of this project are:
1. MCP Server (written in [`server.py`](./server.py)) is deployed on Cloud Run using standard gcloud CLI. Refer to the first section "Building MCP server.py" in [`notes.md`](./notes.md).
2. Google ADK (A2A) application (written in [`agent.py`](./agent.py)) is deployed on Cloud RUn as well using standard gcloud CLI. Refer to the second section "Building google adk" in [`notes.md`](./notes.md).

This deployment is largely following these two google labs: [How to deploy a secure MCP server on Cloud Run
](https://codelabs.developers.google.com/codelabs/cloud-run/how-to-deploy-a-secure-mcp-server-on-cloud-run#0) and [Build and deploy an ADK agent that uses an MCP server on Cloud Run](https://codelabs.developers.google.com/codelabs/cloud-run/use-mcp-server-on-cloud-run-with-an-adk-agent?hl=en#0)
