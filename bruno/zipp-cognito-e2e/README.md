# Zipp Cognito E2E collection

This Bruno collection exercises Cognito API authentication and the authenticated
Zipp API workflow. Bruno calls Cognito `InitiateAuth` with
`USER_PASSWORD_AUTH`, captures the returned access token, and stores it in a
collection variable for the protected requests.

## Configure

1. Start the local API and keep its port-forward running at
   `http://127.0.0.1:8080` (for example, `make port-forward-app`).
2. Open this directory as a collection in Bruno and select **Local Cognito**.
3. Set `cognitoApiClientId`, `cognitoApiUsername`, and
   `cognitoApiPassword` to the dedicated API-test app client and test user.
4. Keep the password in Bruno's local environment and never commit it.

The collection calls the regional Cognito User Pools API directly. If the
regional endpoint or local API port changes, update the selected environment.

## Run the workflow

Run the requests in order, or run the collection from Bruno:

1. **API login** obtains and stores the Cognito access token.
2. **Liveness Check** checks the local API is responding.
3. **Unauthenticated management is rejected** confirms the API requires a
   Cognito bearer token.
4. **Create link** creates a unique link and saves its code for later requests.
5. **List links** and **Get link** verify the signed-in user can see it.
6. **Update destination** changes the managed link.
7. **Visit link** checks the public redirect points to the new destination.
8. **Disable link** disables it for the signed-in owner.
9. **Disabled link is unavailable** checks the public redirect now returns
   404.

The test link expires after one hour if the sequence stops before disable.
Run against a disposable local environment: the workflow creates and disables
one real database record. It does not delete user data or other links.

## CLI

The API login request can run in Bruno desktop or CLI mode, provided the
selected environment supplies the test credentials. For load tests, use the
existing Locust runner's `LOAD_ACCESS_TOKEN` input instead of logging in for
every request.

## Security

- The API app client ID is not a password, but keep it in the local environment.
- Do not commit passwords, tokens, cookies, or app client secrets.
- The access token is held in Bruno's collection variable only for the current
  run. Do not print it from a script.
